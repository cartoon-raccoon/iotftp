import os
import sys
import logging
import socket
import selectors

from iotftp.cmds import *
from iotftp.cmds.get import GetCmdHandler
from iotftp.cmds.delete import DelCmdHandler
from iotftp.cmds.put import PutCmdHandler
from iotftp.utils import *

logger = logging.getLogger()

class IoTFTPServer:
    """
    The core class of this module.
    """

    # class attributes
    host = "127.0.0.1"
    delimiter = b"\n"
    startmsg = b"HI"

    def __init__(self, ipaddr, port, encoding):
        if not validate_ip(ipaddr):
            raise InvalidIPException()
        # the port listening on
        self.port = port
        # all information needed for the user
        self.cwd = os.getcwd()
        self.user = os.getlogin()
        self.euid = os.geteuid()
        # the selector to manage incoming connections
        self.sel = selectors.DefaultSelector()
        # number of active connections
        self.activecount = 0
        # mapping of connections to subconnections
        self.conns = dict()
        # the encoding to use for protocol commands
        self.encoding = encoding
        # track whether the server should be running
        self.running = False
        # the listening socket
        self.listensock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        IoTFTPServer.host = ipaddr

    def start(self):
        self.listensock.bind((IoTFTPServer.host, self.port))
        self.listensock.setblocking(False)
        self.listensock.listen()
        self.sel.register(self.listensock, selectors.EVENT_READ, data=None)
    
    def stop(self):
        if self.running:
            self.running = False
        
        self.listensock.close()
        self.sel.close()
    
    def run(self):
        logger.debug("[*] Running server")
        self.running = True
        while self.running:
            logger.debug("**************** Event Loop Start ****************")
            events = self.sel.select(timeout=None)
            for k, m in events:
                if k.data is None:
                    try:
                        self.accept(k)
                    except ConnectionResetError:
                        logger.debug(f"[!] Connection reset on new connection")
                        continue
                else:
                    try:
                        self.service_conn(k, m)
                    except ConnectionResetError:
                        logger.debug(f"[{k.data.addr}] Connection reset by peer")
                        self.close_all(k.fileobj, k.data)
                    except ConnClosedErr:
                        logger.debug(f"[{k.data.addr}] Connection closed by peer")
                        self.close_all(k.fileobj, k.data)
                    except BrokenPipeError:
                        logger.debug(f"[{k.data.addr}] Connection closed on write")
                        self.close_all(k.fileobj, k.data)
                    except TimeoutError:
                        logger.debug(f"[{k.data.addr}] Connection timed out, closing")
                        self.close_all(k.fileobj, k.data)
            logger.debug("**************** Event Loop End   ****************")
        self.stop()
            
    def accept(self, key):
        """
        Accepts a main connection and registers it with the selector pool.
        """
        conn, addr = key.fileobj.accept()
        logger.debug(f"[*] Got connection from {addr}")
        self.activecount += 1

        # send the welcome message
        self.welcome(conn)

        # set the socket to nonblocking
        conn.setblocking(False)

        self.conns[conn] = []

        # initialize connection metadata and register it
        dat = ConnData(
            ConnType.COMMAND, 
            addr, ConnState.NON, None
        )
        self.sel.register(conn, RWMASK, data=dat)

    def welcome(self, conn):
        """
        Sends the welcome message and relevant information.
        """
        start_fn("welcome")
        delim = IoTFTPServer.delimiter

        send = [
            IoTFTPServer.startmsg,
            bytes(VERSION, self.encoding),
            bytes(self.cwd, self.encoding),
            bytes(self.user, self.encoding),
            bytes(str(self.euid), self.encoding),
        ]

        conn.send(delim.join(send))
        end_fn("welcome")

    def close(self, conn):
        """
        Closes a given connection and all its subconnections.
        """
        logger.debug(f"[*] Closing connection {conn}")

        # unregister and close all subconnections
        for subconn in self.conns.pop(conn, []):
            self.sel.unregister(subconn)
            subconn.close()
        
        self.sel.unregister(conn)
        conn.close()

        # decrement number of active connections
        self.activecount -= 1

    def close_all(self, conn, data):
        """
        If a subconn is given, looks up and closes its main connection.
        Else, just runs close().
        """

        if data.is_subconn():
            mainconn = self.lookup_conn(conn)
        else:
            mainconn = conn
        
        self.close(mainconn)

    def add_subconn(self, mainconn, subconn, data):
        # store the subconnection in the conns dict
        logger.debug(f"Associating subconn {subconn} with mainconn {mainconn}")
        self.conns[mainconn].append(subconn)
        self.sel.register(subconn, RWMASK, ConnData(
            ConnType.TRANSFER,
            data.addr,
            None,
            data.handler,
        ))

    def del_subconn(self, subconn):
        logger.debug(f"Deleting subconn {subconn}")
        
        mainconn = self.lookup_conn(subconn)
        self.conns[mainconn].remove(subconn)
        self.sel.unregister(subconn)
        subconn.close()

    def evalcmd(self, conn, data):
        """
        Evaluates a command sent by a client and prepares the connection
        to be handled by its respective handler.
        """
        start_fn("evalcmd")
        delim = IoTFTPServer.delimiter
        # assume conn can be read from
        cmd = conn.recv(512)
        if not cmd:
            raise ConnClosedErr()
        
        cmd = cmd.split(delim)
        for i in range(len(cmd)):
            cmd[i] = cmd[i].decode(self.encoding)
        data.cmd = cmd

        command = cmd[0]

        match command:
            case "GET":
                logger.debug("Got GET command")
                if len(cmd) != 2:
                    logger.debug("Error: did not receive exactly 2 arguments")
                    data.state = ConnState.E306

                    end_fn("evalcmd")
                    return

                args = cmd[1]
                data.state = ConnState.GET
                data.handler = GetCmdHandler(args)
            case "PUT":
                logger.debug("Got PUT command")
                if len(cmd) != 3:
                    logger.debug("Error: received not exactly 3 arguments")
                    data.state = ConnState.E306

                    end_fn("evalcmd")
                    return
                
                args = cmd[1:]
                data.state = ConnState.PUT
                data.handler = PutCmdHandler(args)
            case "DEL":
                logger.debug("Got DEL command")
                if len(cmd) != 2:
                    logger.debug("Error: received not exactly 2 arguments")
                    data.state = ConnState.E306

                    end_fn("evalcmd")
                    return
                
                args = cmd[1]
                data.state = ConnState.DEL
                data.handler = DelCmdHandler(args)
            case "PWD":
                logger.debug("Got PWD Command")
                # data.state = ConnState.PWD
                data.state = ConnState.E305
            case "LSD":
                logger.debug("Got LSD command")
                # data.state = ConnState.LSD
                data.state = ConnState.E305
            case "CWD":
                logger.debug("Got CWD command")
                # data.state = ConnState.CWD
                data.state = ConnState.E305
            case "BYE":
                logger.debug("Got BYE command")
                data.state = ConnState.BYE
            case _:
                logger.debug(f"Got {command}")
        end_fn("evalcmd")
    
    def service_conn(self, key, mask):
        """
        Handles a connection ready for reading or writing.
        """
        start_fn("service_conn")
        conn = key.fileobj
        data = key.data

        logger.debug(f"Servicing connection {data.addr}")

        logger.debug(data.state)

        if conn.fileno() < 0:
            return

        if mask & selectors.EVENT_READ:
            logger.debug("open for reading")
            if data.state == ConnState.NON:
                # eval the command that the connection wants
                self.evalcmd(conn, data)
            elif data.state == ConnState.ACK:
                # if an error has occurred, read in acknowledgement
                logger.debug("reading in acknowledgement")
                dat = conn.recv(8)
                if not dat:
                    raise ConnClosedErr()
                
                if dat == ACKNOW:
                    logger.debug("ack received, resetting connection")
                    data.reset()
                else:
                    pass #! this is an error condition
            elif data.handler is not None:
                if data.is_subconn():
                    ty, res = data.handler.handle_subconn(conn, self.params(), data, RW.READ)
                else:
                    ty, res = data.handler.handle(conn, self.params(), data, RW.READ)
                self.process_handler_result(ty, res, conn, data)
                
        logger.debug(data.state)
        if conn.fileno() < 0:
            return

        if mask & selectors.EVENT_WRITE:
            logger.debug("open for writing")

            # if state is err, implies that the connection is a main conn,
            # since state for subconn is always None
            if not data.is_subconn() and data.state.is_err():
                logger.debug(f"[*] Sending error message for error {data.state}")
                conn.send(data.state.value.value)
                data.state = ConnState.ACK
            elif data.state == ConnState.BYE:
                logger.debug("Handling BYE command")
                conn.send(RES_OK)
                
                self.running = False
            elif data.handler is not None:
                if data.is_subconn():
                    ty, res = data.handler.handle_subconn(conn, self.params(), data, RW.WRITE)
                else:
                    ty, res = data.handler.handle(conn, self.params(), data, RW.WRITE)
                self.process_handler_result(ty, res, conn, data)
        else:
            logger.debug("Unknown event mask")
            return
        end_fn("service_conn")

    def lookup_conn(self, subconn):
        """
        Looks up the main connection associated with a subconnection.
        """
        start_fn("lookup_conn")

        for k in self.conns:
            if subconn in self.conns[k]:
                logger.debug(f"Got main conn {k}")
                return k
        end_fn("lookup_conn")

    def process_handler_result(self, restype, res, conn, data):
        """
        Processes the handler result accordingly.
        """
        start_fn("process_handler")

        if restype is None:
            logger.error("[ERR] Received invalid handler result")
            data.state = ConnState.E308
            return

        if restype.is_err():
            logger.debug("[*] Restype is error, handling")
            if data.is_subconn():
                # get the data associated with the main conn
                c = self.lookup_conn(conn)
                dat = self.sel.get_key(c).data
                dat.state = ConnState.from_handler_result(restype)
            # set state to error and return
            # sending the error will be handled by service_conn
            else:
                data.state = ConnState.from_handler_result(restype)
        else:
            match restype:
                case HandlerResult.OK:
                    # 200 AIGT sent in handler
                    logger.debug("Received OK, doing nothing")
                case HandlerResult.NEWCONN:
                    logger.debug("Received NEWCONN, registering new subconn")
                    self.add_subconn(conn, res, data)
                case HandlerResult.REPLACE:
                    logger.debug("Received REPLACE, replacing old subconn")
                    if data.is_subconn():
                        mainconn = self.lookup_conn(conn)
                    else:
                        mainconn = conn
                    self.del_subconn(res[0])
                    self.add_subconn(mainconn, res[1][0], res[1][1])
                case HandlerResult.DONE:
                    logger.debug("Received DONE, closing subconn")
                    if data.is_subconn():
                        self.del_subconn(conn)

        end_fn("process_handler")
        return

    def respond(self, conn, response):
        """
        Convenience function to respond to a command.
        Usually used for sending errors.
        """
        conn.send(response)

    def params(self) -> ServerParams:
        """
        Returns the current server parameters.
        """
        return ServerParams(
            IoTFTPServer.host,
            self.port,
            self.cwd,
            self.user,
            self.euid,
            self.activecount,
            IoTFTPServer.delimiter,
            self.encoding
        )