import asyncio
from datetime import datetime as dt, timedelta


class ServerSettings:
    """Server settings."""
    LOGIN_MESSAGE = ('Welcome to chat! First, you need to login. '
                     'Enter \'/login username\': ')
    DEFAULT_HOST = '127.0.0.1'
    DEFAULT_PORT = 8000
    LOGIN_COMMAND = '/login'
    PRIVATE_COMMAND = '/private'
    BAN_COMMAND = '/ban'
    MAX_MESSAGE_COUNT = 20
    MESSAGE_LIVE_TIME = timedelta(minutes=60)
    BAN_TIME = timedelta(hours=4)
    BAN_COUNT = 3


class User:
    """User class."""

    def __init__(self, username: str, address: tuple[str, int]):
        self.username = username
        self.address = address
        self.count = 0
        self.first_message_time = None
        self.complaints = 0
        self.start_ban_time = None

    def __repr__(self):
        return f'{self.username}'

    def __str__(self):
        return self.__repr__()


class Message:
    """Message class."""

    def __init__(self, *, text: str):
        self.text = text
        self.timestamp = dt.now()
        self.end_time = dt.now() + ServerSettings.MESSAGE_LIVE_TIME
        self.is_active = True

    async def start(self):
        """Starts the message timer"""
        asyncio.create_task(self._set_inactive())

    async def _set_inactive(self):
        """Sets the message to inactive after the time has passed"""
        while True:
            if self.end_time < dt.now():
                self.is_active = False
                break
            await asyncio.sleep(1)
