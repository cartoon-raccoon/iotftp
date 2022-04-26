import logging
import sys

import iotftp

# this is a test client for the iotftp server library.

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
logger.addHandler(handler)

PROMPT = ">>> "

def parse_command(raw):

    # todo: do this properly thanks

    # args = []

    # buf = ""

    # for c in raw:
    #
    #     if c == "\"":

    return raw.split(" ")

def run(client, args):
    if len(args) < 1:
        return

    cmd = args[0].lower()
    
    if cmd == "get":
        client.get(args[1])
    elif cmd == "put":
        client.put(args[1])
    elif cmd == "del":
        client.delete(args[1])
    elif cmd == "bye":
        client.bye()


def main():
    ipaddr, port, encoding = sys.argv[1], int(sys.argv[2]), "ascii"
    client = iotftp.IoTFTPClient(ipaddr, port, encoding)
    
    while True:
        try:
            args = parse_command(input(PROMPT))
            run(client, args)
        except OSError as e:
            print(repr(e))
        except Exception as e:
            print(repr(e))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
    
