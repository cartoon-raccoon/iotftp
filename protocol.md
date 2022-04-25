# IoTSuite File Transfer Protocol

IoTFTP is a custom protocol that provides only the needed functionality for IoTSuite and also facilitates the functionality of IoTSuite.

The server is an transient program, not a daemon, that exists only as long as it is needed. It is only started after execution and data collection is done and is only used to transfer execution traces out of the VMs. However, minimal additional functionality is provided (sending a file to the VM, changing working directory, etc) for user interaction.

## Connection Initiation

The client always initiates the connection and is responsible for disconnecting. The server will close the connection when it detects the client has closed the socket on its side.

On successful execution of a command, the server always sends the final transmission, which will always be `200 AIGT`. In case of any error, the server will send an error code, and the client will always be the last to send a transmission which will always be `100 ACK`. All commands and responses will be sent via plaintext, including digits.

The server responds with the following information separated by a delimiter:

- `HI`
- protocol version ("V{version}")
- current directory (always fully qualified path)
- user currently running as
- effective user id

It then awaits a command, which the client then sends with the required arguments.

## Commands

*`PUT` - Transfer a file to the server `[PATH, FILE SIZE]`*

- server responds with `200 AIGT` and port number to use
- client sends `100 ACK` then connects to server on that port
- server sends `200 AIGT` on comms port, client then initiates file transfer
- once `FILE SIZE` number of bytes has been read, server sends `200 AIGT` on initial port
- client is then free to close both sockets

*`GET` - Get a file from the server `[PATH]`*
  
- server response - `200 AIGT`, port number to use, file size
- client sends an ACK then connects to server on that port
- server initiates file transfer once client is connected
- once FILE SIZE number of bytes has been read, client sends ACK again to confirm file transferred
- server responds with `200 AIGT`
- client is then free to close both sockets

*`DEL` - Delete a file on the server*

- server deletes file
- server response 200 OK

*`PWD` - Get the working directory*

- server response `200 AIGT`, path

*`LSD` - List directory `[PATH]`*

- server response 200 OK, number of bytes to be sent to client
- client sends an ack and then begins to receive bytes
- server sends list of files separated by delimiter

*`CWD` - Change working directory `[PATH]`*

- server response 200 OK

*`BYE` - End the connection (this also tells the server to exit)*

- server response 200 OK
  - the server only exits if the connection sending is the only one currently connected

in case of error:

- client sends ACK
- server returns to awaiting commands

## Server Responses

```text
200 AIGT
300+
    301 PERM (permission denied)
    302 NONE (no such file or directory)
    303 NDIR (not a directory (only received with CWD or LSD))
    304 LOCK (the file is currently in use by another connection)
    305 UNSP (unsupported feature or command (usually unimplemented))
    306 ARGS (incorrect or wrong number of arguments)
    307 EXST (file already exists)
    308 UNKW (unknown response)
    309 ISDR (is a directory)
```

## Client Responses

```text
100 ACK
```
