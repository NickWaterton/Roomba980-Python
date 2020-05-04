from roomba.discovery import RoombaDiscovery


class TestDiscovery:

    def test_discovery_with_wrong_msg(self):
        # given
        discovery = RoombaDiscovery()

        # when
        discovery.roomba_message = 'test'
        response = discovery.find()

        # then
        assert not response
