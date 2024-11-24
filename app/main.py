import logging
import asyncio
import argparse


from app.server import (
    Address,
    CommandHandler,
    Server
)


logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)



    

async def main():
    parser = argparse.ArgumentParser(description="Redis-like server with RDB persistence.")
    parser.add_argument("--dir", type=str, default="/tmp" , help="Directory to store RDB files.")
    parser.add_argument("--dbfilename", type=str, default="dump.rdb", help="Name of the RDB file.")
    args = parser.parse_args()

    # Initialize CommandHandler with configuration parameters
    command_handler = CommandHandler(config={
        "dir": args.dir,
        "dbfilename": args.dbfilename,
    })

    # Start the server
    server = Server(Address('localhost', 6379), command_handler)
    try:
        await server.run()
    except asyncio.CancelledError:
        log.info("Server shutdown initiated.")

if __name__ == "__main__":
    asyncio.run(main())
