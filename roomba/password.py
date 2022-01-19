#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__version__ = "2.0a"
'''
Python 3.6
Quick Program to get blid and password from roomba

Nick Waterton 5th May 2017: V 1.0: Initial Release
Nick Waterton 22nd Dec 2020: V2.0: Updated for i and S Roomba versions, update to minimum python version 3.6
'''

from pprint import pformat
import json
import logging
import socket
import ssl
import sys
import time
from ast import literal_eval
import configparser

class Password(object):
    '''
    Get Roomba blid and password - only V2 firmware supported
    if IP is not supplied, class will attempt to discover the Roomba IP first.
    Results are written to a config file, default ".\config.ini"
    V 1.2.3 NW 9/10/2018 added support for Roomba i7
    V 1.2.5 NW 7/10/2019 changed PROTOCOL_TLSv1 to PROTOCOL_TLS to fix i7 software connection problem
    V 1.2.6 NW 12/11/2019 add cipher to ssl to avoid dh_key_too_small issue
    V 2.0 NW 22nd Dec 2020 updated for S and i versions plus braava jet m6, min version of python 3.6
    V 2.1 NW 9th Dec 2021 Added getting password from aws cloud.
    '''

    VERSION = __version__ = "2.1"
    
    config_dicts = ['data', 'mapsize', 'pmaps', 'regions']

    def __init__(self, address='255.255.255.255', file=".\config.ini", login=[]):
        self.address = address
        self.file = file
        self.login = None
        self.password = None
        if len(login) >= 2:
            self.login = login[0]
            self.password = login[1]
        self.log = logging.getLogger('Roomba.{}'.format(__class__.__name__))
        self.log.info("Using Password version {}".format(self.__version__))
        
    def read_config_file(self):
        #read config file
        Config = configparser.ConfigParser()
        roombas = {}
        try:
            Config.read(self.file)
            self.log.info("reading/writing info from config file {}".format(self.file))
            roombas = {s:{k:literal_eval(v) if k in self.config_dicts else v for k, v in Config.items(s)} for s in Config.sections()}   
            #self.log.info('data read from {}: {}'.format(self.file, pformat(roombas)))
        except Exception as e:
            self.log.exception(e)
        return roombas

    def receive_udp(self):
        #set up UDP socket to receive data from robot
        port = 5678
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(10)
        if self.address == '255.255.255.255':
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.bind(("", port))  #bind all interfaces to port
        self.log.info("waiting on port: {} for data".format(port))
        message = 'irobotmcs'
        s.sendto(message.encode(), (self.address, port))
        roomba_dict = {}
        while True:
            try:
                udp_data, addr = s.recvfrom(1024)   #wait for udp data
                #self.log.debug('Received: Robot addr: {} Data: {}'.format(addr, udp_data))
                if udp_data and udp_data.decode() != message:
                    try:
                        #if self.address != addr[0]:
                        #    self.log.warning(
                        #        "supplied address {} does not match "
                        #        "discovered address {}, using discovered "
                        #        "address...".format(self.address, addr[0]))
                        
                        parsedMsg = json.loads(udp_data.decode())
                        if addr[0] not in roomba_dict.keys():
                            s.sendto(message.encode(), (self.address, port))
                            roomba_dict[addr[0]]=parsedMsg
                            self.log.info('Robot at IP: {} Data: {}'.format(addr[0], json.dumps(parsedMsg, indent=2)))
                    except Exception as e:
                        self.log.info("json decode error: {}".format(e))
                        self.log.info('RECEIVED: {}'.format(pformat(udp_data)))

            except socket.timeout:
                break
        s.close()
        return roomba_dict
        
    def add_cloud_data(self, cloud_data, roombas):
        for k, v in roombas.copy().items():
            robotid = v.get('robotid', v.get("hostname", "").split('-')[1])
            for id, data in cloud_data.items():
                if robotid == id:
                    roombas[k]["password"] = data.get('password')
        return roombas

    def get_password(self):
        #load roombas from config file
        file_roombas = self.read_config_file()
        cloud_roombas = {}
        #get roomba info
        roombas = self.receive_udp()
        if self.login and self.password:
            self.log.info("Getting Roomba information from iRobot aws cloud...")
            from getcloudpassword import irobotAuth
            iRobot = irobotAuth(self.login, self.password)
            iRobot.login()
            cloud_roombas = iRobot.get_robots()
            self.log.info("Got cloud info: {}".format(json.dumps(cloud_roombas, indent=2)))
            self.log.info("Found {} roombas defined in the cloud".format(len(cloud_roombas)))
            if len(cloud_roombas) > 0 and len(roombas) > 0:
                roombas = self.add_cloud_data(cloud_roombas, roombas)

        if len(roombas) == 0:
            self.log.warning("No Roombas found on network, try again...")
            return False
            
        self.log.info("{} robot(s) already defined in file{}, found {} robot(s) on network".format(len(file_roombas), self.file, len(roombas)))

        for addr, parsedMsg in roombas.items():
            blid = parsedMsg.get('robotid', parsedMsg.get("hostname", "").split('-')[1])
            robotname = parsedMsg.get('robotname', 'unknown')
            if int(parsedMsg.get("ver", "3")) < 2:
                self.log.info("Roombas at address: {} does not have the correct "
                      "firmware version. Your version info is: {}".format(addr,json.dumps(parsedMsg, indent=2)))
                continue
            
            password = parsedMsg.get('password')
            if password is None:
                self.log.info("To add/update Your robot details,"
                              "make sure your robot ({}) at IP {} is on the Home Base and "
                              "powered on (green lights on). Then press and hold the HOME "
                              "button on your robot until it plays a series of tones "
                              "(about 2 seconds). Release the button and your robot will "
                              "flash WIFI light.".format(robotname, addr))
            else:
                self.log.info("Configuring robot ({}) at IP {} from cloud data, blid: {}, password: {}".format(robotname, addr, blid, password))
            if sys.stdout.isatty():
                char = input("Press <Enter> to continue...\r\ns<Enter> to skip configuring this robot: ")
                if char == 's':
                    self.log.info('Skipping')
                    continue

            #self.log.info("Received: %s"  % json.dumps(parsedMsg, indent=2))

            if password is None:
                self.log.info("Roomba ({}) IP address is: {}".format(robotname, addr))
                data = self.get_password_from_roomba(addr)
                
                if len(data) <= 7:
                    self.log.error( 'Error getting password for robot {} at ip{}, received {} bytes. '
                                    'Follow the instructions and try again.'.format(robotname, addr, len(data)))
                    continue
                # Convert password to str
                password = str(data[7:].decode().rstrip('\x00')) #for i7 - has null termination
            self.log.info("blid is: {}".format(blid))
            self.log.info('Password=> {} <= Yes, all this string.'.format(password))
            self.log.info('Use these credentials in roomba.py')
            
            file_roombas.setdefault(addr, {})
            file_roombas[addr]['blid'] = blid
            file_roombas[addr]['password'] = password
            file_roombas[addr]['data'] = parsedMsg
        return self.save_config_file(file_roombas)
        
    def get_password_from_roomba(self, addr):
        '''
        Send MQTT magic packet to addr
        this is 0xf0 (mqtt reserved) 0x05(data length) 0xefcc3b2900 (data)
        Should receive 37 bytes containing the password for roomba at addr
        This is is 0xf0 (mqtt RESERVED) length (0x23 = 35) 0xefcc3b2900 (magic packet), 
        followed by 0xXXXX... (30 bytes of password). so 7 bytes, followed by 30 bytes of password
        total of 37 bytes
        Uses 10 second timeout for socket connection
        '''
        data = b''
        packet = bytes.fromhex('f005efcc3b2900')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        #context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        context = ssl.SSLContext()
        #context.set_ciphers('DEFAULT@SECLEVEL=1:HIGH:!DH:!aNULL')
        wrappedSocket = context.wrap_socket(sock)
        
        try:
            wrappedSocket.connect((addr, 8883))
            self.log.debug('Connection Successful')
            wrappedSocket.send(packet)
            self.log.debug('Waiting for data')
        
            while len(data) < 37:
                data_received = wrappedSocket.recv(1024)
                data+= data_received
                if len(data_received) == 0:
                    self.log.info("socket closed")
                    break
                
            wrappedSocket.close()
            return data
            
        except socket.timeout as e:
            self.log.error('Connection Timeout Error (for {}): {}'.format(addr, e))
        except (ConnectionRefusedError, OSError) as e:
            if e.errno == 111:      #errno.ECONNREFUSED
                self.log.error('Unable to Connect to roomba at ip {}, make sure nothing else is connected (app?), '
                               'as only one connection at a time is allowed'.format(addr))
            elif e.errno == 113:    #errno.No Route to Host
                self.log.error('Unable to contact roomba on ip {} is the ip correct?'.format(addr))
            else:
                self.log.error("Connection Error (for {}): {}".format(addr, e))
        except Exception as e:
            self.log.exception(e)

        self.log.error('Unable to get password from roomba')
        return data
        
    def save_config_file(self, roomba):
        Config = configparser.ConfigParser()
        if roomba:
            for addr, data in roomba.items():
                Config.add_section(addr)
                for k, v in data.items():
                    #self.log.info('saving K: {}, V: {}'.format(k, pformat(v) if k in self.config_dicts else v))
                    Config.set(addr,k, pformat(v) if k in self.config_dicts else v)
            # write config file
            with open(self.file, 'w') as cfgfile:
                Config.write(cfgfile)
            self.log.info('Configuration saved to {}'.format(self.file))
        else: return False
        return True
        
    def get_roombas(self):
        roombas = self.read_config_file()
        if not roombas:
            self.log.warn("No roomba or config file defined, I will attempt to "
                          "discover Roombas, please put the Roomba on the dock "
                          "and follow the instructions:")
            self.get_password()
            return self.get_roombas()
        self.log.info("{} Roombas Found".format(len(roombas)))
        for ip in roombas.keys():
            roombas[ip]["roomba_name"] = roombas[ip]['data']['robotname']
        return roombas
        
def main():
    import argparse
    loglevel = logging.DEBUG
    LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT, level=loglevel)
    
    #-------- Command Line -----------------
    parser = argparse.ArgumentParser(
        description='Get Robot passwords and update config file')
    parser.add_argument(
        'login',
        nargs='*',
        action='store',
        type=str,
        default=[],
        help='iRobot Account Login and Password (default: None)')
    parser.add_argument(
        '-f', '--configfile',
        action='store',
        type=str,
        default="./config.ini",
        help='config file name, (default: %(default)s)')
    parser.add_argument(
        '-R','--roombaIP',
        action='store',
        type=str,
        default='255.255.255.255',
        help='ipaddress of Roomba (default: %(default)s)')

    arg = parser.parse_args()

    get_passwd = Password(arg.roombaIP, file=arg.configfile, login=arg.login)
    get_passwd.get_password()

if __name__ == '__main__':
    main()

