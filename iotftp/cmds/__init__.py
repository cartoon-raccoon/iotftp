from abc import ABC, abstractmethod
import socket

class BaseCommandHandler(ABC):
    @abstractmethod
    def handle(self, conn: socket.socket, params, data, commtype):
        """
        Handle the main connection.

        A handler function always takes 4 parameters:
        conn: the connection to be handled.
        params: the parameters the server is operating under, 
            NOT the parameters of the command being run
        data: the data associated with the connection.
        commtype: whether the connection is open for reading or writing.

        A handler function should return two items:
        restype: the result type. This can be OK, DONE, NEWCONN, REPLACE, or ERR.
        res: the data associated with the result type. This differs according
        with the result type:
        - OK: None.
        - DONE: None.
        - NEWCONN: The socket to be registered as a subconnection.
        - REPLACE, a tuple (old_conn, (new_conn, new_data)).
        - ERR: A CommandError.
        """
        pass

    @abstractmethod
    def handle_subconn(self, conn: socket.socket, params, data, commtype):
        """
        Handle the subconnection for reading and writing.

        All conventions on handle() apply to this function.
        """
        pass
