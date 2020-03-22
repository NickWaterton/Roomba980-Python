import asyncio
import pytest
from hbmqtt.broker import Broker
import os
from tests import abstract_test_roomba

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


class TestRoombaIntegration(abstract_test_roomba.AbstractTestRoomba):

    @pytest.mark.asyncio
    async def test_roomba_connect(self, broker, event_loop):
        # given
        roomba = self.get_default_roomba()

        # when
        await self.start_broker(broker, event_loop)
        is_connected = await self.roomba_connect(roomba, event_loop)
        await self.roomba_disconnect(roomba)
        await self.stop_broker(broker, event_loop)

        # then
        assert is_connected

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

    @pytest.fixture
    def broker(self, event_loop):
        return Broker(BROKER_CONFIG, loop=event_loop)
