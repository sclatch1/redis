import socket  # noqa: F401
import logging
import asyncio

from app.server import (
    Address,
    CommandHandler,
    Server
)


logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)



    

async def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")
    
    server_addr = Address('localhost', 6379)
    command_handler = CommandHandler()
    server = Server(server_addr, command_handler)

    await server.run()
    
    

if __name__ == "__main__":
    asyncio.run(main())
