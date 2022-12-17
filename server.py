import asyncio
import logging
import sys
from asyncio.streams import StreamReader, StreamWriter
from collections import deque
from datetime import datetime as dt

from utils import Message, ServerSettings, User

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


class Server:
    def __init__(self, host: str = ServerSettings.DEFAULT_HOST,
                 port: int = ServerSettings.DEFAULT_PORT):
        self.host = host
        self.port = port
        self.users = {}
        self.logins = {}
        self.history = deque(maxlen=ServerSettings.MAX_MESSAGE_COUNT)

    async def save_message(self, message: str, user: User) -> None:
        """
        Save message to history.
        """
        if user.count == 0:
            user.first_message_time = dt.now()
        if user.count < ServerSettings.MAX_MESSAGE_COUNT:
            user.count += 1
            msg = Message(text=message)
            await msg.start()
            self.history.append(msg)
        else:
            logger.info('User %s has reached the limit of messages', user)

    async def check_user_activity(self, user: User) -> None:
        """
        Check user activity.
        """
        while True:
            if (user.first_message_time is not None
                and user.first_message_time + ServerSettings.MESSAGE_LIVE_TIME
                    < dt.now()):
                user.count = 0
                user.first_message_time = None
            if (user.start_ban_time is not None
                and user.start_ban_time + ServerSettings.BAN_TIME
                    < dt.now()):
                user.complaints = 0
                user.start_ban_time = None
            await asyncio.sleep(1)

    async def start(self):
        """Start server."""
        srv = await asyncio.start_server(
            self.listen, self.host, self.port)

        logger.info('Server started at %s:%s', self.host, self.port)

        async with srv:
            await srv.serve_forever()

    async def listen(self, reader: StreamReader, writer: StreamWriter):
        """Listen clients."""
        address = writer.get_extra_info('peername')
        self.users[address] = writer
        logger.info('Start serving %s', address)
        is_logged_in, user_login = await self.login(address, reader)
        if is_logged_in:
            await self.send_history(address)
        user = self.logins[user_login]
        while is_logged_in:
            await self.send_message(Message(text='Enter message: '), address)
            message = await self.read_message(reader)
            if not message:
                break
            if user.count > ServerSettings.MAX_MESSAGE_COUNT:
                await self.send_message(
                    Message(text='You have reached the limit of messages'),
                    address)
            if message.startswith(ServerSettings.PRIVATE_COMMAND):
                await self.send_private_message(message, user_login)
            elif message.startswith(ServerSettings.BAN_COMMAND):
                await self.ban_user(message, user)
            else:
                message = f'{user_login}: {message}'
                await self.save_message(message, user)
                if user.start_ban_time is not None:
                    await self.send_message(Message(text='You are banned'),
                                            address)
                    continue
                if user.count < ServerSettings.MAX_MESSAGE_COUNT:
                    await self.send_public_message(message, address)
                else:
                    await self.send_message(
                        Message(text='You have reached the limit of messages'),
                        address)

        logger.info('Stop serving %s', address)
        writer.close()

    async def ban_user(self, message: str, author: User) -> None:
        """
        Ban user.
        """
        login_to_ban = message.split()[1]
        if login_to_ban not in self.logins:
            await self.send_message(Message(text='User not found'),
                                    author.address)
            return
        user = self.logins[login_to_ban]
        if user.complaints < ServerSettings.BAN_COUNT:
            user.complaints += 1
        else:
            await self.send_message(
                Message(text=f'User {user} have been banned already'),
                author.address)
            return
        if user.complaints == ServerSettings.BAN_COUNT:
            user.start_ban_time = dt.now()
            await self.send_message(Message(
                text=f'You have been banned for {ServerSettings.BAN_TIME}'),
                user.address)

    async def login(self, address: tuple, reader: StreamReader) -> tuple[
            bool, str | None]:
        while True:
            await self.send_message(Message(text=ServerSettings.LOGIN_MESSAGE),
                                    address)
            message = await self.read_message(reader)
            if not message:
                break
            if message.startswith(ServerSettings.LOGIN_COMMAND):
                login = message.replace(ServerSettings.LOGIN_COMMAND,
                                        '').strip()
                if login in self.logins:
                    await self.send_message(
                        Message(text='Login already exists. Try another one.'),
                        address)
                else:
                    user = User(username=login, address=address)
                    asyncio.create_task(self.check_user_activity(user))
                    self.logins[login] = user
                    await self.send_message(
                        Message(text='Login successful.\n'), address)
                    return True, login
        return False, None

    async def send_history(self, address: tuple) -> None:
        """
        Send history to client.
        """
        for message in self.history:
            await self.send_message(message, address)

    async def send_public_message(self, message: str, address: tuple) -> None:
        """
        Send message to all clients.
        """
        for user_address, writer in self.users.items():
            # if user_address != address:
            writer.write(message.encode())
            await writer.drain()

    async def send_private_message(self, message: str, me: str) -> None:
        """
        Send private message to client.
        """
        _, recipient_login, message = message.split(maxsplit=2)
        recipient_user = self.logins.get(recipient_login)
        if recipient_user:
            await self.send_message(
                Message(text=f'Private message from {me}: {message}'),
                recipient_user.address)
        else:
            await self.send_message(
                Message(text=f'User {recipient_login} not found'),
                self.logins[me].address)

    async def read_message(self, reader: StreamReader) -> str:
        """
        Read message from client.
        """
        data = await reader.read(1024)
        return data.decode() if data else ''

    async def send_message(self, message: Message, address: tuple) -> None:
        """
        Send message to client.
        """
        if not message.is_active:
            return
        writer = self.users.get(address)
        writer.write(message.text.encode())
        await writer.drain()


if __name__ == '__main__':
    server = Server()
    asyncio.run(server.start())
