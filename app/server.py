import socket
import logging
from contextlib import contextmanager
from dataclasses import dataclass
import asyncio

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

#@contextmanager
async def run_server(address: Address):
    """Start the server socket and listen to incoming client connections"""
    #server_socket = socket.create_server((address.host, address.port), reuse_port=True)
    server = await asyncio.start_server(handle_client, address.host, address.port)
    addr = server.sockets[0].getsockname()
    log.info(f"Server listening on {addr}")
    try:
        await server.serve_forever()
    except asyncio.CancelledError:
        log.info("server shutting down")
        server.close()
        await server.wait_closed()

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """handles incoming messages from a client, responding with PONG to PING commands"""
    address = writer.get_extra_info('peername')
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                log.info(f"COnnection closed by {address}")
                break
            message = data.decode('utf-8')
            log.debug(f"received message from {address}: {message}")
            await handle_message(message, writer)
    except Exception as e:
        log.error(f"error handling message from {address}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()
        log.info(f"closed connection from {address}")
    
        
async def handle_message(message: str, writer: asyncio.StreamWriter):
    """Handle the PING messafe and sends PONG response"""
    log.info(f"got {message.strip().lower()} in handl_message")
    if "ping" in message.strip().lower():
        log.debug(f"responding {message} with PONG")
        writer.write(b'+PONG\r\n')
        await writer.drain()
    else:
        log.error(f"unknown message: {message}")

