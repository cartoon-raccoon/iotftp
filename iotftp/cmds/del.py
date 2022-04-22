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
