from socket import socket, AF_INET, SOCK_STREAM
import os

from iotftp.utils import *

class IoTFTPClient:
    def __init__(self, ipaddr, port):
        self.ipaddr = ipaddr
        self.port = port

    def parse_welcome_msg(self, s):
        """
        Reads in data from the connection and parses it into welcome info
        """
        dat = s.recv(512)
        if not dat:
            #todo: return error
            pass
        
        welcome = dat.split(DELIMITER)

        pwd = welcome[1]
        user = welcome[2]
        euid = welcome[3]

        return pwd, user, euid

    def get(self, filename):
        with socket(AF_INET, SOCK_STREAM) as s:
            s.connect((self.ipaddr, self.port))

            pwd, user, euid = self.parse_welcome_msg(s)

        pass

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