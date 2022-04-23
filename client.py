import socket
import sys
import time

HOST = "127.0.0.1"
PORT = 65432

DELIM = b"\n"

# this is a test client for the iotftp server library.

def p64(i):
    return i.to_bytes(8, 'big')

def test_file_transfer(s):
    with open("test2", "rb") as f:
        msg = f.read()
        length = len(msg)
    
    s.connect((HOST, PORT))
    s.send(p64(length))
    dat = s.recv(4)
    if dat == b"OK":
        print("Length received by server, transmitting file now")
        s.sendall(msg)
        dat = s.recv(4)
        if dat == b"BYE":
            print("Successful")
        else:
            print(f"Not successful, received {dat}")
    else:
        print("Error")
        sys.exit(1)

def test_working_file_transfer(s: socket.socket):
    s.connect((HOST, PORT))
    dat = s.recv(512)
    print(dat)
    s.send(b"GET\ntestelf")
    dat2 = s.recv(32)
    
    print(dat2)

    params = dat2.split(DELIM)
    port = int(params[1].decode('ascii'))
    size = int(params[2].decode("ascii"))

    print(f"Reading {size} bytes from port {port}")

    s.send(b"100 ACK")

    time.sleep(1)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s2:

        f = open("recvedelf", "wb")
        inb, recved = bytes(), 0
        s2.connect((HOST, port))

        while recved < size:
            inb = s2.recv(1024)
            recved += len(inb)
            f.write(inb)
        
        f.close()

        print(recved)

    # send on the first socket
    s.send(b"100 ACK")

    d = s.recv(8)

    if d == b"200 AIGT":
        print("successful")

def test_broken_get(s: socket.socket):
    s.connect((HOST, PORT))
    dat = s.recv(512)
    print(dat)

    s.send(b"GET\ntest")

    dat2 = s.recv(16)
    print(dat2)

    if dat2 == b"302 NONE":
        print("successful")
    
    s.send(b"100 ACK")

def test_delete_cmd(s: socket.socket):
    s.connect((HOST, PORT))
    dat = s.recv(512)
    print(dat)

    s.send(b"DEL\ntest")

    dat2 = s.recv(32)

    if dat2 == b"302 NONE":
        s.send(b"100 ACK")

    print(dat2)

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        test_working_file_transfer(s)



main()
    
