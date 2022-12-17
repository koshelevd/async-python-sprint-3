import asyncio

from utils import ServerSettings


class Client:
    def __init__(self, host: str = ServerSettings.DEFAULT_HOST,
                 port: int = ServerSettings.DEFAULT_PORT):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    async def start(self):
        """Start client."""
        self.reader, self.writer = await asyncio.open_connection(self.host,
                                                                 self.port)
        await asyncio.gather(self.send_message(), self.read_message())

    async def send_message(self):
        """Send message to server."""
        while True:
            message = input()
            self.writer.write(message.encode())
            await self.writer.drain()
            await asyncio.sleep(1)

    async def read_message(self):
        """Read message from server."""
        while True:
            if message := await self.reader.read(1024):
                print(message.decode())
                await asyncio.sleep(1)


if __name__ == '__main__':
    client = Client()
    asyncio.run(client.start())
