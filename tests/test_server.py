import asyncio

import pytest


@pytest.mark.asyncio
async def test_server():
    try:
        reader, writer = await asyncio.open_connection(
            '127.0.0.1',
            8000)
    except ConnectionRefusedError:
        assert False, 'Server is not running'
    message = await reader.read(1024)
    assert message.decode() == '\nWelcome to chat! First, you need to login. Enter \'/login username\': '
