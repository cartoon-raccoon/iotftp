import socket
import os
import logging

from enum import Enum

from iotftp.cmds import BaseCommandHandler
from iotftp.utils import *
import iotftp

logger = logging.getLogger()

class PutCmdState(Enum):
    # raw connection, unhandled
    UNHANDLED = 0
    # sent new port number and details, awaiting acknowledgement
    SENTPORT = 1
    # receiving ack, awaiting connection on subconn
    CONNECT = 2
    # currently receiving file
    RECEIVING = 3
    # complete file received, send ack
    COMPLETE = 4
    # in a current state of error, tracked by main server class
    ERROR = 5

class PutCmdHandler(BaseCommandHandler):
    def __init__(self, args):
        # the current state of the connection
        self.state = PutCmdState.UNHANDLED
        # the main connection where commands are sent
        self.mainconn = None
        # the subconnection where data transfer occurs
        self.subconn = None
        # the file to be transferred
        self.file = None
        # command arguments
        self.args = args
        # total size of the file to receive
        self.totalsize = 0
        # number of bytes received
        self.received = 0


    def handler(self, conn: socket.socket, params, data, commtype):
        start_fn("put_handler")

        if commtype == RW.READ:
            pass
        elif commtype == RW.WRITE:
            pass

        return None, None

    def handle_subconn(self, conn: socket.socket, params, data, commtype):
        return None, None