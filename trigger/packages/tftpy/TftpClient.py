"""This module implements the TFTP Client functionality. Instantiate an
instance of the client, and then use its upload or download method. Logging is
performed via a standard logging object set in TftpShared."""

import types
from TftpShared import *
from TftpPacketTypes import *
from TftpContexts import TftpContextClientDownload, TftpContextClientUpload

class TftpClient(TftpSession):
    """This class is an implementation of a tftp client. Once instantiated, a
    download can be initiated via the download() method, or an upload via the
    upload() method."""

    def __init__(self, host, port, options={}):
        TftpSession.__init__(self)
        self.context = None
        self.host = host
        self.iport = port
        self.filename = None
        self.options = options
        if self.options.has_key('blksize'):
            size = self.options['blksize']
            tftpassert(types.IntType == type(size), "blksize must be an int")
            if size < MIN_BLKSIZE or size > MAX_BLKSIZE:
                raise TftpException, "Invalid blksize: %d" % size

    def download(self, filename, output, packethook=None, timeout=SOCK_TIMEOUT):
        """This method initiates a tftp download from the configured remote
        host, requesting the filename passed. It saves the file to a local
        file specified in the output parameter. If a packethook is provided,
        it must be a function that takes a single parameter, which will be a
        copy of each DAT packet received in the form of a TftpPacketDAT
        object. The timeout parameter may be used to override the default
        SOCK_TIMEOUT setting, which is the amount of time that the client will
        wait for a receive packet to arrive.

        Note: If output is a hyphen then stdout is used."""
        # We're downloading.
        log.debug("Creating download context with the following params:")
        log.debug("host = %s, port = %s, filename = %s, output = %s"
            % (self.host, self.iport, filename, output))
        log.debug("options = %s, packethook = %s, timeout = %s"
            % (self.options, packethook, timeout))
        self.context = TftpContextClientDownload(self.host,
                                                 self.iport,
                                                 filename,
                                                 output,
                                                 self.options,
                                                 packethook,
                                                 timeout)
        self.context.start()
        # Download happens here
        self.context.end()

        metrics = self.context.metrics

        log.info('')
        log.info("Download complete.")
        if metrics.duration == 0:
            log.info("Duration too short, rate undetermined")
        else:
            log.info("Downloaded %.2f bytes in %.2f seconds" % (metrics.bytes, metrics.duration))
            log.info("Average rate: %.2f kbps" % metrics.kbps)
        log.info("%.2f bytes in resent data" % metrics.resent_bytes)
        log.info("Received %d duplicate packets" % metrics.dupcount)

    def upload(self, filename, input, packethook=None, timeout=SOCK_TIMEOUT):
        """This method initiates a tftp upload to the configured remote host,
        uploading the filename passed.  If a packethook is provided, it must
        be a function that takes a single parameter, which will be a copy of
        each DAT packet sent in the form of a TftpPacketDAT object. The
        timeout parameter may be used to override the default SOCK_TIMEOUT
        setting, which is the amount of time that the client will wait for a
        DAT packet to be ACKd by the server.

        The input option is the full path to the file to upload, which can
        optionally be '-' to read from stdin.

        Note: If output is a hyphen then stdout is used."""
        self.context = TftpContextClientUpload(self.host,
                                                 self.iport,
                                                 filename,
                                                 input,
                                                 self.options,
                                                 packethook,
                                                 timeout)
        self.context.start()
        # Upload happens here
        self.context.end()

        metrics = self.context.metrics

        log.info('')
        log.info("Upload complete.")
        if metrics.duration == 0:
            log.info("Duration too short, rate undetermined")
        else:
            log.info("Uploaded %d bytes in %.2f seconds" % (metrics.bytes, metrics.duration))
            log.info("Average rate: %.2f kbps" % metrics.kbps)
        log.info("%.2f bytes in resent data" % metrics.resent_bytes)
        log.info("Resent %d packets" % metrics.dupcount)
