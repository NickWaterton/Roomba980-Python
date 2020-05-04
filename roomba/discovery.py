import socket
import json
import logging

from roomba.roomba import RoombaInfo


class RoombaDiscovery:
    udp_bind_address = ''
    udp_address = '<broadcast>'
    udp_port = 5678
    roomba_message = 'irobotmcs'
    amount_of_broadcasted_messages = 5
    server_socket = None
    log = None

    def __init__(self):
        self.server_socket = _get_socket()
        self.log = logging.getLogger(__name__)

    def find(self, ip=None):
        if ip is not None:
            return self.get(ip)
        return self.get_all()

    def get_all(self):
        self._start_server()
        self._broadcast_message(self.amount_of_broadcasted_messages)
        robots = set()
        while True:
            response = self._get_response()
            if response:
                robots.add(response)
            else:
                break
        return robots

    def get(self, ip):
        self._start_server()
        self._send_message(ip)
        return self._get_response(ip)

    def _get_response(self, ip=None):
        try:
            while True:
                raw_response, addr = self.server_socket.recvfrom(1024)
                if ip is not None and addr[0] != ip:
                    continue
                self.log.debug("Received response: %s, address: %s", raw_response, addr)
                data = raw_response.decode()
                if self._is_from_irobot(data):
                    return _decode_data(data)
        except socket.timeout:
            self.log.info('Socket timeout')
            return None

    def _is_from_irobot(self, data):
        if data == self.roomba_message:
            return False

        json_response = json.loads(data)
        if 'Roomba' in json_response['hostname'] or 'iRobot' in json_response['hostname']:
            return True

        return False

    def _broadcast_message(self, amount):
        for i in range(amount):
            self.server_socket.sendto(self.roomba_message.encode(), (self.udp_address, self.udp_port))
            self.log.debug("Broadcast message sent: " + str(i))

    def _send_message(self, udp_address):
        self.server_socket.sendto(self.roomba_message.encode(), (udp_address, self.udp_port))
        self.log.debug("Message sent")

    def _start_server(self):
        self.server_socket.bind((self.udp_bind_address, self.udp_port))
        self.log.debug("Socket server started, port %s", self.udp_port)


def _decode_data(data):
    json_response = json.loads(data)
    return RoombaInfo(
        hostname=json_response['hostname'],
        robot_name=json_response['robotname'],
        ip=json_response['ip'],
        mac=json_response['mac'],
        firmware=json_response['sw'],
        sku=json_response['sku'],
        capabilities=json_response['cap'])


def _get_socket():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    server_socket.settimeout(5)
    return server_socket
