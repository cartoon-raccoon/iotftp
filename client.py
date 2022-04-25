import iotftp

# this is a test client for the iotftp server library.

def main():
    print("running main")
    client = iotftp.IoTFTPClient("127.0.0.1", 65432, "ascii")

    client.put("testelf")
    client.get("test2")
    client.delete("test2")



main()
    
