from roomba.roomba import Roomba

ROOMBA_CONFIG = {
    'host': '127.0.0.1',
    'username': 'test',
    'password': 'test',
    'name': 'Roomba',
    'continuous': True,
    'delay': 120,
}


class AbstractTestRoomba:

    @staticmethod
    def get_default_roomba():
        return Roomba(
            address=ROOMBA_CONFIG['host'],
            blid=ROOMBA_CONFIG['username'],
            password=ROOMBA_CONFIG['password'],
            continuous=ROOMBA_CONFIG['continuous'],
            delay=ROOMBA_CONFIG['delay'],
        )

    @staticmethod
    def get_message(topic, payload):
        class Message:
            pass

        message = Message
        setattr(message, 'topic', topic)
        setattr(message, 'payload', payload)
        setattr(message, 'qos', 'qos')

        return message
