"""This module implements all contexts for state handling during uploads and
downloads, the main interface to which being the TftpContext base class.

The concept is simple. Each context object represents a single upload or
download, and the state object in the context object represents the current
state of that transfer. The state object has a handle() method that expects
the next packet in the transfer, and returns a state object until the transfer
is complete, at which point it returns None. That is, unless there is a fatal
error, in which case a TftpException is returned instead."""

from TftpShared import *
from TftpPacketTypes import *
from TftpPacketFactory import TftpPacketFactory
from TftpStates import *
import socket, time, sys

###############################################################################
# Utility classes
###############################################################################

class TftpMetrics(object):
    """A class representing metrics of the transfer."""
    def __init__(self):
        # Bytes transferred
        self.bytes = 0
        # Bytes re-sent
        self.resent_bytes = 0
        # Duplicate packets received
        self.dups = {}
        self.dupcount = 0
        # Times
        self.start_time = 0
        self.end_time = 0
        self.duration = 0
        # Rates
        self.bps = 0
        self.kbps = 0
        # Generic errors
        self.errors = 0

    def compute(self):
        # Compute transfer time
        self.duration = self.end_time - self.start_time
        if self.duration == 0:
            self.duration = 1
        log.debug("TftpMetrics.compute: duration is %s" % self.duration)
        self.bps = (self.bytes * 8.0) / self.duration
        self.kbps = self.bps / 1024.0
        log.debug("TftpMetrics.compute: kbps is %s" % self.kbps)
        for key in self.dups:
            self.dupcount += self.dups[key]

    def add_dup(self, pkt):
        """This method adds a dup for a packet to the metrics."""
        log.debug("Recording a dup of %s" % pkt)
        s = str(pkt)
        if self.dups.has_key(s):
            self.dups[s] += 1
        else:
            self.dups[s] = 1
        tftpassert(self.dups[s] < MAX_DUPS, "Max duplicates reached")

###############################################################################
# Context classes
###############################################################################

class TftpContext(object):
    """The base class of the contexts."""

    def __init__(self, host, port, timeout, dyn_file_func=None):
        """Constructor for the base context, setting shared instance
        variables."""
        self.file_to_transfer = None
        self.fileobj = None
        self.options = None
        self.packethook = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)
        self.timeout = timeout
        self.state = None
        self.next_block = 0
        self.factory = TftpPacketFactory()
        # Note, setting the host will also set self.address, as it's a property.
        self.host = host
        self.port = port
        # The port associated with the TID
        self.tidport = None
        # Metrics
        self.metrics = TftpMetrics()
        # Fluag when the transfer is pending completion.
        self.pending_complete = False
        # Time when this context last received any traffic.
        # FIXME: does this belong in metrics?
        self.last_update = 0
        # The last packet we sent, if applicable, to make resending easy.
        self.last_pkt = None
        self.dyn_file_func = dyn_file_func
        # Count the number of retry attempts.
        self.retry_count = 0

    def getBlocksize(self):
        """Fetch the current blocksize for this session."""
        return int(self.options.get('blksize', 512))

    def __del__(self):
        """Simple destructor to try to call housekeeping in the end method if
        not called explicitely. Leaking file descriptors is not a good
        thing."""
        self.end()

    def checkTimeout(self, now):
        """Compare current time with last_update time, and raise an exception
        if we're over the timeout time."""
        log.debug("checking for timeout on session %s" % self)
        if now - self.last_update > self.timeout:
            raise TftpTimeout, "Timeout waiting for traffic"

    def start(self):
        raise NotImplementedError, "Abstract method"

    def end(self):
        """Perform session cleanup, since the end method should always be
        called explicitely by the calling code, this works better than the
        destructor."""
        log.debug("in TftpContext.end")
        if self.fileobj is not None and not self.fileobj.closed:
            log.debug("self.fileobj is open - closing")
            self.fileobj.close()

    def gethost(self):
        "Simple getter method for use in a property."
        return self.__host

    def sethost(self, host):
        """Setter method that also sets the address property as a result
        of the host that is set."""
        self.__host = host
        self.address = socket.gethostbyname(host)

    host = property(gethost, sethost)

    def setNextBlock(self, block):
        if block >= 2 ** 16:
            log.debug("Block number rollover to 0 again")
            block = 0
        self.__eblock = block

    def getNextBlock(self):
        return self.__eblock

    next_block = property(getNextBlock, setNextBlock)

    def cycle(self):
        """Here we wait for a response from the server after sending it
        something, and dispatch appropriate action to that response."""
        try:
            (buffer, (raddress, rport)) = self.sock.recvfrom(MAX_BLKSIZE)
        except socket.timeout:
            log.warn("Timeout waiting for traffic, retrying...")
            raise TftpTimeout, "Timed-out waiting for traffic"

        # Ok, we've received a packet. Log it.
        log.debug("Received %d bytes from %s:%s"
                        % (len(buffer), raddress, rport))
        # And update our last updated time.
        self.last_update = time.time()

        # Decode it.
        recvpkt = self.factory.parse(buffer)

        # Check for known "connection".
        if raddress != self.address:
            log.warn("Received traffic from %s, expected host %s. Discarding"
                        % (raddress, self.host))

        if self.tidport and self.tidport != rport:
            log.warn("Received traffic from %s:%s but we're "
                        "connected to %s:%s. Discarding."
                        % (raddress, rport,
                        self.host, self.tidport))

        # If there is a packethook defined, call it. We unconditionally
        # pass all packets, it's up to the client to screen out different
        # kinds of packets. This way, the client is privy to things like
        # negotiated options.
        if self.packethook:
            self.packethook(recvpkt)

        # And handle it, possibly changing state.
        self.state = self.state.handle(recvpkt, raddress, rport)
        # If we didn't throw any exceptions here, reset the retry_count to
        # zero.
        self.retry_count = 0

class TftpContextServer(TftpContext):
    """The context for the server."""
    def __init__(self, host, port, timeout, root, dyn_file_func=None):
        TftpContext.__init__(self,
                             host,
                             port,
                             timeout,
                             dyn_file_func
                             )
        # At this point we have no idea if this is a download or an upload. We
        # need to let the start state determine that.
        self.state = TftpStateServerStart(self)
        self.root = root
        self.dyn_file_func = dyn_file_func

    def __str__(self):
        return "%s:%s %s" % (self.host, self.port, self.state)

    def start(self, buffer):
        """Start the state cycle. Note that the server context receives an
        initial packet in its start method. Also note that the server does not
        loop on cycle(), as it expects the TftpServer object to manage
        that."""
        log.debug("In TftpContextServer.start")
        self.metrics.start_time = time.time()
        log.debug("Set metrics.start_time to %s" % self.metrics.start_time)
        # And update our last updated time.
        self.last_update = time.time()

        pkt = self.factory.parse(buffer)
        log.debug("TftpContextServer.start() - factory returned a %s" % pkt)

        # Call handle once with the initial packet. This should put us into
        # the download or the upload state.
        self.state = self.state.handle(pkt,
                                       self.host,
                                       self.port)

    def end(self):
        """Finish up the context."""
        TftpContext.end(self)
        self.metrics.end_time = time.time()
        log.debug("Set metrics.end_time to %s" % self.metrics.end_time)
        self.metrics.compute()

class TftpContextClientUpload(TftpContext):
    """The upload context for the client during an upload.
    Note: If input is a hyphen, then we will use stdin."""
    def __init__(self,
                 host,
                 port,
                 filename,
                 input,
                 options,
                 packethook,
                 timeout):
        TftpContext.__init__(self,
                             host,
                             port,
                             timeout)
        self.file_to_transfer = filename
        self.options = options
        self.packethook = packethook
        if input == '-':
            self.fileobj = sys.stdin
        else:
            self.fileobj = open(input, "rb")

        log.debug("TftpContextClientUpload.__init__()")
        log.debug("file_to_transfer = %s, options = %s" %
            (self.file_to_transfer, self.options))

    def __str__(self):
        return "%s:%s %s" % (self.host, self.port, self.state)

    def start(self):
        log.info("Sending tftp upload request to %s" % self.host)
        log.info("    filename -> %s" % self.file_to_transfer)
        log.info("    options -> %s" % self.options)

        self.metrics.start_time = time.time()
        log.debug("Set metrics.start_time to %s" % self.metrics.start_time)

        # FIXME: put this in a sendWRQ method?
        pkt = TftpPacketWRQ()
        pkt.filename = self.file_to_transfer
        pkt.mode = "octet" # FIXME - shouldn't hardcode this
        pkt.options = self.options
        self.sock.sendto(pkt.encode().buffer, (self.host, self.port))
        self.next_block = 1
        self.last_pkt = pkt
        # FIXME: should we centralize sendto operations so we can refactor all
        # saving of the packet to the last_pkt field?

        self.state = TftpStateSentWRQ(self)

        while self.state:
            try:
                log.debug("State is %s" % self.state)
                self.cycle()
            except TftpTimeout, err:
                log.error(str(err))
                self.retry_count += 1
                if self.retry_count >= TIMEOUT_RETRIES:
                    log.debug("hit max retries, giving up")
                    raise
                else:
                    log.warn("resending last packet")
                    self.state.resendLast()

    def end(self):
        """Finish up the context."""
        TftpContext.end(self)
        self.metrics.end_time = time.time()
        log.debug("Set metrics.end_time to %s" % self.metrics.end_time)
        self.metrics.compute()

class TftpContextClientDownload(TftpContext):
    """The download context for the client during a download.
    Note: If output is a hyphen, then the output will be sent to stdout."""
    def __init__(self,
                 host,
                 port,
                 filename,
                 output,
                 options,
                 packethook,
                 timeout):
        TftpContext.__init__(self,
                             host,
                             port,
                             timeout)
        # FIXME: should we refactor setting of these params?
        self.file_to_transfer = filename
        self.options = options
        self.packethook = packethook
        # FIXME - need to support alternate return formats than files?
        # File-like objects would be ideal, ala duck-typing.
        # If the filename is -, then use stdout
        if output == '-':
            self.fileobj = sys.stdout
        else:
            self.fileobj = open(output, "wb")

        log.debug("TftpContextClientDownload.__init__()")
        log.debug("file_to_transfer = %s, options = %s" %
            (self.file_to_transfer, self.options))

    def __str__(self):
        return "%s:%s %s" % (self.host, self.port, self.state)

    def start(self):
        """Initiate the download."""
        log.info("Sending tftp download request to %s" % self.host)
        log.info("    filename -> %s" % self.file_to_transfer)
        log.info("    options -> %s" % self.options)

        self.metrics.start_time = time.time()
        log.debug("Set metrics.start_time to %s" % self.metrics.start_time)

        # FIXME: put this in a sendRRQ method?
        pkt = TftpPacketRRQ()
        pkt.filename = self.file_to_transfer
        pkt.mode = "octet" # FIXME - shouldn't hardcode this
        pkt.options = self.options
        self.sock.sendto(pkt.encode().buffer, (self.host, self.port))
        self.next_block = 1
        self.last_pkt = pkt

        self.state = TftpStateSentRRQ(self)

        while self.state:
            try:
                log.debug("State is %s" % self.state)
                self.cycle()
            except TftpTimeout, err:
                log.error(str(err))
                self.retry_count += 1
                if self.retry_count >= TIMEOUT_RETRIES:
                    log.debug("hit max retries, giving up")
                    raise
                else:
                    log.warn("resending last packet")
                    self.state.resendLast()

    def end(self):
        """Finish up the context."""
        TftpContext.end(self)
        self.metrics.end_time = time.time()
        log.debug("Set metrics.end_time to %s" % self.metrics.end_time)
        self.metrics.compute()
