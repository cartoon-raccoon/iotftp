import socket
import os
import logging

from enum import Enum

from iotftp.cmds import BaseCommandHandler
from iotftp.utils import *
import iotftp

logger = logging.getLogger()

class DelCmdState(Enum):
    # raw connection, unhandled
    UNHANDLED = 0
    # completed, acknowledgement sent
    COMPLETE = 1

class DelCmdHandler(BaseCommandHandler):
    def __init__(self, args):
        self.state = DelCmdState.UNHANDLED
        self.args = args

    def handle(self, conn: socket.socket, params, data, commtype):
        start_fn("del_handler")

        if commtype == RW.READ:
            return HandlerResult.OK, None
            
        elif commtype == RW.WRITE:
            f = os.path.abspath(self.args)
            
            try:
                os.remove(f)
            except FileNotFoundError:
                return HandlerResult.E302, CommandError.ERR_NONE
            except PermissionError:
                return HandlerResult.E301, CommandError.ERR_PERM
            
            conn.send(RES_OK)

            return HandlerResult.DONE, None

    def handle_subconn(self, conn: socket.socket, params, data, commtype):
        pass
