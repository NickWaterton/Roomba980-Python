import os
import asyncio
import pytest
from hbmqtt.broker import Broker
from hbmqtt.client import MQTTClient, ConnectException
from roomba.roomba import Roomba

ROOMBA_CONFIG = {
    'host': '127.0.0.1',
    'username': 'test',
    'password': 'test',
    'name': 'Roomba',
    'continuous': True,
    'delay': 120,
}

BROKER_CONFIG = {
    'listeners': {
        'default': {
            'type': 'tcp',
            'bind': 'localhost:8883',
            'max_connections': 10
        },
    },
    'auth': {
        'allow-anonymous': False,
        'password-file': os.path.join(os.path.dirname(os.path.realpath(__file__)), 'passwd'),
        'plugins': [
            'auth_file', 'auth_anonymous'
        ]
    },
    'topic-check': {
        'enabled': False
    }
}

MOCK_SERVER_URL = 'mqtt://test:test@127.0.0.1:8883'


class AbstractTestRoomba:
    mock_server = None

    @pytest.fixture
    def broker(self, event_loop):
        return Broker(BROKER_CONFIG, loop=event_loop)

    @pytest.fixture
    def mock_server(self, event_loop):
        return MQTTClient(loop=event_loop)

    def get_default_roomba(self):
        return Roomba(
            address=ROOMBA_CONFIG['host'],
            blid=ROOMBA_CONFIG['username'],
            password=ROOMBA_CONFIG['password'],
            continuous=ROOMBA_CONFIG['continuous'],
            delay=ROOMBA_CONFIG['delay'],
        )

    async def roomba_connect(self, roomba, loop):
        roomba.connect()
        await asyncio.sleep(1, loop=loop)
        return roomba.client.mqtt_client.is_connected()

    async def roomba_disconnect(self, roomba):
        roomba.disconnect()

    async def start_broker(self, broker, loop):
        await broker.start()
        await asyncio.sleep(1, loop=loop)

    async def stop_broker(self, broker, loop):
        await broker.shutdown()
        await asyncio.sleep(1, loop=loop)
