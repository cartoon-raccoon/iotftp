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
        self.blocksize = get_blocksize(self.totalsize)


    def handler(self, conn: socket.socket, params, data, commtype):
        start_fn("put_handler")

        if commtype == RW.READ:
            logger.debug("Reading from connection")
            match self.state:
                case PutCmdState.SENTPORT:
                    logger.debug("Sent port, awaiting acknowledgement")
                    b = conn.recv(8)
                    if not b:
                        raise ConnClosedErr()

                    if b == ACKNOW:
                        logger.debug("Got acknowledgement")
                        self.state = PutCmdState.CONNECT
                    else:
                        raise ConnClosedErr()

        elif commtype == RW.WRITE:
            logger.debug("Writing to connection")
            match self.state:
                case PutCmdState.UNHANDLED:
                    logger.debug(f"[{data.addr}] Connection unhandled, setting up now")
                    logger.debug(f"args: {self.args}")
                    f = os.path.abspath(self.args[0])

                    logger.debug(f"Got fully qualified path {f}")

                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.bind((params.host, 0))

                    try:
                        if os.path.exists(f):
                            end_fn("put_handler")
                            return HandlerResult.E307, CommandError.ERR_EXST
                        
                        f = open(self.args[0], "wb")
                    
                    except Exception as e:
                        logger.error(f"[ERR] {e}")
                        end_fn("put_handler")
                        return HandlerResult.E308, CommandError.ERR_UNKW
                    
                    port = sock.getsockname()[1]

                    logger.debug(f"Got port {port}")

                    reply = [
                        RES_OK,
                        bytes(str(port), params.encoding)
                    ]
                    
                    conn.send(params.delim.join(reply))
                    self.subconn = sock
                    self.state = PutCmdState.SENTPORT
                    self.file = f

                    end_fn("put_handler")
                    return HandlerResult.NEWCONN, sock

                case PutCmdState.COMPLETE:
                    logger.debug(f"[{data.addr}] Transfer complete, sending ack")
                    conn.send(RES_OK)

                    end_fn("put_handler")
                    return HandlerResult.DONE, None

        return HandlerResult.OK, None

    def handle_subconn(self, conn: socket.socket, params, data, commtype):
        start_fn("put_handler_subconn")

        if commtype == RW.READ:
            match self.state:
                case PutCmdState.CONNECT:
                    self.subconn.settimeout(5)

                    logger.debug("Listening for connection")
                    self.subconn.listen()

                    newconn, addr = self.subconn.accept()
                    logger.debug(f"Got new connection {addr}")

                    newdata = ConnData(ConnType.TRANSFER, addr, None, self)

                    oldconn = self.subconn
                    self.subconn = newconn

                    self.state = PutCmdState.RECEIVING
                    end_fn("put_handler_subconn")
                    return HandlerResult.REPLACE, (oldconn, (newconn, newdata))

                case PutCmdState.RECEIVING:
                    b = conn.recv(self.blocksize)
                    self.received += len(b)

                    self.file.write(b)

                    if self.received >= self.totalsize:
                        self.state = PutCmdState.COMPLETE
                        self.file.close()

        elif commtype == RW.WRITE:
            pass

        return HandlerResult.OK, None