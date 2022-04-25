import socket
import os
import logging

from enum import Enum

from iotftp.cmds import BaseCommandHandler
from iotftp.utils import *
import iotftp

logger = logging.getLogger()

class GetCmdState(Enum):
    # raw connection, unhandled
    UNHANDLED = 0
    # sent new port number and details, awaiting acknowledgement
    SENTPORT = 1
    # received ack, awaiting connection on subconn
    CONNECT = 2
    # currently sending file
    SENDING = 3
    # sending complete, awaiting ack
    COMPLETE = 4
    # received ack, respond with ack
    SENDACK = 5
    # in a current state of error, tracked by main server class
    ERROR = 6


class GetCmdHandler(BaseCommandHandler):
    def __init__(self, args):
        self.state = GetCmdState.UNHANDLED
        self.mainconn = None
        self.subconn = None
        # the file to be sent
        self.file = None
        # command arguments
        self.args = args
        # total size of the file
        self.totalsize = 0
        self.blocksize = get_blocksize(self.totalsize)
        # number of bytes sent
        self.sent = 0

    def handle(self, conn: socket.socket, params, data, commtype):
        start_fn("get_handler")
        if commtype == iotftp.RW.READ:
            logger.debug("Reading from connection")
            match self.state:
                case GetCmdState.SENTPORT:
                    # receive acknowledgement
                    logger.debug("Sent port, awaiting acknowledgement")
                    b = conn.recv(8)
                    if not b:
                        raise ConnClosedErr()

                    if b == ACKNOW:
                        logger.debug("Got acknowledgement")
                        self.state = GetCmdState.CONNECT
                    else:
                        # instead of sending an error back to the client, just close it
                        raise ConnClosedErr()
                case GetCmdState.COMPLETE:
                    logger.debug("Transfer complete, awaiting acknowledgement")
                    b = conn.recv(8)

                    if b == ACKNOW:
                        logger.debug("Got acknowledgement")
                    else:
                        raise ConnClosedErr()

                    self.state = GetCmdState.SENDACK
                    
                    end_fn("get_handler")
                    return HandlerResult.OK, None

        elif commtype == iotftp.RW.WRITE:
            logger.debug("Writing to connection")
            match self.state:
                case GetCmdState.UNHANDLED:
                    self.mainconn = conn
                    logger.debug(f"[{data.addr}] Connection unhandled, setting up now")
                    logger.debug(f"args: {self.args}")
                    f = os.path.abspath(self.args)

                    logger.debug(f"Got fully qualified path {f}")
                    # create a new socket and bind to it
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.bind((params.host, 0))
                    try:
                        self.file = open(self.args, "rb")
                        self.totalsize = os.path.getsize(f)
                        logger.debug(f"Got size {self.totalsize}")
                    except FileNotFoundError:
                        end_fn("get_handler")
                        return HandlerResult.E302, CommandError.ERR_NONE
                    except PermissionError:
                        end_fn("get_handler")
                        return HandlerResult.E301, CommandError.ERR_PERM
                    except IsADirectoryError:
                        end_fn("get_handler")
                        return HandlerResult.E309, CommandError.ERR_ISDR
                    except OSError as e:
                        logger.debug(f"got err: {e}")

                        end_fn("get_handler")
                        return HandlerResult.E302, CommandError.ERR_NONE

                    port = sock.getsockname()[1]

                    logger.debug(f"Got port {port}")
                    
                    reply = [
                        RES_OK,
                        bytes(str(sock.getsockname()[1]), params.encoding),
                        bytes(str(self.totalsize), params.encoding),
                    ]
                    
                    conn.send(params.delim.join(reply))
                    self.subconn = sock
                    self.state = GetCmdState.SENTPORT

                    end_fn("get_handler")
                    return HandlerResult.NEWCONN, sock

                case GetCmdState.SENDING:
                    logger.debug(f"{data.addr}] Connection sending")
                    pass
                case GetCmdState.SENDACK:
                    logger.debug(f"Sending acknowledgement to client")
                    conn.send(RES_OK)

                    end_fn("get_handler")
                    return HandlerResult.DONE, None

        logger.debug(self.state)

        end_fn("get_handler")
        return HandlerResult.OK, None

    def handle_subconn(self, conn: socket.socket, params, data, commtype):
        start_fn("get_handler_subconn")

        #! ALWAYS ASSUME conn IS THE SUBCONN

        if commtype == RW.READ:
            # only read from sending socket if waiting for connection (SENTPORT)
            match self.state:
                case GetCmdState.CONNECT:
                    # listen for connection
                    # assume self.subconn is the listening socket

                    # set subconn to blocking and listen
                    self.subconn.settimeout(5)

                    logger.debug("Listening for connection")
                    self.subconn.listen()

                    newconn, addr = self.subconn.accept()

                    logger.debug(f"Got new connection {addr}")

                    newdata = ConnData(ConnType.TRANSFER, addr, None, self)

                    # replace old connection with new one
                    # don't close it here, will be closed on processing
                    oldconn = self.subconn
                    self.subconn = newconn

                    # once connection received, change state
                    self.state = GetCmdState.SENDING

                    end_fn("get_handler_subconn")
                    return HandlerResult.REPLACE, (oldconn, (newconn, newdata))
        
        elif commtype == RW.WRITE:
            match self.state:
                case GetCmdState.SENDING:
                    b = self.file.read(self.blocksize)

                    self.sent += conn.send(b)

                    if self.sent >= self.totalsize:
                        self.state = GetCmdState.COMPLETE
                        self.file.close()

        end_fn("get_handler_subconn")
        return HandlerResult.OK, None
