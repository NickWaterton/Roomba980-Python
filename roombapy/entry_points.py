import sys

from roombapy import RoombaFactory
from roombapy.discovery import RoombaDiscovery
from roombapy.getpassword import RoombaPassword


def discovery():
    roomba_ip = _get_ip_from_arg()

    roomba_discovery = RoombaDiscovery()
    if roomba_ip is not None:
        print(roomba_discovery.find(roomba_ip))
        return

    robots_info = roomba_discovery.find()
    for robot in robots_info:
        print(robot)


def password():
    roomba_ip = _get_ip_from_arg()
    _validate_ip(roomba_ip)
    _wait_for_input()

    roomba_discovery = RoombaDiscovery()
    roomba_info = roomba_discovery.find(roomba_ip)
    _validate_roomba_info(roomba_info)

    roomba_password = RoombaPassword(roomba_ip)
    found_password = roomba_password.get_password()
    roomba_info.password = found_password
    print(roomba_info)


def connect():
    roomba_ip = _get_ip_from_arg()
    _validate_ip(roomba_ip)

    roomba_password = _get_password_from_arg()
    _validate_password(roomba_password)

    roomba_discovery = RoombaDiscovery()
    roomba_info = roomba_discovery.find(roomba_ip)
    _validate_roomba_info(roomba_info)

    roomba = RoombaFactory.create_roomba(
        roomba_info.ip, roomba_info.blid, roomba_password
    )
    roomba.register_on_message_callback(lambda msg: print(msg))
    roomba.connect()

    while True:
        pass


def _validate_ip(ip):
    if ip is None:
        raise Exception("ip cannot be null")


def _validate_password(ip):
    if ip is None:
        raise Exception("password cannot be null")


def _validate_roomba_info(roomba_info):
    if roomba_info is None:
        raise Exception("cannot find roomba")


def _wait_for_input():
    print(
        "Roomba have to be on Home Base powered on.\n"
        "Press and hold HOME button until you hear series of tones.\n"
        "Release button, Wi-Fi LED should be flashing"
    )
    input("Press Enter to continue...")


def _get_ip_from_arg():
    if len(sys.argv) < 2:
        return None
    return str(sys.argv[1])


def _get_password_from_arg():
    if len(sys.argv) < 3:
        return None
    return str(sys.argv[2])
