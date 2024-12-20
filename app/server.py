import socket
import logging
from dataclasses import dataclass, field
import asyncio
from typing import List, Dict

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

DELIMITER = "\r\n"

@dataclass
class Address:
    host: str
    port: int

@dataclass
class CommandHandler:
    """Handles Redis-like commands."""
    
    store: Dict[str,str] = field(default_factory=dict)
    expirations: Dict[str, int] = field(default_factory=dict)  # Stores expiration times in milliseconds.
    config: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Automatically maps methods starting with 'cmd_' to commands."""
        self.commands = {
            method_name[4:]: getattr(self, method_name)
            for method_name in dir(self)
            if callable(getattr(self, method_name)) and method_name.startswith("cmd_")
        }

    def execute(self, command_name: str, args: List[str]) -> str:
        """Executes a command if it exists."""
        command = self.commands.get(command_name.lower())
        if not command:
            return "-ERR unknown command\r\n"
        try:
            return command(args)
        except Exception as e:
            log.error(f"Error executing command {command_name}: {e}")
            return "-ERR command execution failed\r\n"
    
    def _is_expired(self, key: str) -> bool:
        if key not in self.expirations:
            return False
        current_time = asyncio.get_event_loop().time() * 1000 # current time in milliseconds
        if current_time >= self.expirations[key]:
            del self.expirations[key]
            del self.store[key]
            return True
        return False
    
    def cmd_config(self, args: List[str]) -> str:
        """Handles the CONFIG GET commmand."""
        if len(args) != 2 or args[0].lower() != "get":
            return "-ERR wrong number of arguments for 'config' command\r\n"
        
        parameter = args[1].lower()
        if parameter not in self.config:
            return "*0\r\n"
        
        value = self.config[parameter]
        return f"*2\r\n${len(parameter)}\r\n{parameter}\r\n${len(value)}\r\n{value}\r\n"

    def cmd_ping(self, args: List[str]) -> str:
        """Handles the PING command."""
        return "+PONG\r\n"

    def cmd_echo(self, args: List[str]) -> str:
        """Handles the ECHO command."""
        if not args:
            return "-ERR wrong number of arguments for 'echo' command\r\n"
        return f"${len(args[0])}\r\n{args[0]}\r\n"

    def cmd_set(self, args: List[str]) -> str:
        """Handles the SET command (mocked storage)."""
        if len(args) < 2:
            return "-ERR wrong number of arguments for 'set' command\r\n"
        key, value = args[0], args[1]
        self.store[key] = value
        # Check for optional PX argument
        if len(args) > 2:
            option = args[2].lower()
            if option == "px" and len(args) > 3:
                try:
                    expiry = int(args[3])
                    current_time = asyncio.get_event_loop().time() * 1000  # Current time in milliseconds
                    self.expirations[key] = current_time + expiry
                except ValueError:
                    return "-ERR PX requires a valid integer\r\n"

        return "+OK\r\n"

    def cmd_get(self, args: List[str]) -> str:
        """Handles the GET command (mocked retrieval)."""
        if len(args) < 1:
            return "-ERR wrong number of arguments for 'get' command\r\n"
        key = args[0]

        if self._is_expired(key):
            return "$-1\r\n"
    
        if key not in self.store:
            return "$-1\r\n"  # RESP nil for missing keys
        value = self.store[key]
        return f"${len(value)}\r\n{value}\r\n"


class CloseServer(Exception):
    pass

class CloseClient(Exception):
    pass


@dataclass
class Server:
    address: Address
    command_handler: CommandHandler

    async def run(self):
        """Start the server socket and listen to incoming client connections."""
        server = await asyncio.start_server(self.handle_client, self.address.host, self.address.port)
        addr = server.sockets[0].getsockname()
        log.info(f"Server listening on {addr}")
        try:
            await server.serve_forever()
        except asyncio.CancelledError:
            log.info("Server shutting down")
            server.close()
            await server.wait_closed()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handles incoming messages from a client."""
        address = writer.get_extra_info('peername')
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    log.info(f"Connection closed by {address}")
                    break
                message = data.decode('utf-8')
                log.debug(f"Received message from {address}: {message}")
                await self.handle_message(message, writer)
        except Exception as e:
            log.error(f"Error handling message from {address}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            log.info(f"Closed connection from {address}")

    async def handle_message(self, message: str, writer: asyncio.StreamWriter):
        """Process messages using the command handler."""
        try:
            args = self.parse_redis_protocol(message)
            if not args:
                raise ValueError("Empty command")
            command = args[0]
            response = self.command_handler.execute(command, args[1:])
            writer.write(response.encode('utf-8'))
            await writer.drain()
        except ValueError as e:
            log.error(f"Error parsing message: {e}")
            writer.write(b"-ERR invalid command\r\n")
            await writer.drain()

    def parse_redis_protocol(self, data: str) -> List[str]:
        """Parses Redis protocol commands and arguments."""
        lines = data.strip().split(DELIMITER)
        if not lines or lines[0][0] != '*':
            raise ValueError("Invalid RESP data")
        num_elements = int(lines[0][1:])
        if num_elements <= 0 or len(lines) < 2 * num_elements + 1:
            raise ValueError("Incomplete RESP data")

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
