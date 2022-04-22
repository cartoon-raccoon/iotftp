# iotsuite file transfer protocol

a custom protocol that provides only the needed functionality for iot-suite and also facilitates the functionality of iot-suite
the server is an transient program, not a daemon, that exists only as long as it is needed
it is only started after execution and data collection is done and is only used to transfer execution traces out of the VMs
however, minimal additional functionality is provided (sending a file to the VM, changing working directory, etc) for user interaction

client always initiates connection and is responsible for disconnecting
server responds with information:

- `HI`
- current directory (always fully qualified path)
- user currently running as
- effective user id

and then awaits command
client acknowledges and sends command

commands
PUT - Transfer a file to the server `[PATH, FILE SIZE]`
    server response - 200 OK, port number to use
    client sends an ACK then connects to server on that port
    client sends a magic byte sequence on that port and initiates file transfer
    once FILE SIZE number of bytes has been read, server sends 200 OK on initial port
    client responds with ACK
GET - Get a file from the server `[PATH]`
    server response - 200 OK, port number to use, file size
    client sends an ACK then connects to server on that port
    server sends 200 OK and a magic byte sequence to initiate file transfer
    once FILE SIZE number of bytes has been read, client sends ACK again to confirm file transferred
    server responds with 200 OK
DEL - Delete a file on the server
    server response 200 OK
    server then deletes file
PWD - Get the working directory
    server response 200 OK, path
LSD - List directory `[PATH]`
    server response 200 OK, list of files separated by thing
CWD - Change working directory `[PATH]`
    server response 200 OK
BYE - End the connection (this also tells the server to exit)
    server response 200 OK
in case of error
    client sends ACK
    server returns to awaiting commands

server responses

```text
200 AIGT
300+
    301 PERM (permission denied)
    302 NONE (no such file or directory)
    303 NDIR (not a directory (only received with CWD or LSD))
    304 LOCK (the file is currently in use by another connection)
    305 UNSP (unsupported feature or command (usually unimplemented))
    306 ARGS (incorrect or wrong number of arguments)
```

client responses

```text
100 ACK
```
