import sys
import logging

from iotftp import IoTFTPServer, InvalidIPException

logger = logging.getLogger()
logger.setLevel(logging.WARN)
handler = logging.StreamHandler()
logger.addHandler(handler)

def main():
    ipaddr, port = sys.argv[1], int(sys.argv[2])

    if len(sys.argv) > 3 and sys.argv[3] == "-v":
        logger.setLevel(logging.DEBUG)
    
    try:
        server = IoTFTPServer(ipaddr, port, 'ascii')
    except InvalidIPException:
        print("[ERROR] Invalid ip given.")
    server.start()
    try:
        server.run()
    except KeyboardInterrupt:
        print("Received Ctrl-C, closing")
    finally:
        server.stop()

if __name__ == "__main__":
    main()