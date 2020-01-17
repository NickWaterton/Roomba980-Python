import asyncio
import pytest
from tests import abstract_test_roomba


class TestRoomba(abstract_test_roomba.AbstractTestRoomba):

    @pytest.mark.asyncio
    async def test_roomba_connect(self, broker, event_loop):
        # given
        default_roomba = self.get_default_roomba()

        # when
        await self.start_broker(broker, event_loop)
        is_connected = await self.roomba_connect(default_roomba, event_loop)
        await self.roomba_disconnect(default_roomba)
        await self.stop_broker(broker, event_loop)

        # then
        assert is_connected

    @pytest.mark.asyncio
    async def test_roomba_with_data(self, broker, mock_server, event_loop):
        # given
        default_roomba = self.get_default_roomba()

        async def mock_server_send_data():
            await mock_server.connect(abstract_test_roomba.MOCK_SERVER_URL)
            await mock_server.publish('wifistat', b'{"state":{"reported":{"netinfo":{"dhcp":false,"addr":0000000000,"mask":0000000000,"gw":0000000000,"dns1":000000000,"dns2":00000000,"bssid":"00:00:00:00:00:00","sec":4}}}}')
            await mock_server.publish('wifistat', b'{"state":{"reported":{"wifistat":{"wifi":1,"uap":false,"cloud":1}}}}')
            await mock_server.publish('wifistat', b'{"state":{"reported":{"wlcfg":{"sec":7,"ssid":"00000000000000000000","addr":0000000000,"mask":0000000000,"gw":0000000000,"dns1":000000000,"dns2":00000000}}}}')
            await mock_server.publish('wifistat', b'{"state":{"reported":{"mac":"00:00:00:00:00:00"}}}')
            await mock_server.publish('aws/things/3162C21462538560/shadow/update', b'{"state":{"reported":{"country": "UN"}}}')
            await mock_server.publish('aws/things/3162C21462538560/shadow/update', b'{"state":{"reported":{"cloudEnv": "prod"}}}')
            await mock_server.publish('aws/things/3162C21462538560/shadow/update', b'{"state":{"reported":{"svcEndpoints":{"svcDeplId": "v011"}}}}')
            await mock_server.publish('aws/things/3162C21462538560/shadow/update', b'{"state":{"reported":{"name": "Name"}}}')
            await mock_server.publish('aws/things/3162C21462538560/shadow/update', b'{"state":{"reported":{"lastDisconnect":2,"cap":{"ota":1,"eco":1,"svcConf":1},"bbrun":{"nCliffsF":1177,"nPanics":1162,"hr":127,"min":56,"nScrubs":384,"sqft":0,"nStuck":0,"nPicks":0,"nCliffsR":0,"nMBStll":0,"nWStll":0,"nCBump":0},"bbmssn":{"nMssn":209,"nMssnOk":145,"nMssnF":64,"aMssnM":17,"nMssnC":0,"aCycleM":0},"bbpause":{"pauses":[0,0,6,0,0,13,0,18,0,0]},"bbrstinfo":{"nNavRst":0,"nMobRst":0,"causes":"0000"},"bbpanic":{"panics":[12,15,17,12,17]}}}}')
            await mock_server.publish('aws/things/3162C21462538560/shadow/update', b'{"state":{"reported":{"cleanSchedule":{"cycle":["none","none","none","none","none","none","none"],"h":[9,11,11,11,11,11,9],"m":[0,0,0,0,0,0,0]},"language":0,"cleanMissionStatus":{"cycle":"none","phase":"charge","expireM":0,"rechrgM":0,"error":0,"notReady":0,"mssnM":108,"sqft":0,"initiator":"","nMssn":209},"dock":{"known":true},"bin":{"present":true,"full":false},"batteryType":"lith","batPct":100,"mobilityVer":"7375","bootloaderVer":"36","soundVer":"13"}}}')
            await mock_server.publish('aws/things/3162C21462538560/shadow/update', b'{"state":{"reported":{"langs":[{"en-US":0},{"en-GB":15},{"fr-FR":1},{"de-DE":2},{"es-ES":3},{"es-XL":11},{"pt-PT":12},{"pt-BR":19},{"it-IT":4},{"nl-NL":5},{"da-DK":6},{"sv-SE":7},{"nb-NO":8},{"fi-FI":16},{"pl-PL":10},{"cs-CZ":17},{"ru-RU":18},{"he-IL":20},{"ja-JP":13},{"zh-CN":14},{"zh-TW":9}],"audio":{"active":false},"binPause":false,"carpetBoost":false,"noAutoPasses":false,"noPP":false,"openOnly":false,"twoPass":false,"vacHigh":false,"sku":"R691040","timezone":"Europe/Warsaw"}}}')
            await mock_server.publish('aws/things/3162C21462538560/shadow/update', b'{"state":{"reported":{"tz":{"ver":7,"events":[{"dt":1564675200,"off":120},{"dt":1572138001,"off":60},{"dt":1585443601,"off":120}]},"ecoCharge":false,"wifiSwVer":"3.2.47+77","softwareVer":"3.2.47+77","lastCommand":{"command": "start", "initiator": "rmtApp", "time": 1575873539},"hardwareRev":2,"wifiAnt":1,"schedHold":false}}}')
            await mock_server.publish('wifistat', b'{"state":{"reported":{"signal":{"rssi":-35,"snr":54}}}}')
            await mock_server.publish('wifistat', b'{"state":{"reported":{"signal":{"rssi":-38,"snr":52}}}}')

        async def mock_server_disconnect():
            await mock_server.disconnect()

        # when
        await self.start_broker(broker, event_loop)
        await self.roomba_connect(default_roomba, event_loop)
        await mock_server_send_data()
        await mock_server_disconnect()
        await asyncio.sleep(1, loop=event_loop)

        state = default_roomba.master_state

        await self.roomba_disconnect(default_roomba)
        await self.stop_broker(broker, event_loop)

        # then
        assert state
        assert state['state']['reported']['bin']['present']
        assert not state['state']['reported']['bin']['full']
        assert state['state']['reported']['batPct'] == 100
