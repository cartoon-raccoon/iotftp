import selectors
import logging
from enum import Enum
import netifaces as ni

from iotftp.cmds import BaseCommandHandler

RWMASK = selectors.EVENT_READ | selectors.EVENT_WRITE

# acknowledgement sent by client
ACKNOW = b"100 ACK"
# ok response sent by server
RES_OK   = b"200 AIGT"

BLOCKSIZE = 1024

logger = logging.getLogger()

def start_fn(name):
    logger.debug(f"========START {name}========")

def end_fn(name):
    logger.debug(f"======== END  {name}========")

def validate_ip(ipaddr):
    for iface in ni.interfaces():
        addrs = ni.ifaddresses(iface)[ni.AF_INET]
        for add in addrs:
            addr = add['addr']
            if addr == ipaddr:
                return True
    return False

class InvalidIPException(Exception):
    """
    An IP address that does not exist on the existing interfaces
    """

class ConnClosedErr(Exception):
    """
    A connection that has been closed by a client
    """

class CommandError(Enum):
    ERR_PERM = b"301 PERM"
    ERR_NONE = b"302 NONE"
    ERR_NDIR = b"303 NDIR"
    ERR_LOCK = b"304 LOCK"
    ERR_UNSP = b"305 UNSP"
    ERR_ARGS = b"306 ARGS"
    ERR_UNKW = b"307 UNKW"

class ConnState(Enum):
    # no command currently running
    NON = 0
    # running a get command
    GET = 1
    # running a put command
    PUT = 2
    # running a del command
    DEL = 3
    # running a cwd command
    CWD = 4
    # running a bye command
    BYE = 5
    # error running command, response to be sent
    E301 = CommandError.ERR_PERM
    E302 = CommandError.ERR_NONE
    E303 = CommandError.ERR_NDIR
    E304 = CommandError.ERR_LOCK
    E305 = CommandError.ERR_UNSP
    E306 = CommandError.ERR_ARGS
    E307 = CommandError.ERR_UNKW
    # awaiting acknowledgement for error
    ACK = 12

    def is_err(self):
        return self.name[0] == "E"

    @classmethod
    def from_handler_result(cls, res):
        match res:
            case HandlerResult.E301:
                return ConnState.E301
            case HandlerResult.E302:
                return ConnState.E302
            case HandlerResult.E303:
                return ConnState.E303
            case HandlerResult.E304:
                return ConnState.E304
            case HandlerResult.E305:
                return ConnState.E305
            case HandlerResult.E306:
                return ConnState.E306
            case _:
                #? raise error?
                pass


class ConnType(Enum):
    """
    The type of connection in the selector pool.
    """
    # a connection for receiving commands.
    COMMAND = 0
    # a connection for sending data.
    TRANSFER = 1

class ConnData:
    """
    Metadata about the connection.

    If the type is COMMAND, all other fields will be populated.
    If the type is TRANSFER, only addr and handler will be populated.
    """
    def __init__(self, type, addr, state, handler: BaseCommandHandler):
        self.type = type
        # connection metadata such as IP and port
        self.addr = addr
        # current state of the connection
        self.state = state
        # any arguments for a command being run
        self.cmd = []
        # the handler for the command being run (if any)
        self.handler = handler

    def reset(self):
        self.state = ConnState.NON
        self.args = []
        self.handler = None

    def is_subconn(self):
        return self.type == ConnType.TRANSFER

class ServerParams:
    """
    Various params about the server.
    """

    def __init__(self, host, port, cwd, user, euid, active, delim, encoding):
        self.host = host
        self.port = port
        self.cwd = cwd
        self.user = user
        self.euid = euid
        self.active = active
        self.delim = delim
        self.encoding = encoding


class RW(Enum):
    READ = 0
    WRITE = 1

class HandlerResult(Enum):
    # handled properly but still in progress, no action required
    OK = 0
    # handled properly and complete, close all sockets involved
    DONE = 1
    # handled properly and a new socket required, add it to the pool
    NEWCONN = 2
    # received new connection to receive/send data, replace existing conn
    REPLACE = 3
    # error in handling, send error and close connection
    E301 = CommandError.ERR_PERM
    E302 = CommandError.ERR_NONE
    E303 = CommandError.ERR_NDIR
    E304 = CommandError.ERR_LOCK
    E305 = CommandError.ERR_UNSP
    E306 = CommandError.ERR_ARGS
    E307 = CommandError.ERR_UNKW

    def is_err(self):
        return self.name[0] == "E"

    