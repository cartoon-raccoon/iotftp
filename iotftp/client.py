from socket import socket, AF_INET, SOCK_STREAM
import os
import logging
import time

logger = logging.getLogger()

from iotftp.utils import *

class ServerError(Exception):
    """
    Error that has occurred on the server.
    """
    def __init__(self, string):
        self.string = string

    def __repr__(self):
        return self.string

class UnknownWelcome(Exception):
    """
    Raised when the welcome message received is not as expected.
    """

class IoTFTPClient:
    def __init__(self, ipaddr, port, encoding):
        self.ipaddr = ipaddr
        self.port = port
        self.encoding = encoding

    def parse_welcome_msg(self, s):
        """
        Reads in data from the connection and parses it into welcome info
        """
        dat = s.recv(512)
        if not dat:
            #todo: return error
            pass
        
        welcome = dat.split(DELIMITER)

        if welcome[0] != b"HI":
            raise UnknownWelcome()

        ver = welcome[1].decode(self.encoding)
        pwd = welcome[2].decode(self.encoding)
        user = welcome[3].decode(self.encoding)
        euid = int(welcome[4].decode(self.encoding))

        return (ver, pwd, user, euid)

    def determine_err(self, errb):
        match errb[0:3]:
            case "301":
                return ServerError("[301] Permission denied")
            case "302":
                return ServerError("[302] No such file or directory")
            case "303":
                return ServerError("[303] Not a directory")
            case "304":
                return ServerError("[304] File is currently in use")
            case "305":
                return ServerError("[305] Unsupported command")
            case "306":
                return ServerError("[306] Invalid arguments specified")
            case "307":
                return ServerError("[307] File already exists on server")
            case "308":
                return ServerError("[308] Unknown error")
            case "309":
                return ServerError("[309] Is a directory")
    
    def eval_result(self, resb, success_msg):
        """
        Evaluates the success of a command from a bytes object.
        This should be the bytes received from the server.

        Also accepts a success message to print on success.
        """
        if resb == RES_OK:
            logger.debug(success_msg)
        elif len(resb) > 0 and resb[0] == b"3":
                raise self.determine_err(resb.decode(self.encoding))
        else:
            logger.error(f"[ERR] Unknown server response: {resb}")



    def get(self, filename):

        abspath = os.path.abspath(filename)
        if os.path.exists(abspath):
            raise FileExistsError(abspath)
        
        with socket(AF_INET, SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((self.ipaddr, self.port))

            _ = self.parse_welcome_msg(s)

            # construct and send command
            args = [ b"GET", bytes(filename, self.encoding) ]
            s.send(DELIMITER.join(args))

            # receive command parameters
            params = s.recv(32)
            if not params:
                raise ConnectionResetError(s)
            
            params = params.decode(self.encoding)

            if not params.startswith("200 AIGT"):
                s.send(ACKNOW)
                raise self.determine_err(params)

            params = params.split(DELIMITER.decode(self.encoding))
            port, size = int(params[1]), int(params[2])

            print(f"[*] Reading {size} bytes from port {port}")

            s.send(ACKNOW)

            s2 = socket(AF_INET, SOCK_STREAM)

            # attempt to connect 5 times; if not, return error
            i = 0
            while True:
                try:
                    s2.connect((self.ipaddr, port))
                except OSError as e:
                    i += 1
                    if i < 5:
                        time.sleep(0.5)
                        continue
                    else:
                        raise e
                else:
                    break

            with s2:
                s2.settimeout(5)
                f = open(filename, "wb")
                inb, recved = bytes(), 0
                bs = get_blocksize(size)

                while recved < size:
                    inb = s2.recv(bs)
                    recved += len(inb)
                    f.write(inb)

                f.close()

            s.send(ACKNOW)
            d = s.recv(8)

        self.eval_result(d, f"[*] File transfer successful: {recved} bytes received")

    def put(self, filename):
        abspath = os.path.abspath(filename)
        if not os.path.exists(abspath):
            raise FileNotFoundError(abspath)

        with socket(AF_INET, SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((self.ipaddr, self.port))

            _ = self.parse_welcome_msg(s)

            size = os.path.getsize(abspath)
            
            args = [
                b"PUT",
                bytes(filename, self.encoding),
                bytes(str(size), self.encoding),
            ]

            s.send(DELIMITER.join(args))

            params = s.recv(32)
            if not params:
                raise ConnectionResetError(s)
            
            params = params.decode(self.encoding)

            if not params.startswith("200 AIGT"):
                s.send(ACKNOW)
                raise self.determine_err(params)

            params = params.split(DELIMITER.decode(self.encoding))
            port = int(params[1])

            logger.debug(f"[*] Sending {size} bytes on port {port}")

            s.send(ACKNOW)

            s2 = socket(AF_INET, SOCK_STREAM)

            i = 0
            while True:
                try:
                    s2.connect((self.ipaddr, port))
                except OSError as e:
                    i += 1
                    if i < 5:
                        time.sleep(0.5)
                        continue
                    else:
                        raise e
                else:
                    break
            
            with s2:
                s2.settimeout(5)
                f = open(filename, "rb")
                sent = 0
                bs = get_blocksize(size)

                while sent < size:
                    outb = f.read(bs)
                    out = s2.send(outb)
                    sent += out
                
                f.close()

            d = s.recv(8)

        self.eval_result(d, f"[*] File transfer successful: {sent} bytes sent")

    def delete(self, filename):
        with socket(AF_INET, SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((self.ipaddr, self.port))

            _ = self.parse_welcome_msg(s)

            # construct and send command
            args = [ b"DEL", bytes(filename, self.encoding) ]
            s.send(DELIMITER.join(args))

            res = s.recv(8)
            
        self.eval_result(res, "[*] Command successful")

    def pwd(self):
        pass

    def lsd(self):
        pass

    def cwd(self, dirname):
        pass

    def bye(self):
        with socket(AF_INET, SOCK_STREAM) as s:
            s.connect((self.ipaddr, self.port))

            _ = self.parse_welcome_msg(s)

            s.send(b"BYE")

            s.settimeout(5)
            res = s.recv(8)
        
        self.eval_result(res, "[*] Command successful")