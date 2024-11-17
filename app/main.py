import socket  # noqa: F401
import logging
import asyncio

from app.server import (
    Address,
    run_server
)


logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)



    

async def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")
    
    server_addr = Address('localhost', 6379)


    await run_server(server_addr)

    
    
    

if __name__ == "__main__":
    asyncio.run(main())
