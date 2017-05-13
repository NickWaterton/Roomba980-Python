#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = "1.0"
'''
Python 2.7
Program to connect to Roomba 980 vacuum cleaner, dcode json, and forward to mqtt server

Nick Waterton 24th April 2017: V 1.0: Initial Release
'''

#NOTE: MUST use Pillow Pillow 4.1.1 to avoid some horrible memory leaks in the text handling!

global HAVE_MQTT
HAVE_MQTT=False
try:
    import paho.mqtt.client as mqtt
    HAVE_MQTT=True
except ImportError:
    print("paho mqtt client not found")
import sys, os
import ssl
import json
import datetime
from collections import OrderedDict, Mapping
import threading
import logging
import time
from logging.handlers import RotatingFileHandler
from ast import literal_eval
import socket
import ConfigParser
import math

global HAVE_CV2
HAVE_CV2=False
global HAVE_PIL
HAVE_PIL=False
try:
    import cv2
    import numpy as np
    HAVE_CV2=True
except ImportError:
    print("CV or numpy module not found, falling back to PIL")
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
    HAVE_PIL=True
except ImportError:
    print("PIL module not found, maps are disabled")  
    

#----------- Start of Classes ------------

    
class password(object):
    '''
    Get Roomba blid and password - only V2 firmware supported
    if IP is not supplied, class will attempt to discover the Roomba IP first.
    Results are written to a config file, default ".\config.ini"
    '''
    
    VERSION = "1.0"
    
    def __init__(self, address='255.255.255.255', file=".\config.ini"):
        self.address = address
        self.file = file
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
        s.sendto(message, (self.address, port))
        roomba_dict = {}
        while True:
            try:
                udp_data, addr = s.recvfrom(1024)   #wait for udp data
                #print('Received: Robot addr: %s Data: %s ' % (addr, udp_data))
                if len(udp_data) > 0:
                    if udp_data != message:
                        try:
                            if self.address != addr[0]:
                                self.log.warn("supplied address %s does not match discovered address %s, using discovered address..." % (self.address, addr[0]))
                            parsedMsg = json.loads(udp_data)
                            roomba_dict[addr]=parsedMsg
                        except Exception as e:
                            print("json decode error: %s" % e)
                            break
                        #print('Robot Data: %s ' % json.dumps(parsedMsg, indent=2))
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
            print("found %d Roombas" % len(roombas))
            
        for address,parsedMsg in roombas.iteritems():
            addr = address[0]
            if int(parsedMsg["ver"]) < 2:
                print("Roombas at address: %s does not have the correct firmware version. Your version info is: %s" % (addr,json.dumps(parsedMsg, indent=2)))
                continue
                
            print("Make sure your robot (%s) at IP %s is on the Home Base and powered on (green lights on). Then press and hold the HOME button on your robot until it plays a series of tones (about 2 seconds). Release the button and your robot will flash WIFI light." % (parsedMsg["robotname"],addr))
            raw_input("Press Enter to continue...")
            
            print("Received: %s"  % json.dumps(parsedMsg, indent=2))
            print("\r\rRoomba (%s) IP address is: %s" % (parsedMsg["robotname"],addr))
            hostname = parsedMsg["hostname"].split('-')
            if hostname[0] == 'Roomba':
                blid = hostname[1]
            
            packet = 'f005efcc3b2900'.decode("hex") #this is 0xf0 (mqtt reserved) 0x05(data length) 0xefcc3b2900 (data)
            #send socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)

            #ssl wrap
            wrappedSocket = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_TLSv1)
            #connect and send packet
            try:
                wrappedSocket.connect((addr, 8883))
            except Exception as e:
                print("Connection Error %s" % e)
                
            wrappedSocket.send(packet)
            data = ''
            data_len = 35
            while True:
                try:
                    if len(data) >= data_len+2: #NOTE data is 0xf0 (mqtt RESERVED) length (0x23 = 35), 0xefcc3b2900 (magic packet), 0xXXXX... (30 bytes of password). so 7 bytes, followed by 30 bytes of password (total of 37)
                        break
                    data_received = wrappedSocket.recv(1024)
                except socket.error, e:
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
            '''
            if len(data) > 0:
                import binascii
                print("received data: hex: %s, length: %d" % (binascii.hexlify(data), len(data)))
            '''        
            if len(data) <= 7:
                print('Error getting password, receive %d bytes. Follow the instructions and try again.' % len(data))
                return False
            else:
                print("blid is: %s" % blid)
                print('Password=> %s <= Yes, all this string.' % str(data[7:]))
                print('Use these credentials in roomba.py')
                
                Config = ConfigParser.ConfigParser()
                Config.add_section(addr)
                Config.set(addr,'blid',blid)
                Config.set(addr,'password',str(data[7:]))
                Config.set(addr,'data',parsedMsg)
                #write config file
                with open(self.file, 'w') as cfgfile:
                    Config.write(cfgfile)
        return True

      
class Roomba(object):
    '''
    This is a Class for Roomba 900 series WiFi connected Vacuum cleaners
    Requires firmware version 2.0 and above (not V1.0). Tested with Roomba 980
    username (blid) and password are required, and can be found using the password() class above 
    Most of the underlying info was obtained from here:
    https://github.com/koalazak/dorita980 many thanks!
    The values received from the Roomba as stored in a dictionay called master_state, and can be accessed
    at any time, the contets are live, and will build with time after connection.
    This is not needed if the forward to mqtt option is used, as the events will be decoded and published on the
    designated mqtt client topic.
    '''
    
    VERSION = "1.0"
    
    states = {  "charge":"Charging",
                "new":"New Mission",
                "run":"Running",
                "resume":"Running",
                "hmMidMsn":"Recharging",
                "recharge":"Recharging",
                "stuck":"Stuck",
                "hmUsrDock":"User Docking",
                "dock":"Docking",
                "dockend":"Docking - End Mission",
                "cancelled":"Cancelled",
                "stop":"Stopped",
                "pause":"Paused",
                "hmPostMsn":"End Mission",
                "":None}
                
    # From http://homesupport.irobot.com/app/answers/detail/a_id/9024/~/roomba-900-error-messages
    _ErrorMessages = {
        0 : "None",
        1 : "Roomba is stuck with its left or right wheel hanging down.",
        2 : "The debris extractors can't turn.",
        5 : "The left or right wheel is stuck.",
        6 : "The cliff sensors are dirty, it is hanging over a drop, or it is stuck on a dark surface.",
        8 : "The fan is stuck or its filter is clogged.",
        9 : "The bumper is stuck, or the bumper sensor is dirty.",
        10: "The left or right wheel is not moving.",
        11: "Roomba has an internal error.",
        14: "The bin has a bad connection to the robot.",
        15: "Roomba has an internal error.",
        16: "Roomba has started while moving or at an angle, or was bumped while running.",
        17: "The cleaning job is incomplete.",
        18: "Roomba cannot return to the Home Base or starting position."
    }
    
    def __init__(self, address=None, blid=None, password=None, topic="#", continuous=True, clean=False, cert_name="", roombaName="", file="./config.ini"):
        '''
        address is the IP address of the Roomba, the continuous flag
        enables a continuous mqtt connection, if this is set to False, the client connects and disconnects every 'delay' seconds
        (1 by default, but can be changed). This is to allow other programs access, as there can only be one Roomba connection at a time.
        As cloud connections are unaffected, I reccomend leaving this as True.
        leave topic as is, unless debugging (# = all messages).
        if a python standard logging object exists, it will be used for logging.
        '''
        
        self.debug = False
        self.log = logging.getLogger(__name__+'.Roomba')
        if self.log.getEffectiveLevel() == logging.DEBUG:
            self.debug = True           
        self.address = address      
        if cert_name == "":
            self.cert_name = "./ca-certificates.crt" #/etc/ssl/certs/ca-certificates.crt is default for Linux Debian based systems
        else:
            self.cert_name = cert_name
        self.continuous = continuous
        if self.continuous:
            self.log.info("CONTINUOUS connection")
        else:
            self.log.info("PERIODIC connection")
        self.pretty_print = False   #set this to True to enable pretty printing of json data
        self.stop_connection = False
        self.periodic_connection_running = False
        self.clean = clean
        self.roomba_port = 8883
        self.blid = blid
        self.password = password
        self.roombaName = roombaName
        self.topic = topic
        self.mqttc = None
        self.exclude = ""
        self.delay = 1
        self.roomba_connected = False
        self.indent = 0
        self.master_indent = 0
        self.raw = False
        self.drawmap = False
        self.previous_co_ords = self.co_ords = self.zero_coords()
        self.fnt = None
        self.home_pos = None
        self.angle = 0
        self.cleanMissionStatus_phase = ""
        self.previous_cleanMissionStatus_phase = ""
        self.current_state = None
        self.last_completed_time = None
        self.bin_full = False
        self.base = None #base map
        self.dock_icon = None   #dock icon
        self.roomba_icon = None #roomba icon
        self.roomba_cancelled_icon = None #roomba cancelled icon
        self.roomba_battery_icon = None #roomba battery low icon
        self.roomba_error_icon = None #roomba error icon
        self.bin_full_icon = None #bin full icon
        self.room_outline_contour = None
        self.transparent = (0, 0, 0, 0)  #transparent
        self.previous_display_text = self.display_text = None
        self.master_state = {}
        self.time = time.time()
        self.update_seconds = 300   #update with all values every 5 minutes
        self.show_final_map = True
        self.client = None
        
        if self.address is None or blid is None or password is None:
            read_config_file(file)
        
    def read_config_file(file="./config.ini"):       
        #read config file
        Config = ConfigParser.ConfigParser()
        try:
            Config.read(file)
        except Exception as e:
            self.log.warn("Error reading config file %s" %e)
            self.log.info("No Roomba specified, and no config file found - attempting discovery")
            if password(self.address, file):
                return self.read_config_file(file)
            else: return False
        self.log.info("reading info from config file %s" % file)
        addresses = Config.sections()
        if self.address is None:
            if len(addresses) > 1:
                self.log.warn("config file has entries for %d Roombas, only configuring the first!")
                self.address = addresses[0]
        self.blid = Config.get(self.address, "blid"), 
        self.password = Config.get(self.address, "password")
        #self.roombaName = literal_eval(Config.get(self.address, "data"))["robotname"]
        return True
        
    def setup_client(self):
        if self.client is None:
            if not HAVE_MQTT:
                print("Please install paho-mqtt '<sudo> pip install paho-mqtt' to use this library")
                return False
            self.client = mqtt.Client(client_id=self.blid, clean_session=self.clean)
            # Assign event callbacks
            self.client.on_message = self.on_message
            self.client.on_connect = self.on_connect
            self.client.on_publish = self.on_publish
            self.client.on_subscribe = self.on_subscribe
            self.client.on_disconnect = self.on_disconnect

            # Uncomment to enable debug messages
            #client.on_log = self.on_log
            
            #set TLS, self.cert_name is required by paho-mqtt, even if the certificate is not used...
            self.client.tls_set(self.cert_name, cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLSv1)

            # disables peer verification
            self.client.tls_insecure_set(True)
            self.client.username_pw_set(self.blid, self.password)
            return True
        return False
        
    def connect(self):
        if self.address is None or self.blid is None or self.password is None:
            self.log.critical("Invalid address, blid, or password! All these must be specified!")
            sys.exit(1)
        if self.roomba_connected or self.periodic_connection_running: return

        if self.continuous:
            if not self._connect():
                if self.mqttc is not None:
                    self.mqttc.disconnect()
                sys.exit(1)
        else:
            self._thread = threading.Thread(target=self.periodic_connection)
            self._thread.daemon = True
            self._thread.start()
            
        self.time = time.time()   #save connect time
            
    def _connect(self, count=0, new_connection=False):
        max_retries = 3
        try:
            if self.client is None or new_connection:
                self.log.info("Connecting %s" % self.roombaName)
                self.setup_client()
                self.client.connect(self.address, self.roomba_port, 60)
            else:
                self.log.info("Attempting to Reconnect %s" % self.roombaName)
                self.client.loop_stop()
                self.client.reconnect()
            self.client.loop_start()
            return True
        except Exception as e:
            self.log.error("Error: %s " % e)
            if e[0] == 111: #errno.ECONNREFUSED
                count +=1
                if count <= max_retries:
                    self.log.error("Attempting new Connection# %d" % count)
                    time.sleep(1)
                    self._connect(count, True)
        if count == max_retries:                
            self.log.error("Unable to connect %s" % self.roombaName)
        return False
        
    def disconnect(self):
        if self.continuous:
            self.client.disconnect()
        else:
            self.stop_connection = True    
        
    def periodic_connection(self):
        if self.periodic_connection_running: return #only one connection thread at a time!
        self.periodic_connection_running = True
        while not self.stop_connection:
            if self._connect():
                time.sleep(self.delay)
                self.client.disconnect()
            time.sleep(self.delay)

        self.client.disconnect()
        self.periodic_connection_running = False

    def on_connect(self, client, userdata, flags, rc):
        self.log.info("Roomba Connected %s" % self.roombaName)
        if rc == 0:
            self.roomba_connected = True
            self.client.subscribe(self.topic)
        else:
            self.log.error("Roomba Connected with result code "+str(rc))
            self.log.error("Please make sure your blid and password are correct %s" % self.roombaName)
            if self.mqttc is not None:
               self.mqttc.disconnect()
            sys.exit(1)
        
    def on_message(self, mosq, obj, msg):
        #print(msg.topic+" "+str(msg.qos)+" "+str(msg.payload))
        if self.exclude != "":
            if self.exclude in msg.topic:
                return
            
        if self.indent == 0:
            self.master_indent = max(self.master_indent, len(msg.topic))
            
        log_string, json_data = self.decode_payload(msg.topic,msg.payload)
        self.dict_merge(self.master_state, json_data)
        
        if self.pretty_print:
            self.log.info("%-{:d}s : %s".format(self.master_indent) % (msg.topic,log_string))
        else:
            self.log.info("Received Roomba Data %s: %s, %s" % (self.roombaName, str(msg.topic), str(msg.payload)))
        
        if self.raw:
            self.publish(msg.topic, msg.payload)
        else:
            self.decode_topics(json_data)
        
        if time.time() - self.time > self.update_seconds:   #default every 5 minutes
            self.log.info("Publishing master_state %s" % self.roombaName)
            self.decode_topics(self.master_state)    #publish all values
            self.time = time.time()
        
    def on_publish(self, mosq, obj, mid):
        pass

    def on_subscribe(self, mosq, obj, mid, granted_qos):
        self.log.debug("Subscribed: %s %s" % (str(mid), str(granted_qos)))

    def on_disconnect(self, mosq, obj, rc):
        self.roomba_connected = False
        if rc != 0:
            self.log.warn("Unexpected Disconnect From Roomba %s! - reconnecting" % self.roombaName)
        else:
            self.log.info("Disconnected From Roomba %s" % self.roombaName)

    def on_log(self, mosq, obj, level, string):
        self.log.info(string)
        
    def set_mqtt_client(self, mqttc=None, brokerFeedback=""):
        self.mqttc = mqttc
        if self.mqttc is not None:
            if self.roombaName != "":
                self.brokerFeedback = brokerFeedback+"/"+self.roombaName
            else:
                self.brokerFeedback = brokerFeedback
            
    def send_command(self, command):
        self.log.info("Received COMMAND: %s" % command)
        Command = OrderedDict()
        Command["command"] = command
        Command["time"] = self.totimestamp(datetime.datetime.now())
        Command["initiator"] = "localApp"
        myCommand = json.dumps(Command)
        self.log.info("Publishing Roomba Command : %s" % myCommand)
        self.client.publish("cmd", myCommand)
        
    def set_preference(self, preference, setting):
        self.log.info("Received SETTING: %s, %s" % (preference, setting))
        val = False
        if setting.lower() == "true":
            val = True
        tmp = {preference: val}
        Command = {"state": tmp}
        myCommand = json.dumps(Command)
        self.log.info("Publishing Roomba Setting : %s" % myCommand)
        self.client.publish("delta", myCommand)
        
    def publish(self, topic, message):
        if self.mqttc is not None and message is not None:
            self.log.debug("Publishing item: %s: %s" % (self.brokerFeedback+"/"+topic, message))
            self.mqttc.publish(self.brokerFeedback+"/"+topic, message)
            
    def set_options(self, raw=False, indent=0, pretty_print=False):
        self.raw = raw
        self.indent = indent
        self.pretty_print = pretty_print
        if self.raw:
            self.log.info("Posting RAW data")
        else:
            self.log.info("Posting DECODED data")
            
    def enable_map(self, enable=False, mapSize="(800,1500,0,0,0,0)", mapPath="./",
                         home_icon_file="./home.png", 
                         roomba_icon_file="./roomba.png", 
                         roomba_error_file="./roombaerror.png", 
                         roomba_cancelled_file="./roombacancelled.png",
                         roomba_battery_file="./roomba-charge.png",
                         bin_full_file="./binfull.png", 
                         roomba_size=(50,50), draw_edges = 30, auto_rotate=True):
        '''
        Enable live map drawing. mapSize is x,y size, x,y offset of docking station ((0,0) is the center of the image)
        final value is map rotation (in case map is not streight up/down). These values depend on the size/shape of the
        area Roomba covers. Offset depends on where you place the docking station. This will need some experimentation
        to get right. You can supply 32x32 icons for dock and roomba etc. If the files don't exist, crude representations ar made. 
        if you specify home_icon_file as None, then no dock is drawn. Draw edges attempts to draw streight lines around the final (not live) map, 
        and Auto_rotate (on/off) attempts to line the map up vertically. These only work if you have openCV installed. otherwise a PIL
        version is used, which is not as good (but less CPU intensive).
        Returns map enabled True/False
        '''
        
        if not HAVE_PIL: #can't draw a map without PIL!
            return False
            
        self.drawmap = enable
        if self.drawmap:
            self.log.info("MAP: Maps Enabled")
            self.mapSize = literal_eval(mapSize)
            if len(mapSize) < 6:
                self.log.error("mapSize is required, and is of the form (800,1500,0,0,0,0) - (x,y size, x,y dock loc, theta1, theta2), map,roomba roatation")
                self.drawmap = False
                return False
            self.angle = self.mapSize[4]
            self.roomba_angle = self.mapSize[5]
            self.mapPath = mapPath
            self.home_icon_file = home_icon_file
            self.roomba_icon_file = roomba_icon_file
            self.roomba_error_file = roomba_error_file
            self.roomba_cancelled_file = roomba_cancelled_file
            self.roomba_battery_file = roomba_battery_file
            self.bin_full_file = bin_full_file
            self.draw_edges = draw_edges/10000
            self.auto_rotate = auto_rotate
            
            self.initialise_map(roomba_size)
            return True
        return False
            
        if Image.PILLOW_VERSION < "4.1.1":
            print("WARNING: PIL version is %s, this is not the latest! you can get bad memory leaks with old versions of PIL" % Image.PILLOW_VERSION)
            print("run: 'pip install --upgrade pillow' to fix this")
        
    def totimestamp(self, dt):
        td = dt - datetime.datetime(1970,1,1)
        return int(td.total_seconds())
        
    def dict_merge(self, dct, merge_dct):
        """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
        updating only top-level keys, dict_merge recurses down into dicts nested
        to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
        ``dct``.
        :param dct: dict onto which the merge is executed
        :param merge_dct: dct merged into dct
        :return: None
        """
        for k, v in merge_dct.iteritems():
            if (k in dct and isinstance(dct[k], dict)
                    and isinstance(merge_dct[k], Mapping)):
                self.dict_merge(dct[k], merge_dct[k])
            else:
                dct[k] = merge_dct[k]
        
    def decode_payload(self, topic, payload):
        '''
        Format json for pretty printing, return string sutiable for logging, and a dict of the json data
        '''
        indent = self.master_indent + 31 #number of spaces to indent json data
        
        try:
            #if it's json data, decode it (use OrderedDict to preserve keys order), else return as is...
            json_data = json.loads(payload.replace(":nan", ":NaN").replace(":inf",":Infinity").replace(":-inf",":-Infinity"), object_pairs_hook=OrderedDict)
            if not isinstance(json_data, dict): #if it's not a dictionary, probably just a number
                return json_data, dict(json_data)
            json_data_string = "\n".join((indent * " ") + i for i in (json.dumps(json_data, indent = 2)).splitlines())

            formatted_data = "Decoded JSON: \n%s" % (json_data_string)
                
        except ValueError as e:
            formatted_data = payload
            
        if self.raw:
            formatted_data = payload

        return formatted_data, dict(json_data)
        
    def decode_topics(self, state, prefix=None):
        '''
        decode json data dict, and publish as individual topics to brokerFeedback/topic
        the keys are concatinated with _ to make one unique topic name
        strings are expressely converted to strings to avoid unicode representations
        '''
        for k, v in state.iteritems():
            if isinstance(v, dict):
                if prefix is None:
                    self.decode_topics(v, k)
                else:
                    self.decode_topics(v, prefix+"_"+k)
            else:
                if isinstance(v, list):
                    newlist = []
                    for i in v:
                        if isinstance(i, dict):
                            for ki, vi in i.iteritems():
                                newlist.append((str(ki), vi))
                        else:
                            if isinstance(i, basestring):
                                i = str(i)
                            newlist.append(i)
                    v = newlist
                if prefix is not None:
                    k = prefix+"_"+k
                k = k.replace("state_reported_","") #all data starts with this, so it's redundant
                #save variables for drawing map
                if k == "pose_theta":
                    self.co_ords["theta"] = v
                if k == "pose_point_x": #x and y are reversed...
                    self.co_ords["y"] = v
                if k == "pose_point_y":
                    self.co_ords["x"] = v
                if k == "bin_full":
                    self.bin_full = v
                if k == "cleanMissionStatus_error":
                    try:
                        self.error_message = self._ErrorMessages[v]
                    except KeyError as e:
                        log.warn("Error looking up Roomba error message %s" % e)
                        self.error_message = "Unknown Error number: %d" % v
                    self.publish("error_message", self.error_message)
                if k == "cleanMissionStatus_phase":
                    self.previous_cleanMissionStatus_phase = self.cleanMissionStatus_phase
                    self.cleanMissionStatus_phase = v
                
                self.publish(k, str(v))
        
        if prefix is None:
            self.update_state_machine()
            
    def update_state_machine(self, new_state = None):
        '''
        Roomba progresses through states (phases), current identified states are:
        ""              : program started up, no state yet
        "run"           : running on a Cleaning Mission
        "hmUsrDock"     : returning to Dock
        "hmMidMsn"      : need to recharge
        "hmPostMsn"     : mission completed
        "charge"        : chargeing
        "stuck"         : Roomba is stuck
        "stop"          : Stopped
        "pause"         : paused
        
        available states:
        states = {  "charge":"Charging",
                    "new":"New Mission",
                    "run":"Running",
                    "resume":"Running",
                    "hmMidMsn":"Recharging",
                    "recharge":"Recharging",
                    "stuck":"Stuck",
                    "hmUsrDock":"User Docking",
                    "dock":"Docking",
                    "dockend":"Docking - End Mission",
                    "cancelled":"Cancelled",
                    "stop":"Stopped",
                    "pause":"Paused",
                    "hmPostMsn":"End Mission",
                    "":None}
        
        Normal Sequence is "" -> charge -> run -> hmPostMsn -> charge
        Mid mission recharge is "" -> charge -> run -> hmMidMsn -> charge - > run -> hmPostMsn -> charge
        Stuck is "" -> charge -> run -> hmPostMsn -> stuck -> run/charge/stop/hmUsrDock -> charge
        Start program during run is "" -> run -> hmPostMsn -> charge
        
        Need to identify a new mission to initialize map, and end of mission to finalise map.
        Assume  charge -> run = start of mission (init map)
                stuck - > charge = init map
        Assume hmPostMsn -> charge = end of mission (finalize map)
        Anything else = continue with existing map
        '''
        
        current_mission = self.current_state
        
        #if self.current_state == None: #set initial state here for debugging
        #    self.current_state = self.states["recharge"]
        #    self.show_final_map = False
        
        if self.current_state == self.states["charge"] and self.cleanMissionStatus_phase == "run":
            self.current_state = self.states["new"]
        elif self.current_state == self.states["run"] and self.cleanMissionStatus_phase == "hmMidMsn":
            self.current_state = self.states["dock"]
        elif self.current_state == self.states["dock"] and self.cleanMissionStatus_phase == "charge" and not self.bin_full:
            self.current_state = self.states["recharge"]
        elif self.current_state == self.states["dock"] and self.cleanMissionStatus_phase == "charge" and self.bin_full:
            self.current_state = self.states["pause"]
        elif self.current_state == self.states["run"] and self.cleanMissionStatus_phase == "charge":
            self.current_state = self.states["recharge"]
        elif self.current_state == self.states["recharge"] and self.cleanMissionStatus_phase == "run":
            self.current_state = self.states["pause"]
        elif self.current_state == self.states["pause"] and self.cleanMissionStatus_phase == "charge":
            self.current_state = self.states["pause"]
        elif self.current_state == self.states["recharge"] and self.cleanMissionStatus_phase == "charge":
            self.current_state = self.states["recharge"]
            current_mission = None #so that we will draw map and can update recharge time
        elif self.current_state == self.states["charge"] and self.cleanMissionStatus_phase == "charge":
            current_mission = None #so that we will draw map and can update charge status
        elif (self.current_state == self.states["stop"] or self.current_state == self.states["pause"]) and self.cleanMissionStatus_phase == "hmUsrDock":
            self.current_state = self.states["cancelled"]
        elif (self.current_state == self.states["hmUsrDock"] or self.current_state == self.states["cancelled"]) and self.cleanMissionStatus_phase == "charge":
            self.current_state = self.states["dockend"]
        elif self.current_state == self.states["hmPostMsn"] and self.cleanMissionStatus_phase == "charge":
            self.current_state = self.states["dockend"]
        elif self.current_state == self.states["dockend"] and self.cleanMissionStatus_phase == "charge":
            self.current_state = self.states["charge"]
        
        else:
            self.current_state = self.states[self.cleanMissionStatus_phase]
         
        if new_state is not None:
            self.current_state = self.states[new_state]
            self.log.info("set current state to: %s" % (self.current_state))
            
        if self.current_state != current_mission:
            self.log.info("updated state to: %s" % (self.current_state))
            
        self.publish("state", self.current_state)
        self.draw_map(current_mission != self.current_state)
        
    def make_transparent(self, image, colour=None):
        '''
        take image and make white areas transparent
        return transparent image
        '''
        image = image.convert("RGBA")
        datas = image.getdata()
        newData = []
        for item in datas:
            if item[0] >= 254 and item[1] >= 254 and item[2] >= 254:    #white (ish)
                newData.append(self.transparent)
            else:
                if colour:
                    newData.append(colour)
                else:
                    newData.append(item)
                
        image.putdata(newData)
        return image
                    
    def make_icon(self, input="./roomba.png", output="./roomba_mod.png"):
        #utility function to make roomba icon from generic roomba icon
        if not HAVE_PIL: #drawing library loaded?
            self.log.error("PIL module not loaded")
            return None
        try:
            roomba = Image.open(input).convert('RGBA')
            roomba = roomba.rotate(90, expand=False)
            roomba = self.make_transparent(roomba)
            draw_wedge = ImageDraw.Draw(roomba)
            draw_wedge.pieslice([(5,0),(roomba.size[0]-5,roomba.size[1])], 175, 185, fill="red", outline="red")
            roomba.save(output, "PNG")
            return roomba
        except Exception as e:
            self.log.error("ERROR: %s" % e)
            return None
            
    def load_icon(self, filename="", icon_name=None, fnt=None, size=(32,32), base_icon=None):
        '''
        Load icon from file, or draw icon if file not found.
        returns icon object
        '''
        if icon_name is None:
            return None
            
        try:
            icon = Image.open(filename).convert('RGBA').resize(size, Image.ANTIALIAS)
            icon = self.make_transparent(icon)
        except IOError as e:
            self.log.warn("error loading %s: %s, using default icon instead" % (icon_name,e))
            if base_icon is None:
                icon = Image.new('RGBA', size, self.transparent)
            else:
                icon = base_icon
                
            draw_icon = ImageDraw.Draw(icon)
                
            if icon_name == "roomba":
                if base_icon is None:
                    draw_icon.ellipse([(5,5),(icon.size[0]-5,icon.size[1]-5)], fill="green", outline="black")
                draw_icon.pieslice([(5,5),(icon.size[0]-5,icon.size[1]-5)], 355, 5, fill="red", outline="red")
            elif icon_name == "stuck":
                if base_icon is None:
                    draw_icon.ellipse([(5,5),(icon.size[0]-5,icon.size[1]-5)], fill="green", outline="black")
                    draw_icon.pieslice([(5,5),(icon.size[0]-5,icon.size[1]-5)], 175, 185, fill="red", outline="red")
                draw_icon.polygon([(icon.size[0]/2,icon.size[1]), (0, 0), (0,icon.size[1])], fill = 'red')
                if fnt is not None:
                    draw_icon.text((4,-4), "!", font=fnt, fill=(255,255,255,255))
            elif icon_name == "cancelled":
                if base_icon is None:
                    draw_icon.ellipse([(5,5),(icon.size[0]-5,icon.size[1]-5)], fill="green", outline="black")
                    draw_icon.pieslice([(5,5),(icon.size[0]-5,icon.size[1]-5)], 175, 185, fill="red", outline="red")
                if fnt is not None:
                    draw_icon.text((4,-4), "X", font=fnt, fill=(255,0,0,255))
            elif icon_name == "bin full":
                draw_icon.rectangle([icon.size[0]-10,icon.size[1]-10,icon.size[0]+10,icon.size[1]+10], fill = "grey")
                if fnt is not None:
                    draw_icon.text((4,-4), "F", font=fnt, fill=(255,255,255,255))
            elif icon_name == "battery":
                draw_icon.rectangle([icon.size[0]-10,icon.size[1]-10,icon.size[0]+10,icon.size[1]+10], fill = "orange")
                if fnt is not None:
                    draw_icon.text((4,-4), "B", font=fnt, fill=(255,255,255,255))
            elif icon_name == "home":
                draw_icon.rectangle([0,0,32,32], fill="red", outline="black")
                if fnt is not None:
                    draw_icon.text((4,-4), "D", font=fnt, fill=(255,255,255,255))
            else:
                icon = None
        #rotate icon 180 degrees
        icon = icon.rotate(180-self.angle, expand=False)
        return icon
        
    def initialise_map(self, roomba_size):
        '''
        Initialize all map items (base maps, overlay, icons fonts etc)
        '''
        # get base image of Roomba path
        if self.base is None:
            try:
                self.log.info("MAP: openening existing line image")
                self.base = Image.open(self.mapPath+'/'+self.roombaName+'lines.png').convert('RGBA')
                if self.base.size != (self.mapSize[0], self.mapSize[1]):
                    raise IOError("Image is wrong size")
            except IOError as e:
                self.base = Image.new('RGBA', (self.mapSize[0], self.mapSize[1]), self.transparent)
                self.log.warn("MAP: line image problem: %s: created new image" % e)
                
            try:
                self.log.info("MAP: openening existing problems image")
                self.roomba_problem = Image.open(self.mapPath+'/'+self.roombaName+'problems.png').convert('RGBA')
                if self.roomba_problem.size != self.base.size:
                    raise IOError("Image is wrong size")
            except IOError as e:
                self.roomba_problem = Image.new('RGBA', self.base.size, self.transparent)
                self.log.warn("MAP: problems image problem: %s: created new image" % e)
            
            try:
                self.log.info("MAP: openening existing room outline image")
                self.room_outline = Image.open(self.mapPath+'/'+self.roombaName+'room.png').convert('RGBA')
                #self.room_outline = self.make_transparent(self.room_outline, (64,64,64,255)) # grey border
                if self.room_outline.size != self.base.size:
                    raise IOError("Image is wrong size")
            except IOError as e:
                self.room_outline = Image.new('RGBA', self.base.size, self.transparent)
                self.log.warn("MAP: room outline image problem: %s: set to None" % e)
                
            try:
                self.log.info("MAP: openening existing map no text image")
                self.previous_map_no_text = None
                self.map_no_text = Image.open(self.mapPath+'/'+self.roombaName+'map_notext.png').convert('RGBA')
                if self.map_no_text.size != self.base.size:
                    raise IOError("Image is wrong size")
            except IOError as e:
                self.map_no_text = None
                self.log.warn("MAP: map no text image problem: %s: set to None" % e)
        
        self.cx = self.base.size[0]  #save x and y center of image, for centering of final map image
        self.cy = self.base.size[1]
        
        # get a font
        if self.fnt is None:
            try:
                self.fnt = ImageFont.truetype('FreeMono.ttf', 40)
            except IOError as e:
                self.log.warn("error loading font: %s, loading default font" % e)
                self.fnt = ImageFont.load_default()
                
        #set dock home position
        if self.home_pos is None:
            self.home_pos = (self.mapSize[0]/2+self.mapSize[2], self.mapSize[1]/2+self.mapSize[3])
            self.log.info("MAP: home_pos: (%d,%d)" % (self.home_pos[0], self.home_pos[1]))
                
        #get icons
        if self.roomba_icon is None:
            self.roomba_icon = self.load_icon(filename=self.roomba_icon_file, icon_name="roomba", fnt=self.fnt, size=roomba_size, base_icon=None)
     
        if self.roomba_error_icon is None:
            self.roomba_error_icon = self.load_icon(filename=self.roomba_error_file, icon_name="stuck", fnt=self.fnt, size=roomba_size, base_icon=self.roomba_icon)
            
        if self.roomba_cancelled_icon is None:
            self.roomba_cancelled_icon = self.load_icon(filename=self.roomba_cancelled_file, icon_name="cancelled", fnt=self.fnt, size=roomba_size, base_icon=self.roomba_icon)

        if self.roomba_battery_icon is None:
            self.roomba_battery_icon = self.load_icon(filename=self.roomba_battery_file, icon_name="battery", fnt=self.fnt, size=roomba_size, base_icon=self.roomba_icon)
 
        if self.dock_icon is None and self.home_icon_file is not None:
            self.dock_icon = self.load_icon(filename=self.home_icon_file, icon_name="home", fnt=self.fnt)
            self.dock_position =(self.home_pos[0]-self.dock_icon.size[0]/2, self.home_pos[1]-self.dock_icon.size[1]/2)
        
        if self.bin_full_icon is None:
            self.bin_full_icon = self.load_icon(filename=self.bin_full_file, icon_name="bin full", fnt=self.fnt, size=roomba_size, base_icon=self.roomba_icon)
            
        self.log.info("MAP: Initialisation complete")
        
    def transparent_paste(self, base_image, icon, position):
        '''
        needed because PIL pasting of transparent imges gives weird results
        '''
        image = Image.new('RGBA', self.base.size, self.transparent)
        image.paste(icon,position)
        base_image = Image.alpha_composite(base_image, image)
        return base_image
        
    def zero_coords(self):
        '''
        returns dictionary with default zero coords
        '''
        return {"x":0,"y":0,"theta":180}
        
    def offset_coordinates(self, old_co_ords, new_co_ords):
        '''
        offset coordinates according to mapSize settings, with 0,0 as center
        '''
        x_y = (new_co_ords["x"]+self.mapSize[0]/2+self.mapSize[2], new_co_ords["y"]+self.mapSize[1]/2+self.mapSize[3])
        old_x_y = (old_co_ords["x"]+self.mapSize[0]/2+self.mapSize[2], old_co_ords["y"]+self.mapSize[1]/2+self.mapSize[3])

        theta = int(new_co_ords["theta"]-90+self.roomba_angle)
        while theta > 359: theta = 360-theta
        while theta < 0: theta = 360+theta
        
        return old_x_y, x_y, theta
        
    def get_roomba_pos(self, x_y):
        '''
        calculate roomba position as list
        '''
        return [x_y[0]-self.roomba_icon.size[0]/2, x_y[1]-self.roomba_icon.size[1]/2, x_y[0]+self.roomba_icon.size[0]/2, x_y[1]+self.roomba_icon.size[1]/2]
        
    def draw_vacuum_lines(self, image, old_x_y, x_y, theta, colour="lawngreen"):
        '''
        draw lines on image from old_x_y to x_y reepresenting vacuum coverage, taking into account angle theta
        (roomba angle).
        '''
        lines = ImageDraw.Draw(image)
        if x_y != old_x_y:
            self.log.info("MAP: drawing line: %s, %s" % (old_x_y, x_y))
            lines.line([old_x_y, x_y], fill=colour, width=self.roomba_icon.size[0]/2)
        #draw circle over roomba vacuum area to give smooth edges.
        arcbox =[x_y[0]-self.roomba_icon.size[0]/4, x_y[1]-self.roomba_icon.size[0]/4,x_y[0]+self.roomba_icon.size[0]/4,x_y[1]+self.roomba_icon.size[0]/4]
        lines.ellipse(arcbox, fill=colour)
        
    def draw_text(self, image, display_text, fnt, pos=(0,0), colour=(0,0,255,255), rotate=False):
        #draw text - (WARNING old versions of PIL have huge memory leak here!)
        if display_text is None: return
        self.log.info("MAP: writing text: pos: %s, text: %s" % (pos, display_text))
        if rotate:
            txt = Image.new('RGBA', (fnt.getsize(display_text)), self.transparent)
            text = ImageDraw.Draw(txt)
            # draw text rotated 180 degrees...
            text.text((0,0), display_text, font=fnt, fill=colour)
            image.paste(txt.rotate(180-self.angle, expand=True), pos)
        else:
            text = ImageDraw.Draw(image)
            text.text(pos, display_text, font=fnt, fill=colour)
 
    def draw_map(self, force_redraw=False):
        '''
        Draw map of Roomba cleaning progress
        '''
        if ((self.co_ords != self.previous_co_ords or self.cleanMissionStatus_phase != self.previous_cleanMissionStatus_phase)  or force_redraw) and self.drawmap:
            self.render_map(self.co_ords, self.previous_co_ords)
            self.previous_co_ords = self.co_ords.copy()
            self.previous_cleanMissionStatus_phase = self.cleanMissionStatus_phase
            
    def render_map(self, new_co_ords, old_co_ords):
        '''
        draw map
        '''        
        draw_final = False
        stuck = False
        cancelled = False
        bin_full = False
        battery_low = False
        
        if self.current_state is None:      #program just started, and we don't have phase yet.
            return
        
        if self.show_final_map == False:
            self.log.info("MAP: received: new_co_ords: %s old_co_ords: %s phase: %s, state: %s" % (new_co_ords, old_co_ords, self.cleanMissionStatus_phase, self.current_state))
         
        if  self.current_state == self.states["charge"]:
            self.log.info("MAP: ignoring new co-ords in charge phase")
            new_co_ords = old_co_ords = self.zero_coords()
            self.display_text = "Charging: Battery: " + str(self.master_state["state"]["reported"]["batPct"]) + "%"
            if self.bin_full:
                self.display_text = "Bin Full," + self.display_text.replace("Charging", "Not Ready")
            if self.last_completed_time is None or time.time() - self.last_completed_time > 3600:
                self.save_text_and_map_on_whitebg(self.map_no_text)
            draw_final = True
            
        elif self.current_state == self.states["recharge"]:
            self.log.info("MAP: ignoring new co-ords in recharge phase")
            new_co_ords = old_co_ords = self.zero_coords()
            self.display_text = "Recharging:" + " Time: " + str(self.master_state["state"]["reported"]["cleanMissionStatus"]["rechrgM"]) + "m"
            if self.bin_full:
                self.display_text = "Bin Full," + self.display_text
            self.save_text_and_map_on_whitebg(self.map_no_text)
            
        elif self.current_state == self.states["pause"]:
            self.log.info("MAP: ignoring new co-ords in pause phase")
            new_co_ords = old_co_ords# = self.zero_coords()
            self.display_text = "Paused:" + " Time: " + time.strftime("%a %b %d %H:%M:%S")
            if self.bin_full:
                self.display_text = "Bin Full," + self.display_text
            self.save_text_and_map_on_whitebg(self.map_no_text)
                
        elif self.current_state == self.states["hmPostMsn"]:
            self.display_text = "Completed: " + time.strftime("%a %b %d %H:%M:%S")
            self.log.info("MAP: end of mission")    
            
        elif self.current_state == self.states["dockend"]:
            self.log.info("MAP: mission completed: ignoring new co-ords in docking phase")
            new_co_ords = old_co_ords = self.zero_coords()
            self.draw_final_map(True)
            draw_final = True   
            
        elif self.current_state == self.states["run"] or self.current_state == self.states["stop"] or self.current_state == self.states["pause"]:
            if self.current_state == self.states["run"]:
                self.display_text = self.states["run"] + " Time: " + str(self.master_state["state"]["reported"]["cleanMissionStatus"]["mssnM"]) + "m, Bat: "+ str(self.master_state["state"]["reported"]["batPct"]) + "%"
            else:
                self.display_text = None
            self.show_final_map = False
            
        elif self.current_state == self.states["new"]:
            self.angle = self.mapSize[4]    #reset angle
            self.base = Image.new('RGBA', self.base.size, self.transparent)
            self.roomba_problem = Image.new('RGBA', self.base.size, self.transparent) #overlay for roomba problem position
            self.show_final_map = False
            self.display_text = None
            self.log.info("MAP: created new image at start of new run")  
            
        elif self.current_state == self.states["stuck"]:
            self.display_text = "STUCK!: " + time.strftime("%a %b %d %H:%M:%S")
            self.draw_final_map(True)
            draw_final = True
            stuck = True   
            
        elif self.current_state == self.states["cancelled"]:
            self.display_text = "Cancelled: " + time.strftime("%a %b %d %H:%M:%S")
            cancelled = True
        
        elif self.current_state == self.states["dock"]:
            self.display_text = "Docking"
            if self.bin_full:
                self.display_text = "Bin Full," + self.display_text
                bin_full = True
            else:
                self.display_text = "Battery low: " + str(self.master_state["state"]["reported"]["batPct"]) + "%, " + self.display_text
                battery_low = True
            
        else:
            self.log.warn("MAP: no special handling for state: %s" % self.current_state)
            
        if self.base is None:
            self.log.warn("MAP: no image, exiting...")
            return
            
        if self.display_text is None:
            self.display_text = self.current_state
            
        if self.show_final_map: #just display final map - not live
            self.log.debug("MAP: not updating map - Roomba not running")
            return
            
        if self.debug:
            self.draw_final_map() #debug final map (careful, uses a lot of CPU power!)
            
        #calculate co-ordinates, with 0,0 as center
        old_x_y, x_y, theta = self.offset_coordinates(old_co_ords, new_co_ords)
        roomba_pos = self.get_roomba_pos(x_y)

        self.log.info("MAP: old x,y: %s new x,y: %s theta: %s roomba pos: %s" % (old_x_y, x_y, theta, roomba_pos))

        #draw lines
        self.draw_vacuum_lines(self.base, old_x_y, x_y, theta)

        # make a blank image for the text and Roomba overlay, initialized to transparent text color
        roomba_sprite = Image.new('RGBA', self.base.size, self.transparent)
        
        #draw roomba
        self.log.info("MAP: drawing roomba: pos: %s, theta: %s" % (roomba_pos, theta))
        if stuck:
            self.log.info("MAP: Drawing stuck Roomba")
            self.roomba_problem.paste(self.roomba_error_icon,roomba_pos)
        if cancelled:
            self.log.info("MAP: Drawing cancelled Roomba")
            self.roomba_problem.paste(self.roomba_cancelled_icon,roomba_pos)
        if bin_full:
            self.log.info("MAP: Drawing full bin")
            self.roomba_problem.paste(self.bin_full_icon,roomba_pos)
        if battery_low:
            self.log.info("MAP: Drawing low battery Roomba")
            self.roomba_problem.paste(self.roomba_battery_icon,roomba_pos) 
        
        roomba_sprite = self.transparent_paste(roomba_sprite, self.roomba_icon.rotate(theta, expand=False), roomba_pos)
        
        # paste dock over roomba_sprite
        if self.dock_icon is not None:
            roomba_sprite = self.transparent_paste(roomba_sprite, self.dock_icon, self.dock_position)
        
        #save base lines
        self.base.save(self.mapPath+'/'+self.roombaName+'lines.png', "PNG")
        #save problem overlay
        self.roomba_problem.save(self.mapPath+'/'+self.roombaName+'problems.png', "PNG")
        #merge lines with rooma overlay
        out = Image.alpha_composite(self.base, roomba_sprite)
        #merge problem location for roomba into out
        out = Image.alpha_composite(out, self.roomba_problem)
        #draw room outline (saving results if this is a final map) update x,y and angle if auto_rotate
        self.draw_room_outline(draw_final)
        out = Image.alpha_composite(out, self.room_outline)   #paste room outline onto background
        if draw_final and self.auto_rotate:
            #translate image to center it if auto_rotate is on
            self.log.info("MAP: calculation of center: %s, translating final map to center it, x:%d, y:%d deg: %.2f" % ((self.cx,self.cy),self.cx-out.size[0]/2,self.cy-out.size[1]/2,self.angle))
            out = out.transform(out.size, Image.AFFINE, (1, 0, self.cx-out.size[0]/2, 0, 1, self.cy-out.size[1]/2))
        out_rotated = out.rotate(180+self.angle, expand=True).resize(self.base.size)    #map is upside down, so rotate 180 degrees, and size to fit
        #save composite image
        self.save_text_and_map_on_whitebg(out_rotated)
        if draw_final:
            self.show_final_map = True  #prevent re-drawing of map until reset
    
    def save_text_and_map_on_whitebg(self, map):
        if map is None or (map == self.previous_map_no_text and self.previous_display_text == self.display_text): #if no map or nothing changed
            return
        self.map_no_text = map
        self.previous_map_no_text = self.map_no_text
        self.previous_display_text = self.display_text
        self.map_no_text.save(self.mapPath+'/'+self.roombaName+'map_notext.png', "PNG")
        final = Image.new('RGBA', self.base.size, (255,255,255,255))    #white
        final = Image.alpha_composite(final, map)   #paste onto a white background, so it's easy to see
        #draw text
        self.draw_text(final, self.display_text, self.fnt)
        final.save(self.mapPath+'/'+self.roombaName+'_map.png', "PNG")
        os.rename(self.mapPath+'/'+self.roombaName+'_map.png',self.mapPath+'/'+self.roombaName+'map.png')   #try to avoid other programs reading file while writing it, rename should be atomic.       
    
    def ScaleRotateTranslate(self, image, angle, center = None, new_center = None, scale = None, expand=False):
        '''
        experimental - not used yet
        '''
        if center is None:
            return image.rotate(angle, expand)
        angle = -angle/180.0*math.pi
        nx,ny = x,y = center
        if new_center != center:
            (nx,ny) = new_center
        sx=sy=1.0
        if scale:
            (sx,sy) = scale
        cosine = math.cos(angle)
        sine = math.sin(angle)
        a = cosine/sx
        b = sine/sx
        c = x-nx*a-ny*b
        d = -sine/sy
        e = cosine/sy
        f = y-nx*d-ny*e
        return image.transform(image.size, Image.AFFINE, (a,b,c,d,e,f), resample=Image.BICUBIC)
    
    def draw_room_outline(self, overwrite=False, colour=(64,64,64,255), width=1):
        '''
        draw room outline
        '''
        self.log.info("MAP: checking room outline")
        if HAVE_CV2:
            if self.room_outline_contour is None:
                try:
                    self.room_outline_contour = np.load(self.mapPath+'/'+self.roombaName+'room.npy')
                except IOError as e:
                    self.log.warn("Unable to load room outline: %s, setting to 0" % e)
                    self.room_outline_contour = np.array([(0,0),(0,0),(0,0),(0,0)], dtype=np.int)
            room_outline_area = cv2.contourArea(self.room_outline_contour)
            edgedata = cv2.add(np.array(self.base.convert('L'), dtype=np.uint8), np.array(self.room_outline.convert('L'), dtype=np.uint8))
            _, contours, _ = self.findContours(edgedata,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE) #find external contour
            if contours[0] is None: return
            if len(contours[0]) < 5: return
            max_area = cv2.contourArea(contours[0])
            if max_area > room_outline_area:
                self.log.info("MAP: found new outline perimiter")
                self.room_outline_contour = contours[0]
                perimeter = cv2.arcLength(self.room_outline_contour,True)
                outline = Image.new('RGBA',self.base.size,self.transparent)
                edgeimage = np.array(outline)   #make blank RGBA image array
                approx = cv2.approxPolyDP(self.room_outline_contour,self.draw_edges*perimeter,True) #self.draw_edges is the max deviation from a line (set to 0.3%) - you can fiddle with this
                cv2.drawContours(edgeimage,[approx] , -1, colour, width) #outline with grey, width 1
                self.room_outline = Image.fromarray(edgeimage)
                
        else:
            edges = ImageOps.invert(self.room_outline.convert('L'))
            edges.paste(self.base)
            edges = edges.convert('L').filter(ImageFilter.SMOOTH_MORE)
            edges = ImageOps.invert(edges.filter(ImageFilter.FIND_EDGES))
            self.room_outline = self.make_transparent(edges, (0, 0, 0, 255))
        
        #self.test_get_image_parameters(self.room_outline)   # debugging
        if overwrite or self.debug:
            self.room_outline.save(self.mapPath+'/'+self.roombaName+'room.png', "PNG") #save room outline
            if HAVE_CV2:
                np.save(self.mapPath+'/'+self.roombaName+'room.npy', self.room_outline_contour) #save room outline contour as numpy array
            if self.auto_rotate:
                self.get_image_parameters(image=self.room_outline, contour=self.room_outline_contour, final=overwrite)  #update map centre and angle
            self.log.info("MAP: Wrote new room outline files")
 
    def test_get_image_parameters(self, image=None):
        '''
        FOR TESTING ONLY!
        updates angle of image, and centre using cv2 or PIL.
        NOTE: this assumes the floorplan is rectangular! if you live in a lighthouse, the angle will not be valid!
        input is cv2 contour or PIL image
        '''
        if image is not None and HAVE_PIL:
            imbw = image.convert('L')
            max_area = self.base.size[0] * self.base.size[1]
            x_y = (self.base.size[0]/2, self.base.size[1]/2)
            final_angle = self.angle
            for angle in range(90, 0, -1):
                im = imbw.rotate(angle, expand=True).resize(self.base.size)    #rotate image and resize to fit
                box = im.getbbox()
                if box is not None:
                    area = (box[2]-box[0]) * (box[3]-box[1])
                    if area < max_area:
                        final_angle = angle 
                        x_y = ((box[2]-box[0])/2+box[0], (box[3]-box[1])/2+box[1])
                        max_area = area
                    
            if final_angle < self.angle-45:
                final_angle += 90
            if final_angle > 45-self.angle:
                final_angle -= 90
            angle = final_angle
        else:
            return

        self.log.info("MAP: PIL_TEST: image center: x:%d, y:%d, angle %.2f" % (x_y[0], x_y[1], angle))

    def get_image_parameters(self, image=None, contour=None, final=False):
        '''
        updates angle of image, and centre using cv2 or PIL.
        NOTE: this assumes the floorplan is rectangular! if you live in a lighthouse, the angle will not be valid!
        input is cv2 contour or PIL image
        '''
        if contour is not None and HAVE_CV2:
            x_y,l_w,angle = cv2.minAreaRect(contour)  #returns (x,y), (width, height), theta - where (x,y) is the center
            if angle < self.angle-45:
                angle += 90
            if angle > 45-self.angle:
                angle -= 90
                
        elif image is not None and HAVE_PIL:
            imbw = image.convert('L')
            max_area = self.base.size[0] * self.base.size[1]
            x_y = (self.base.size[0]/2, self.base.size[1]/2)
            final_angle = self.angle
            for angle in range(90, 0, -1):
                im = imbw.rotate(angle, expand=True).resize(self.base.size)    #rotate image and resize to fit
                box = im.getbbox()
                if box is not None:
                    area = (box[2]-box[0]) * (box[3]-box[1])
                    if area < max_area:
                        final_angle = angle 
                        x_y = ((box[2]-box[0])/2+box[0], (box[3]-box[1])/2+box[1])
                        max_area = area
                    
            if final_angle < self.angle-45:
                final_angle += 90
            if final_angle > 45-self.angle:
                final_angle -= 90
            angle = final_angle
        else:
            return
        
        if final:
            self.cx = x_y[0]
            self.cy = x_y[1]
            self.angle = angle
        self.log.info("MAP: image center: x:%d, y:%d, angle %.2f" % (x_y[0], x_y[1], angle))
        
    def angle_between(self, p1, p2):
        '''
        clockwise angle between two points in degrees
        '''
        if HAVE_CV2:
            ang1 = np.arctan2(*p1[::-1])
            ang2 = np.arctan2(*p2[::-1])
            return np.rad2deg((ang1 - ang2) % (2 * np.pi))
        else:
            side1=math.sqrt(((p1[0]-p2[0])**2))
            side2=math.sqrt(((p1[1]-p2[1])**2))
            return math.degrees(math.atan(side2/side1))
            
    def findContours(self,image,mode,method):
        '''
        Version independent find contours routine. Works with OpenCV 2 or 3.
        Returns modified image (with contours applied), contours list, hierarchy
        '''
        ver = int(cv2.__version__.split(".")[0])
        im = image.copy()
        if ver == 2:
            contours, hierarchy = cv2.findContours(im,mode,method)
            return im, contours, hierarchy
        else:
            im_cont, contours, hierarchy = cv2.findContours(im,mode,method)
            return im_cont, contours, hierarchy
            
    def draw_final_map(self, overwrite=False):
        merge = Image.new('RGBA',self.base.size,self.transparent)
        if HAVE_CV2:
            #NOTE: this is CPU intensive!
            edgedata = np.array(self.base.convert('L'), dtype=np.uint8)
            _, contours, _ = self.findContours(edgedata,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE) #find all contours
            edgedata.fill(0) #zero edge data for later use
            max_perimeter = 0
            max_contour = None
            for cnt in contours:
                perimeter = cv2.arcLength(cnt,True)
                if perimeter >= max_perimeter:
                    max_contour = cnt   #get the contour with maximum length
                    max_perimeter = perimeter
            if max_contour is None: return
            if len(max_contour) < 5: return
            try:
                contours.remove(max_contour)    #remove max contour from list
            except ValueError:
                self.log.warn("MAP: unable to remove contour")
                pass
            
            mask = np.full(edgedata.shape, 255, dtype=np.uint8) #white
            cv2.drawContours(mask,contours,-1,0,-1)   #create mask (of other contours) in black
            
            approx = cv2.approxPolyDP(max_contour,self.draw_edges*max_perimeter,True) #self.draw_edges is the max deviation from a line (set to 0.25%) - you can fiddle with this

            bgimage = np.array(merge)   #make blank RGBA image array
            cv2.drawContours(bgimage,[approx] , -1, (124,252,0,255), -1) #fill with "lawngreen"
            bgimage = cv2.bitwise_and(bgimage,bgimage,mask = mask)  #mask image with internal contours
            cv2.drawContours(edgedata,[approx] , -1, (255), 1)  #draw longest contour aproximated to lines (in black), width 1
            
            outline = Image.fromarray(edgedata) #outline
            base = Image.fromarray(bgimage)   #filled background image
        else:
            base = self.base.filter(ImageFilter.SMOOTH_MORE)
            outline = base.convert('L').filter(ImageFilter.FIND_EDGES)  #draw edges at end of mission
            
        edges = ImageOps.invert(outline)
        edges = self.make_transparent(edges, (0, 0, 0, 255))
        if self.debug:
            edges.save(self.mapPath+'/'+self.roombaName+'edges.png', "PNG")
        merge = Image.alpha_composite(merge,base)
        merge = Image.alpha_composite(merge,edges)
        if overwrite:
            self.log.info("MAP: Drawing final map")
            self.last_completed_time = time.time()
            self.base=merge
            
        if self.debug:
            merge_rotated = merge.rotate(180+self.angle, expand=True)
            merge_rotated.save(self.mapPath+'/'+self.roombaName+'final_map.png', "PNG")
        
#----------- End of Classes ------------

if __name__ == '__main__':
    #----------- Local Routines ------------
    
    def broker_on_connect(client, userdata, flags, rc):
        log.debug("Broker Connected with result code "+str(rc))
        #subscribe to roomba feedback, if there is more than one roomba, the roombaName is added to the topic to subscribe to
        if rc == 0:
            if brokerCommand != "":
                if len(roombas) == 1:
                    mqttc.subscribe(brokerCommand)
                else:
                    for myroomba in roomba_list:
                        mqttc.subscribe(myroomba.roombaName+"/"+brokerCommand)
            if brokerSetting != "":
                if len(roombas) == 1:
                    mqttc.subscribe(brokerSetting)
                else:
                    for myroomba in roomba_list:
                        mqttc.subscribe(myroomba.roombaName+"/"+brokerSetting)
                        
    def broker_on_message(mosq, obj, msg):
        #publish to roomba, if there is more than one roomba, the roombaName is added to the topic to publish to
        if "command" in msg.topic:
            log.info("Received COMMAND: %s" % str(msg.payload))
            if len(roombas) == 1:
                roomba_list[0].send_command(str(msg.payload))
            else:
                for myroomba in roomba_list:
                    if myroomba.roombaName in msg.topic:
                        myroomba.send_command(str(msg.payload))
        elif "setting" in msg.topic:
            log.info("Received SETTING: %s" % str(msg.payload))
            cmd = str(msg.payload).split()
            if len(roombas) == 1:
                roomba_list[0].set_preference(cmd[0], cmd[1])
            else:
                for myroomba in roomba_list:
                    if myroomba.roombaName in msg.topic:
                        myroomba.set_preference(cmd[0], cmd[1])
        else:
            log.warn("Unknown topic: %s" % str(msg.topic))
        
    def broker_on_publish(mosq, obj, mid):
        pass

    def broker_on_subscribe(mosq, obj, mid, granted_qos):
        log.debug("Broker Subscribed: %s %s" % (str(mid), str(granted_qos)))

    def broker_on_disconnect(mosq, obj, rc):
        log.debug("Broker disconnected")
        if rc == 0:
            sys.exit(0)

    def broker_on_log(mosq, obj, level, string):
        log.info(string)
        
    def read_config_file(file="./config.ini"):       
        #read config file
        Config = ConfigParser.ConfigParser()
        try:
            Config.read(file)
            log.info("reading info from config file %s" % file)
            roombas = {}
            for address in Config.sections():
                roombas[address] = {"blid": Config.get(address, "blid"), "password": Config.get(address, "password"), "roombaName": literal_eval(Config.get(address, "data"))["robotname"]}
        except Exception as e:
            log.warn("Error reading config file %s" %e)
        return roombas
        
    def setup_logger(logger_name, log_file, level=logging.DEBUG, console=False):
        try:
            l = logging.getLogger(logger_name)
            if logger_name ==__name__:
                formatter = logging.Formatter('[%(levelname)1.1s %(asctime)s] %(message)s')
            else:
                formatter = logging.Formatter('%(message)s')
            fileHandler = logging.handlers.RotatingFileHandler(log_file, mode='a', maxBytes=2000000, backupCount=5)
            fileHandler.setFormatter(formatter)
            if console == True:
              streamHandler = logging.StreamHandler()

            l.setLevel(level)
            l.addHandler(fileHandler)
            if console == True:
              streamHandler.setFormatter(formatter)
              l.addHandler(streamHandler)
        except IOError as e:
            if e[0] == 13: #errno Permission denied
                print("Error: %s: You probably don't have permission to write to the log file/directory - try sudo" % e)
            else:
                print("Log Error: %s" % e)
            sys.exit(1)
            
          
    #--------- End Local Routines ----------

    import argparse
    #-------- Command Line -----------------
    parser = argparse.ArgumentParser(description='Forward MQTT data from Roomba 980 to local MQTT broker')
    parser.add_argument('-f','--configfile', action='store',type=str, default="./config.ini", help='config file name (default: ./config.ini)')
    parser.add_argument('-n','--roombaName', action='store',type=str, default="", help='optional Roomba name (default: "")')
    parser.add_argument('-t','--topic', action='store',type=str, default="#", help='Roomba MQTT Topic to subscribe to (can use wildcards # and + default: #)')
    parser.add_argument('-T','--brokerFeedback', action='store',type=str, default="/roomba/feedback", help='Topic on broker to publish feedback to (default: /roomba/feedback)')
    parser.add_argument('-C','--brokerCommand', action='store',type=str, default="/roomba/command", help='Topic on broker to publish commands to (default: /roomba/command')
    parser.add_argument('-S','--brokerSetting', action='store',type=str, default="/roomba/setting", help='Topic on broker to publish settings to (default: /roomba/setting')
    parser.add_argument('-b','--broker', action='store',type=str, default=None, help='ipaddress of MQTT broker (default: None)')
    parser.add_argument('-p','--port', action='store',type=int, default=1883, help='MQTT broker port number (default: 1883)')
    parser.add_argument('-U','--user', action='store',type=str, default=None, help='MQTT broker user name (default: None)')
    parser.add_argument('-P','--password', action='store',type=str, default=None, help='MQTT broker password (default: None)')
    parser.add_argument('-R','--roombaIP', action='store',type=str, default=None, help='ipaddress of Roomba 980 (default: None)')
    parser.add_argument('-u','--blid', action='store',type=str, default=None, help='Roomba 980 blid (default: None)')
    parser.add_argument('-w','--roombaPassword', action='store',type=str, default=None, help='Roomba 980 password (default: None)')
    parser.add_argument('-i','--indent', action='store',type=int, default=0, help='Default indentation=auto')
    parser.add_argument('-l','--log', action='store',type=str, default="./Roomba.log", help='path/name of log file (default: ./Roomba.log)')
    parser.add_argument('-e','--echo', action='store_false', help='Echo to Console (default: True)', default = True)
    parser.add_argument('-D','--debug', action='store_true', help='debug mode', default = False)
    parser.add_argument('-r','--raw', action='store_true', help='Output raw data to mqtt, no decoding of json data', default = False)
    parser.add_argument('-j','--pretty_print', action='store_true', help='pretty print json in logs', default = False)
    parser.add_argument('-c','--continuous', action='store_false', help='Continuous connection to Roomba (default: True)', default = True)
    parser.add_argument('-d','--delay', action='store',type=int, default=1000, help='Disconnect period for non-continuous connection (default: 1000ms)')
    parser.add_argument('-m','--drawmap', action='store_false', help='Draw Roomba cleaning map (default: True)', default = True)
    parser.add_argument('-M','--mapPath', action='store',type=str, default="./", help='Location to store maps to (default: ./)')
    parser.add_argument('-s','--mapSize', action='store',type=str, default="(800,1500,0,0,0,0)", help='Map Size, Dock offset and skew for the map. (800,1500) is the size, (0,0) is the dock location, in the center of the map, 0 is the rotation of the map, 0 is the rotation of the roomba. use single quotes around the string. (default: \'(800,1500,0,0,0,0)\')')
    parser.add_argument('-I','--icon', action='store',type=str, default="./home.png", help='location of dock icon. (default: "./home.png")')
    parser.add_argument('-x','--exclude', action='store',type=str, default="", help='Exclude topics that have this in them (default: "")')
    parser.add_argument('--version', action='version', version="%(prog)s ("+__version__+")")
    
    arg = parser.parse_args()
      
    #----------- Global Variables -----------
    #-------------- Main --------------
     
    if arg.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
            
    #setup logging
    setup_logger(__name__, arg.log,level=log_level,console=arg.echo)

    log = logging.getLogger(__name__)
    
    #------------ Main ------------------

    log.info("*******************")
    log.info("* Program Started *")
    log.info("*******************")
    
    log.info("Paho MQTT Version: %s" % mqtt.VERSION_NUMBER)
    
    log.debug("-- DEBUG Mode ON -")
    log.info("<CNTRL C> to Exit")
    log.info("Roomba 980 MQTT data Interface")
    
    roombas = {}
    
    if arg.blid is None or arg.roombaPassword is None:
        roombas = read_config_file(arg.configfile)
        if len(roombas) == 0:
            log.warn("No roomba or config file defined, I will attempt to discover Roombas, please put the Roomba on the dock and follow the instructions:")
            if arg.roombaIP is None:
                password(file=arg.configfile)
            else:
                password(arg.roombaIP,file=arg.configfile)
            roombas = read_config_file(arg.configfile)
            if len(roombas) == 0:
                log.error("No Roombas found! You must specify RoombaIP, blid and roombaPassword to run this program, or have a config file, use -h to show options.")
                sys.exit(0)
            else:
                log.info("Success! %d Roombas Found!" % len(roombas))
    else:
        roombas[arg.roombaIP] = {"blid": arg.blid, "password": arg.roombaPassword, "roombaName": arg.roombaName}
   
    #set broker = "127.0.0.1"  # mosquitto broker is running on localhost
    mqttc = None
    if arg.broker is not None:
        brokerCommand = arg.brokerCommand
        brokerSetting = arg.brokerSetting
        
        #connect to broker
        mqttc = mqtt.Client()
        # Assign event callbacks
        mqttc.on_message = broker_on_message
        mqttc.on_connect = broker_on_connect
        mqttc.on_disconnect = broker_on_disconnect
        mqttc.on_publish = broker_on_publish
        mqttc.on_subscribe = broker_on_subscribe
        #mqttc.on_log = broker_on_log   #uncomment to enable logging
    
        try:
            if arg.user != None:
                mqttc.username_pw_set(arg.user, arg.password)
            log.info("connecting to broker")
            mqttc.connect(arg.broker, arg.port, 60) # Ping MQTT broker every 60 seconds if no data is published from this script.
            
        except socket.error:
            log.error("Unable to connect to MQTT Broker")
            mqttc = None
    
    roomba_list = []
    for addr, info in roombas.iteritems():
        log.info("Creating Roomba object %s" % addr)
        #NOTE: cert_name is a default certificate. change this if your certificates are in a different place. any valid certificate will do, it's not used
        #      but needs to be there to enable mqtt TLS encryption
        #instansiate Roomba object
        #myroomba = Roomba(address, blid, roombaPassword)  #minnimum required to connect on Linux Debian system
        roomba_list.append(Roomba(addr, blid=info["blid"], password=info["password"], topic=arg.topic, continuous=arg.continuous, clean=False, cert_name = "./ca-certificates.crt", roombaName=info["roombaName"]))
     
    for myroomba in roomba_list:
        log.info("connecting Roomba %s" % myroomba.address)
        #all these are optional, if you don't include them, the defaults will work just fine
        if arg.exclude != "":
            myroomba.exclude = arg.exclude
        myroomba.set_options(raw=arg.raw, indent=arg.indent, pretty_print=arg.pretty_print)
        if not arg.continuous:
            myroomba.delay = arg.delay/1000
        if arg.mapSize != "" and arg.mapPath != "":
            myroomba.enable_map(enable=True, mapSize=arg.mapSize, mapPath=arg.mapPath, home_icon_file=arg.icon)  #enable live maps, class default is no maps
        if arg.broker is not None:
            myroomba.set_mqtt_client(mqttc, arg.brokerFeedback) #if you want to publish Roomba data to your own mqtt broker (default is not to) if you have more than one roomba, and assign a roombaName, it is addded to this topic (ie brokerFeedback/roombaName)
        #finally connect to Roomba - (required!)
        myroomba.connect()
    
    try:
        if mqttc is not None:
            mqttc.loop_forever()
        else:
            while True:
                log.info("Roomba Data: %s" % json.dumps(myroomba.master_state, indent=2))
                time.sleep(5)
            
    except (KeyboardInterrupt, SystemExit):
        log.info("System exit Received - Exiting program")
        mqttc.disconnect()
        sys.exit(0)

