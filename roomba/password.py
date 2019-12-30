from __future__ import print_function
from pprint import pformat
import json
import logging
import socket
import six
import ssl
import sys
try:
    import configparser
except:
    from six.moves import configparser
    
if sys.version_info[0] < 3: #fix more python 3 incompatibilities
    input = raw_input

log = logging.getLogger(__name__)

class Password(object):
    '''
    Get Roomba blid and password - only V2 firmware supported
    if IP is not supplied, class will attempt to discover the Roomba IP first.
    Results are written to a config file, default ".\config.ini"
    V 1.2.3 NW 9/10/2018 added support for Roomba i7
    V 1.2.5 NW 7/10/2019 changed PROTOCOL_TLSv1 to PROTOCOL_TLS to fix i7 software connection problem
    V 1.2.6 NW 12/11/2019 add cipher to ssl to avoid dh_key_too_small issue
    '''

    VERSION = __version__ = "1.2.6"

    def __init__(self, address='255.255.255.255', file=".\config.ini"):
        self.address = address
        self.file = file
        #self.log = logging.getLogger(__name__+'.Roomba_getpassword')
        if __name__ == "password": 
            self.log = logging.getLogger("__main__")    #another logging fix NW 3/2/2018
        else:
            self.log = logging.getLogger("roomba.__main__")
        #self.log.info("__name__ is %s" % __name__)
        self.log.info("Using Password version %s" % self.VERSION)
        self.get_password()

    def receive_udp(self):
        #set up UDP socket to receive data from robot
        port = 5678
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(10)
        if self.address == '255.255.255.255':
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.bind(("", port))  #bind all intefaces to port
        print("waiting on port: %d for data" % port)
        message = 'irobotmcs'
        s.sendto(message.encode(), (self.address, port))
        roomba_dict = {}
        while True:
            try:
                udp_data, addr = s.recvfrom(1024)   #wait for udp data
                #print('Received: Robot addr: %s Data: %s ' % (addr, udp_data))
                if len(udp_data) > 0:
                    if udp_data != message:
                        try:
                            if self.address != addr[0]:
                                self.log.warn(
                                    "supplied address %s does not match "
                                    "discovered address %s, using discovered "
                                    "address..." % (self.address, addr[0]))
                            if udp_data.decode() != message:
                                parsedMsg = json.loads(udp_data.decode()) #1.2.3 added .decode() to avoid python 3 bytes error
                                roomba_dict[addr]=parsedMsg
                        except Exception as e:
                            print("json decode error: %s" % e)
                            print('RECEIVED: %s', pformat(udp_data))
                        # print('Robot Data: %s '
                        #       % json.dumps(parsedMsg, indent=2))
                else:
                    break
            except socket.timeout:
                break
        s.close()
        return roomba_dict

    def get_password(self):
        import struct
        #get roomba info
        blid=None
        roombas = self.receive_udp()

        if len(roombas) == 0:
            print("No Roombas found, try again...")
            return False
        else:
            print("found %d Roomba(s)" % len(roombas))

        for address,parsedMsg in six.iteritems(roombas):
            addr = address[0]
            if int(parsedMsg["ver"]) < 2:
                print("Roombas at address: %s does not have the correct "
                      "firmware version. Your version info is: %s"
                      % (addr,json.dumps(parsedMsg, indent=2)))
                continue

            print("Make sure your robot (%s) at IP %s is on the Home Base and "
                  "powered on (green lights on). Then press and hold the HOME "
                  "button on your robot until it plays a series of tones "
                  "(about 2 seconds). Release the button and your robot will "
                  "flash WIFI light."
                  % (parsedMsg["robotname"],addr))
            input("Press Enter to continue...")

            print("Received: %s"  % json.dumps(parsedMsg, indent=2))
            print("\r\rRoomba (%s) IP address is: %s"
                  % (parsedMsg["robotname"],addr))
            hostname = parsedMsg["hostname"].split('-')
            if hostname[0] == 'Roomba' or hostname[0] == 'iRobot':  #for i7 robot name is now iRobot
                blid = hostname[1]

            if hasattr(str, 'decode'):
                # this is 0xf0 (mqtt reserved) 0x05(data length)
                # 0xefcc3b2900 (data)
                packet = 'f005efcc3b2900'.decode("hex")
            else:
                #this is 0xf0 (mqtt reserved) 0x05(data length)
                # 0xefcc3b2900 (data)
                packet = bytes.fromhex('f005efcc3b2900')
            #send socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)

            #ssl wrap
            wrappedSocket = ssl.wrap_socket(
                sock, ssl_version=ssl.PROTOCOL_TLS, ciphers='DEFAULT@SECLEVEL=1')   #ciphers='HIGH:!DH:!aNULL' may work as well
            #connect and send packet
            try:
                wrappedSocket.connect((addr, 8883))
            except Exception as e:
                print("Connection Error %s" % e)

            wrappedSocket.send(packet)
            data = b''
            data_len = 35
            while True:
                try:
                    # NOTE data is 0xf0 (mqtt RESERVED) length (0x23 = 35),
                    # 0xefcc3b2900 (magic packet), 0xXXXX... (30 bytes of
                    # password). so 7 bytes, followed by 30 bytes of password
                    # (total of 37)
                    if len(data) >= data_len+2:
                        break
                    data_received = wrappedSocket.recv(1024)
                except socket.error as e:
                    print("Socket Error: %s" % e)
                    break

                if len(data_received) == 0:
                    print("socket closed")
                    break
                else:
                    data += data_received
                    if len(data) >= 2:
                        data_len = struct.unpack("B", data[1:2])[0]

            #close socket
            wrappedSocket.close()
            # if len(data) > 0:
            #     import binascii
            #     print("received data: hex: %s, length: %d"
            #           % (binascii.hexlify(data), len(data)))
            if len(data) <= 7:
                print('Error getting password, receive %d bytes. Follow the '
                      'instructions and try again.' % len(data))
                return False
            else:
                # Convert password to str
                #password = str(data[7:].decode()) #old version
                password = str(data[7:].decode().rstrip('\x00')) #for i7 - has null termination
                print("blid is: %s" % blid)
                print('Password=> %s <= Yes, all this string.' % password)
                print('Use these credentials in roomba.py')

                Config = configparser.ConfigParser()
                Config.add_section(addr)
                Config.set(addr,'blid', blid)
                Config.set(addr,'password', password)
                Config.set(addr,'data', pformat(parsedMsg))
                # write config file
                with open(self.file, 'w') as cfgfile:
                    Config.write(cfgfile)
        return True
