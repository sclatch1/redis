import socket
import logging
from dataclasses import dataclass
import asyncio

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

DELIMITER = "\r\n"

@dataclass
class Address:
    host: str
    port: int

class CloseServer(Exception):
    pass

class CloseClient(Exception):
    pass

async def run_server(address: Address):
    """Start the server socket and listen to incoming client connections"""
    server = await asyncio.start_server(handle_client, address.host, address.port)
    addr = server.sockets[0].getsockname()
    log.info(f"Server listening on {addr}")
    try:
        await server.serve_forever()
    except asyncio.CancelledError:
        log.info("Server shutting down")
        server.close()
        await server.wait_closed()

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Handles incoming messages from a client, responding with commands"""
    address = writer.get_extra_info('peername')
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                log.info(f"Connection closed by {address}")
                break
            message = data.decode('utf-8')
            log.debug(f"Received message from {address}: {message}")
            await handle_message(message, writer)
    except Exception as e:
        log.error(f"Error handling message from {address}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()
        log.info(f"Closed connection from {address}")

def parse_redis_protocol(data: str):
    """Parses Redis protocol commands and arguments"""
    lines = data.strip().split(DELIMITER)
    if not lines or lines[0][0] != '*':
        raise ValueError("Invalid RESP data")

    num_elements = int(lines[0][1:])
    if num_elements <= 0 or len(lines) < 2 * num_elements + 1:
        raise ValueError("Incomplete RESP data")

    # Extract arguments
    args = []
    i = 1
    while i < len(lines):
        if lines[i][0] == '$':
            length = int(lines[i][1:])
            args.append(lines[i + 1])
            i += 2
        else:
            raise ValueError("Invalid RESP argument format")
    return args

async def handle_message(message: str, writer: asyncio.StreamWriter):
    """Handle Redis protocol messages and commands"""
    try:
        args = parse_redis_protocol(message)
        if not args:
            raise ValueError("Empty command")

        command = args[0].lower()
        if command == "ping":
            writer.write(b"+PONG\r\n")
        elif command == "echo":
            if len(args) < 2:
                writer.write(b"-ERR wrong number of arguments for 'echo' command\r\n")
            else:
                response = f"${len(args[1])}\r\n{args[1]}\r\n".encode('utf-8')
                writer.write(response)
        else:
            writer.write(b"-ERR unknown command\r\n")
        await writer.drain()
    except ValueError as e:
        log.error(f"Error parsing message: {e}")
        writer.write(b"-ERR invalid command\r\n")
        await writer.drain()
