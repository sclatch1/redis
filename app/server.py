import socket
import logging
from contextlib import contextmanager
from dataclasses import dataclass

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

@dataclass
class Address:
    host: str
    port: int

class CloseServer(Exception):
    pass

class CloseClient(Exception):
    pass

@contextmanager
def make_server(address: Address):
    """Creates a server socket and binds it to the specified address"""
    server_socket = socket.create_server((address.host, address.port), reuse_port=True)
    server_socket.listen()
    log.info(f"Server listening on {address.host}:{address.port}")
    try:
        yield server_socket
    finally:
        server_socket.close()
        log.info("Server socket close")

def next_client(server_socket: socket.socket):
    """Yields new client connections from the server socket"""
    while True:
        try:
            conn, addr = server_socket.accept()
            log.info(f"New connection from {addr}")
            yield conn, addr
        except Exception as e:
            log.error(f"New connection from {addr}")
            raise CloseServer from e
        
def next_message(conn: socket.socket, address: tuple[str,int]):
    """Yields message received from the client socket"""
    while True:
        try:
            log.debug(conn)
            message = conn.recv(1024)
            if not message:
                log.info(f"Connection close by {address}")
                raise CloseClient("Client closed connection")
            yield message
        except CloseClient:
            log.info(f"Ending message reception from {address}")