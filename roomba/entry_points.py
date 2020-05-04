import sys
from roomba.discovery import RoombaDiscovery
from roomba.getpassword import RoombaPassword


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


def _validate_ip(ip):
    if ip is None:
        raise Exception('ip cannot be null')


def _validate_roomba_info(roomba_info):
    if roomba_info is None:
        raise Exception('cannot find roomba')


def _wait_for_input():
    print('Roomba have to be on Home Base powered on.\n'
          'Press and hold HOME button until you hear series of tones.\n'
          'Release button, Wi-Fi LED should be flashing')
    input('Press Enter to continue...')


def _get_ip_from_arg():
    if len(sys.argv) == 1:
        return None
    return str(sys.argv[1])
