from roombapy import Roomba
from roombapy.remote_client import RoombaRemoteClient


class RoombaFactory:
    """
    Allows you to create Roomba class to control your robot
    """

    @staticmethod
    def create_roomba(
        address=None, blid=None, password=None, continuous=True, delay=1
    ):
        remote_client = RoombaFactory._create_remote_client(
            address, blid, password
        )
        return Roomba(remote_client, continuous, delay)

    @staticmethod
    def _create_remote_client(address=None, blid=None, password=None):
        return RoombaRemoteClient(address=address, blid=blid, password=password)
