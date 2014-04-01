"""This module implements all state handling during uploads and downloads, the
main interface to which being the TftpState base class. 

The concept is simple. Each context object represents a single upload or
download, and the state object in the context object represents the current
state of that transfer. The state object has a handle() method that expects
the next packet in the transfer, and returns a state object until the transfer
is complete, at which point it returns None. That is, unless there is a fatal
error, in which case a TftpException is returned instead."""

from TftpShared import *
from TftpPacketTypes import *
import os

###############################################################################
# State classes
###############################################################################

class TftpState(object):
    """The base class for the states."""

    def __init__(self, context):
        """Constructor for setting up common instance variables. The involved
        file object is required, since in tftp there's always a file
        involved."""
        self.context = context

    def handle(self, pkt, raddress, rport):
        """An abstract method for handling a packet. It is expected to return
        a TftpState object, either itself or a new state."""
        raise NotImplementedError, "Abstract method"

    def handleOACK(self, pkt):
        """This method handles an OACK from the server, syncing any accepted
        options."""
        if pkt.options.keys() > 0:
            if pkt.match_options(self.context.options):
                log.info("Successful negotiation of options")
                # Set options to OACK options
                self.context.options = pkt.options
                for key in self.context.options:
                    log.info("    %s = %s" % (key, self.context.options[key]))
            else:
                log.error("Failed to negotiate options")
                raise TftpException, "Failed to negotiate options"
        else:
            raise TftpException, "No options found in OACK"

    def returnSupportedOptions(self, options):
        """This method takes a requested options list from a client, and
        returns the ones that are supported."""
        # We support the options blksize and tsize right now.
        # FIXME - put this somewhere else?
        accepted_options = {}
        for option in options:
            if option == 'blksize':
                # Make sure it's valid.
                if int(options[option]) > MAX_BLKSIZE:
                    log.info("Client requested blksize greater than %d "
                             "setting to maximum" % MAX_BLKSIZE)
                    accepted_options[option] = MAX_BLKSIZE
                elif int(options[option]) < MIN_BLKSIZE:
                    log.info("Client requested blksize less than %d "
                             "setting to minimum" % MIN_BLKSIZE)
                    accepted_options[option] = MIN_BLKSIZE
                else:
                    accepted_options[option] = options[option]
            elif option == 'tsize':
                log.debug("tsize option is set")
                accepted_options['tsize'] = 1
            else:
                log.info("Dropping unsupported option '%s'" % option)
        log.debug("Returning these accepted options: %s" % accepted_options)
        return accepted_options

    def serverInitial(self, pkt, raddress, rport):
        """This method performs initial setup for a server context transfer,
        put here to refactor code out of the TftpStateServerRecvRRQ and
        TftpStateServerRecvWRQ classes, since their initial setup is
        identical. The method returns a boolean, sendoack, to indicate whether
        it is required to send an OACK to the client."""
        options = pkt.options
        sendoack = False
        if not self.context.tidport:
            self.context.tidport = rport
            log.info("Setting tidport to %s" % rport)

        log.debug("Setting default options, blksize")
        self.context.options = { 'blksize': DEF_BLKSIZE }

        if options:
            log.debug("Options requested: %s" % options)
            supported_options = self.returnSupportedOptions(options)
            self.context.options.update(supported_options)
            sendoack = True

        # FIXME - only octet mode is supported at this time.
        if pkt.mode != 'octet':
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, \
                "Only octet transfers are supported at this time."

        # test host/port of client end
        if self.context.host != raddress or self.context.port != rport:
            self.sendError(TftpErrors.UnknownTID)
            log.error("Expected traffic from %s:%s but received it "
                            "from %s:%s instead."
                            % (self.context.host,
                               self.context.port,
                               raddress,
                               rport))
            # FIXME: increment an error count?
            # Return same state, we're still waiting for valid traffic.
            return self

        log.debug("Requested filename is %s" % pkt.filename)
        # There are no os.sep's allowed in the filename.
        # FIXME: Should we allow subdirectories?
        if pkt.filename.find(os.sep) >= 0:
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "%s found in filename, not permitted" % os.sep

        self.context.file_to_transfer = pkt.filename

        return sendoack

    def sendDAT(self):
        """This method sends the next DAT packet based on the data in the
        context. It returns a boolean indicating whether the transfer is
        finished."""
        finished = False
        blocknumber = self.context.next_block
        # Test hook
        if DELAY_BLOCK and DELAY_BLOCK == blocknumber:
            import time
            log.debug("Deliberately delaying 10 seconds...")
            time.sleep(10)
        tftpassert( blocknumber > 0, "There is no block zero!" )
        dat = None
        blksize = self.context.getBlocksize()
        buffer = self.context.fileobj.read(blksize)
        log.debug("Read %d bytes into buffer" % len(buffer))
        if len(buffer) < blksize:
            log.info("Reached EOF on file %s"
                % self.context.file_to_transfer)
            finished = True
        dat = TftpPacketDAT()
        dat.data = buffer
        dat.blocknumber = blocknumber
        self.context.metrics.bytes += len(dat.data)
        log.debug("Sending DAT packet %d" % dat.blocknumber)
        self.context.sock.sendto(dat.encode().buffer,
                                 (self.context.host, self.context.tidport))
        if self.context.packethook:
            self.context.packethook(dat)
        self.context.last_pkt = dat
        return finished

    def sendACK(self, blocknumber=None):
        """This method sends an ack packet to the block number specified. If
        none is specified, it defaults to the next_block property in the
        parent context."""
        log.debug("In sendACK, passed blocknumber is %s" % blocknumber)
        if blocknumber is None:
            blocknumber = self.context.next_block
        log.info("Sending ack to block %d" % blocknumber)
        ackpkt = TftpPacketACK()
        ackpkt.blocknumber = blocknumber
        self.context.sock.sendto(ackpkt.encode().buffer,
                                 (self.context.host,
                                  self.context.tidport))
        self.context.last_pkt = ackpkt

    def sendError(self, errorcode):
        """This method uses the socket passed, and uses the errorcode to
        compose and send an error packet."""
        log.debug("In sendError, being asked to send error %d" % errorcode)
        errpkt = TftpPacketERR()
        errpkt.errorcode = errorcode
        self.context.sock.sendto(errpkt.encode().buffer,
                                 (self.context.host,
                                  self.context.tidport))
        self.context.last_pkt = errpkt

    def sendOACK(self):
        """This method sends an OACK packet with the options from the current
        context."""
        log.debug("In sendOACK with options %s" % self.context.options)
        pkt = TftpPacketOACK()
        pkt.options = self.context.options
        self.context.sock.sendto(pkt.encode().buffer,
                                 (self.context.host,
                                  self.context.tidport))
        self.context.last_pkt = pkt

    def resendLast(self):
        "Resend the last sent packet due to a timeout."
        log.warn("Resending packet %s on sessions %s"
            % (self.context.last_pkt, self))
        self.context.metrics.resent_bytes += len(self.context.last_pkt.buffer)
        self.context.metrics.add_dup(self.context.last_pkt)
        self.context.sock.sendto(self.context.last_pkt.encode().buffer,
                                 (self.context.host, self.context.tidport))
        if self.context.packethook:
            self.context.packethook(self.context.last_pkt)

    def handleDat(self, pkt):
        """This method handles a DAT packet during a client download, or a
        server upload."""
        log.info("Handling DAT packet - block %d" % pkt.blocknumber)
        log.debug("Expecting block %s" % self.context.next_block)
        if pkt.blocknumber == self.context.next_block:
            log.debug("Good, received block %d in sequence"
                        % pkt.blocknumber)

            self.sendACK()
            self.context.next_block += 1

            log.debug("Writing %d bytes to output file"
                        % len(pkt.data))
            self.context.fileobj.write(pkt.data)
            self.context.metrics.bytes += len(pkt.data)
            # Check for end-of-file, any less than full data packet.
            if len(pkt.data) < self.context.getBlocksize():
                log.info("End of file detected")
                return None

        elif pkt.blocknumber < self.context.next_block:
            if pkt.blocknumber == 0:
                log.warn("There is no block zero!")
                self.sendError(TftpErrors.IllegalTftpOp)
                raise TftpException, "There is no block zero!"
            log.warn("Dropping duplicate block %d" % pkt.blocknumber)
            self.context.metrics.add_dup(pkt)
            log.debug("ACKing block %d again, just in case" % pkt.blocknumber)
            self.sendACK(pkt.blocknumber)

        else:
            # FIXME: should we be more tolerant and just discard instead?
            msg = "Whoa! Received future block %d but expected %d" \
                % (pkt.blocknumber, self.context.next_block)
            log.error(msg)
            raise TftpException, msg

        # Default is to ack
        return TftpStateExpectDAT(self.context)

class TftpStateServerRecvRRQ(TftpState):
    """This class represents the state of the TFTP server when it has just
    received an RRQ packet."""
    def handle(self, pkt, raddress, rport):
        "Handle an initial RRQ packet as a server."
        log.debug("In TftpStateServerRecvRRQ.handle")
        sendoack = self.serverInitial(pkt, raddress, rport)
        path = self.context.root + os.sep + self.context.file_to_transfer
        log.info("Opening file %s for reading" % path)
        if os.path.exists(path):
            # Note: Open in binary mode for win32 portability, since win32
            # blows.
            self.context.fileobj = open(path, "rb")
        elif self.context.dyn_file_func:
            log.debug("No such file %s but using dyn_file_func" % path)
            self.context.fileobj = \
                self.context.dyn_file_func(self.context.file_to_transfer)

            if self.context.fileobj is None:
                log.debug("dyn_file_func returned 'None', treating as "
                          "FileNotFound")
                self.sendError(TftpErrors.FileNotFound)
                raise TftpException, "File not found: %s" % path
        else:
            self.sendError(TftpErrors.FileNotFound)
            raise TftpException, "File not found: %s" % path

        # Options negotiation.
        if sendoack:
            # Note, next_block is 0 here since that's the proper
            # acknowledgement to an OACK.
            # FIXME: perhaps we do need a TftpStateExpectOACK class...
            self.sendOACK()
            # Note, self.context.next_block is already 0.
        else:
            self.context.next_block = 1
            log.debug("No requested options, starting send...")
            self.context.pending_complete = self.sendDAT()
        # Note, we expect an ack regardless of whether we sent a DAT or an
        # OACK.
        return TftpStateExpectACK(self.context)

        # Note, we don't have to check any other states in this method, that's
        # up to the caller.

class TftpStateServerRecvWRQ(TftpState):
    """This class represents the state of the TFTP server when it has just
    received a WRQ packet."""
    def handle(self, pkt, raddress, rport):
        "Handle an initial WRQ packet as a server."
        log.debug("In TftpStateServerRecvWRQ.handle")
        sendoack = self.serverInitial(pkt, raddress, rport)
        path = self.context.root + os.sep + self.context.file_to_transfer
        log.info("Opening file %s for writing" % path)
        if os.path.exists(path):
            # FIXME: correct behavior?
            log.warn("File %s exists already, overwriting..." % self.context.file_to_transfer)
        # FIXME: I think we should upload to a temp file and not overwrite the
        # existing file until the file is successfully uploaded.
        self.context.fileobj = open(path, "wb")

        # Options negotiation.
        if sendoack:
            log.debug("Sending OACK to client")
            self.sendOACK()
        else:
            log.debug("No requested options, expecting transfer to begin...")
            self.sendACK()
        # Whether we're sending an oack or not, we're expecting a DAT for
        # block 1
        self.context.next_block = 1
        # We may have sent an OACK, but we're expecting a DAT as the response
        # to either the OACK or an ACK, so lets unconditionally use the
        # TftpStateExpectDAT state.
        return TftpStateExpectDAT(self.context)

        # Note, we don't have to check any other states in this method, that's
        # up to the caller.

class TftpStateServerStart(TftpState):
    """The start state for the server. This is a transitory state since at
    this point we don't know if we're handling an upload or a download. We
    will commit to one of them once we interpret the initial packet."""
    def handle(self, pkt, raddress, rport):
        """Handle a packet we just received."""
        log.debug("In TftpStateServerStart.handle")
        if isinstance(pkt, TftpPacketRRQ):
            log.debug("Handling an RRQ packet")
            return TftpStateServerRecvRRQ(self.context).handle(pkt,
                                                               raddress,
                                                               rport)
        elif isinstance(pkt, TftpPacketWRQ):
            log.debug("Handling a WRQ packet")
            return TftpStateServerRecvWRQ(self.context).handle(pkt,
                                                               raddress,
                                                               rport)
        else:
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, \
                "Invalid packet to begin up/download: %s" % pkt

class TftpStateExpectACK(TftpState):
    """This class represents the state of the transfer when a DAT was just
    sent, and we are waiting for an ACK from the server. This class is the
    same one used by the client during the upload, and the server during the
    download."""
    def handle(self, pkt, raddress, rport):
        "Handle a packet, hopefully an ACK since we just sent a DAT."
        if isinstance(pkt, TftpPacketACK):
            log.info("Received ACK for packet %d" % pkt.blocknumber)
            # Is this an ack to the one we just sent?
            if self.context.next_block == pkt.blocknumber:
                if self.context.pending_complete:
                    log.info("Received ACK to final DAT, we're done.")
                    return None
                else:
                    log.debug("Good ACK, sending next DAT")
                    self.context.next_block += 1
                    log.debug("Incremented next_block to %d"
                        % (self.context.next_block))
                    self.context.pending_complete = self.sendDAT()

            elif pkt.blocknumber < self.context.next_block:
                log.debug("Received duplicate ACK for block %d"
                    % pkt.blocknumber)
                self.context.metrics.add_dup(pkt)

            else:
                log.warn("Oooh, time warp. Received ACK to packet we "
                         "didn't send yet. Discarding.")
                self.context.metrics.errors += 1
            return self
        elif isinstance(pkt, TftpPacketERR):
            log.error("Received ERR packet from peer: %s" % str(pkt))
            raise TftpException, \
                "Received ERR packet from peer: %s" % str(pkt)
        else:
            log.warn("Discarding unsupported packet: %s" % str(pkt))
            return self

class TftpStateExpectDAT(TftpState):
    """Just sent an ACK packet. Waiting for DAT."""
    def handle(self, pkt, raddress, rport):
        """Handle the packet in response to an ACK, which should be a DAT."""
        if isinstance(pkt, TftpPacketDAT):
            return self.handleDat(pkt)

        # Every other packet type is a problem.
        elif isinstance(pkt, TftpPacketACK):
            # Umm, we ACK, you don't.
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received ACK from peer when expecting DAT"

        elif isinstance(pkt, TftpPacketWRQ):
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received WRQ from peer when expecting DAT"

        elif isinstance(pkt, TftpPacketERR):
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received ERR from peer: " + str(pkt)

        else:
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received unknown packet type from peer: " + str(pkt)

class TftpStateSentWRQ(TftpState):
    """Just sent an WRQ packet for an upload."""
    def handle(self, pkt, raddress, rport):
        """Handle a packet we just received."""
        if not self.context.tidport:
            self.context.tidport = rport
            log.debug("Set remote port for session to %s" % rport)

        # If we're going to successfully transfer the file, then we should see
        # either an OACK for accepted options, or an ACK to ignore options.
        if isinstance(pkt, TftpPacketOACK):
            log.info("Received OACK from server")
            try:
                self.handleOACK(pkt)
            except TftpException:
                log.error("Failed to negotiate options")
                self.sendError(TftpErrors.FailedNegotiation)
                raise
            else:
                log.debug("Sending first DAT packet")
                self.context.pending_complete = self.sendDAT()
                log.debug("Changing state to TftpStateExpectACK")
                return TftpStateExpectACK(self.context)

        elif isinstance(pkt, TftpPacketACK):
            log.info("Received ACK from server")
            log.debug("Apparently the server ignored our options")
            # The block number should be zero.
            if pkt.blocknumber == 0:
                log.debug("Ack blocknumber is zero as expected")
                log.debug("Sending first DAT packet")
                self.context.pending_complete = self.sendDAT()
                log.debug("Changing state to TftpStateExpectACK")
                return TftpStateExpectACK(self.context)
            else:
                log.warn("Discarding ACK to block %s" % pkt.blocknumber)
                log.debug("Still waiting for valid response from server")
                return self

        elif isinstance(pkt, TftpPacketERR):
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received ERR from server: " + str(pkt)

        elif isinstance(pkt, TftpPacketRRQ):
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received RRQ from server while in upload"

        elif isinstance(pkt, TftpPacketDAT):
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received DAT from server while in upload"

        else:
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received unknown packet type from server: " + str(pkt)

        # By default, no state change.
        return self

class TftpStateSentRRQ(TftpState):
    """Just sent an RRQ packet."""
    def handle(self, pkt, raddress, rport):
        """Handle the packet in response to an RRQ to the server."""
        if not self.context.tidport:
            self.context.tidport = rport
            log.info("Set remote port for session to %s" % rport)

        # Now check the packet type and dispatch it properly.
        if isinstance(pkt, TftpPacketOACK):
            log.info("Received OACK from server")
            try:
                self.handleOACK(pkt)
            except TftpException, err:
                log.error("Failed to negotiate options: %s" % str(err))
                self.sendError(TftpErrors.FailedNegotiation)
                raise
            else:
                log.debug("Sending ACK to OACK")

                self.sendACK(blocknumber=0)

                log.debug("Changing state to TftpStateExpectDAT")
                return TftpStateExpectDAT(self.context)

        elif isinstance(pkt, TftpPacketDAT):
            # If there are any options set, then the server didn't honour any
            # of them.
            log.info("Received DAT from server")
            if self.context.options:
                log.info("Server ignored options, falling back to defaults")
                self.context.options = { 'blksize': DEF_BLKSIZE }
            return self.handleDat(pkt)

        # Every other packet type is a problem.
        elif isinstance(pkt, TftpPacketACK):
            # Umm, we ACK, the server doesn't.
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received ACK from server while in download"

        elif isinstance(pkt, TftpPacketWRQ):
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received WRQ from server while in download"

        elif isinstance(pkt, TftpPacketERR):
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received ERR from server: " + str(pkt)

        else:
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received unknown packet type from server: " + str(pkt)

        # By default, no state change.
        return self
