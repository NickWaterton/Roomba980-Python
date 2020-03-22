from tests import abstract_test_roomba


class TestRoomba(abstract_test_roomba.AbstractTestRoomba):

    def test_roomba_with_data(self):
        # given
        roomba = self.get_default_roomba()

        # when
        roomba.on_message(None, None, TestRoomba.get_message('topic', b'{"state":{"reported":{"cleanSchedule":{"cycle":["none","none","none","none","none","none","none"],"h":[9,11,11,11,11,11,9],"m":[0,0,0,0,0,0,0]},"language":0,"cleanMissionStatus":{"cycle":"none","phase":"charge","expireM":0,"rechrgM":0,"error":0,"notReady":0,"mssnM":108,"sqft":0,"initiator":"","nMssn":209},"dock":{"known":true},"bin":{"present":true,"full":false},"batteryType":"lith","batPct":100,"mobilityVer":"7375","bootloaderVer":"36","soundVer":"13"}}}'))
        roomba.on_message(None, None, TestRoomba.get_message('topic', b'{"state":{"reported":{"signal":{"rssi":-38,"snr":52}}}}'))

        # then
        state = roomba.master_state

        assert state
        assert state['state']['reported']['bin']['present']
        assert not state['state']['reported']['bin']['full']
        assert state['state']['reported']['batPct'] == 100
