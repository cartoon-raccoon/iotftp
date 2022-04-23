from socket import socket, AF_INET, SOCK_STREAM
import os
import logging

logger = logging.getLogger()

from iotftp.utils import *

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

        pwd = welcome[1].decode(self.encoding)
        user = welcome[2].decode(self.encoding)
        euid = int(welcome[3].decode(self.encoding))

        return (pwd, user, euid)

    def get(self, filename):

        abspath = os.path.abspath(filename)
        if os.path.exists(abspath):
            # todo: make this return error
            return
        
        with socket(AF_INET, SOCK_STREAM) as s:
            s.connect((self.ipaddr, self.port))

            _ = self.parse_welcome_msg(s)

            # construct and send command
            args = [ b"GET", bytes(filename, "ascii") ]
            s.send(DELIMITER.join(args))

            # receive command parameters
            params = s.recv(32).decode(self.encoding)

            if not params.startswith("200 AIGT"):
                # todo: determine error type, handle it, and raise err
                s.send(ACKNOW)
                return

            params = params.split(DELIMITER)
            port, size = int(params[1]), int(params[2])

            logger.debug(f"[*] Reading {size} bytes from port {port}")

            s.send(ACKNOW)

            s2 = socket(AF_INET, SOCK_STREAM)
            while True:
                try:
                    s2.connect((self.ipaddr, port))
                except:
                    continue
                else:
                    break

            with s2:
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

            if d == RES_OK:
                logger.debug(f"[*] File transfer successful: {recved} bytes received")
            
            # todo: do check for error

    def put(self, filename):
        pass

    def delete(self, filename):
        pass

    def pwd(self):
        pass

    def lsd(self):
        pass

    def cwd(self, dirname):
        pass

    def bye(self):
        pass