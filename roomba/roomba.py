#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Python 3.6 Program to connect to Roomba vacuum cleaners, dcode json, and forward to mqtt
server

Nick Waterton 24th April 2017: V 1.0: Initial Release
Nick Waterton 4th July   2017  V 1.1.1: Fixed MQTT protocol version, and map
paths, fixed paho-mqtt tls changes
Nick Waterton 5th July   2017  V 1.1.2: Minor fixes, CV version 3 .2 support
Nick Waterton 7th July   2017  V1.2.0: Added -o option "roomOutline" allows
enabling/disabling of room outline drawing, added auto creation of css/html files
Nick Waterton 11th July  2017  V1.2.1: Quick (untested) fix for room outlines
if you don't have OpenCV
Nick Waterton 3rd Feb  2018  V1.2.2: Quick (untested) fix for running directly (ie not installed)
Nick Waterton 12th April 2018 V1.2.3: Fixed image rotation bug causing distorted maps if map rotation was not 0.
Nick Waterton 21st Dec 2018 V1.2.4: Fixed problem with findContours with OpenCV V4. Note V4.0.0-alpha still returns 3 values, and so won't work.
Nick Wateton 7th Oct 2019 V1.2.5: changed PROTOCOL_TLSv1 to PROTOCOL_TLS to fix i7 connection problem after F/W upgrade.
Nick Waterton 12th Nov 2019 V1.2.6: added set_ciphers('DEFAULT@SECLEVEL=1') to ssl context to work arounf dh_key_too_small error.
Nick Waterton 14th Jan 2020 V1.2.7: updated error code list.
Nick Waterton 16th march 2020 V 1.2.8 fixed __version__ for Pillow v7 (replaced with __version__)
Nick Waterton 24th April 2020 V 1.2.9 added possibility to send json commands to Roomba
Nick Waterton 24th dec 2020 V 2.0.0: Complete re-write
Nick Waterton 26th Februaury 2021 v 2.0.0b changed battery low and bin full handling, added 'no battery' (error 101).
Nick Waterton 3rd march 2021 v 2.0.0c changed battery low when docked, added callback handling and flags, added tank level,
                                      changed bin full handling, recovery from error condition mapping and added floormaps
                                      updated error list
Nick Waterton 27th March 2021 V2.0.0d Fixed floorplan offset on webpage in map.js.
Nick Waterton 28th March 2021 V2.0.0e Added invery x, y option
Nick Waterton 19th April 2021 V2.0.0f: added set_ciphers('DEFAULT@SECLEVEL=1') to ssl context to work arounf dh_key_too_small error (requred for ubuntu 20.04).
Nick Waterton 3rd May 2021 V2.0.0g: More python 3.8 fixes.
Nick Waterton 7th May 2021 V2.0.0h: added "ignore_run" after mission complete as still geting bogus run states
Nick Waterton 17th May 2021 V2.0.0i: mission state machine rework due to bogus states still being reported. increased max_distance to 500
Nick Waterton 14th January 2022 V2.0.0j: Added ability to send json commands via mqtt for testing.
Nick Waterton 17th June 2022 V2.0.0k: Added error 216 "Charging base bag full"
Nick Waterton 12th jan 2023 V 2.0.1: Python 3.10 compatibility
'''

__version__ = "2.0.1"

import asyncio
from ast import literal_eval
#from collections import OrderedDict, Mapping
from collections.abc import Mapping
from password import Password
import datetime
import json
import math
import logging
import os
import socket
import ssl
import sys
import time
import textwrap
import io
import configparser

# Import trickery
global HAVE_CV2
global HAVE_MQTT
global HAVE_PIL
HAVE_CV2 = False
HAVE_MQTT = False
HAVE_PIL = False
try:
    import paho.mqtt.client as mqtt
    HAVE_MQTT = True
except ImportError:
    print("paho mqtt client not found")
try:
    import cv2
    import numpy as np
    HAVE_CV2 = True
except ImportError:
    print("CV or numpy module not found, falling back to PIL")

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageColor
    HAVE_PIL = True
except ImportError:
    print("PIL module not found, maps are disabled")
    
if sys.version_info < (3, 7):
    asyncio.get_running_loop = asyncio.get_event_loop
    
transparent = (0, 0, 0, 0)  #transparent colour

def make_transparent(image, colour=None):
    '''
    take image and make white areas transparent
    return transparent image
    '''
    image = image.convert("RGBA")
    datas = image.getdata()
    newData = []
    for item in datas:
        # white (ish)
        if item[0] >= 254 and item[1] >= 254 and item[2] >= 254:
            newData.append(transparent)
        else:
            if colour:
                newData.append(colour)
            else:
                newData.append(item)

    image.putdata(newData)
    return image
    
class icons():
    '''
    Roomba icons object
    '''
    def __init__(self, base_icon=None, angle=0, fnt=None, size=(50,50), log=None):
        #super().__init__()
        if log:
            self.log = log
        else:
            self.log = logging.getLogger("Roomba.{}".format(__name__))
        self.angle = angle
        self.fnt = fnt
        self.size = size
        self.base_icon = base_icon
        if self.base_icon is None:
            self.base_icon = self.draw_base_icon()
        
        self.init_dict()
                        
    def init_dict(self):
        self.icons = {  'roomba'    : self.create_icon('roomba'),
                        'stuck'     : self.create_icon('stuck'),
                        'cancelled' : self.create_icon('cancelled'),
                        'battery'   : self.create_icon('battery'),
                        'bin full'  : self.create_icon('bin full'),
                        'tank low'  : self.create_icon('tank low'),
                        'home'      : self.create_icon('home', (32,32))
                     }
                        
    def __getitem__(self, name):
        return self.icons.get(name)
                        
    def set_font(self, fnt):
        self.fnt = fnt
        self.init_dict()
        
    def set_angle(self, angle):
        self.angle = angle
        
    def create_default_icon(self, name, size=None):
        self.icons[name] = self.create_icon(name, size)
            
    def load_icon_file(self, name, filename, size=None):
        try:
            if not size:
                size = self.size
            icon = Image.open(filename).convert('RGBA').resize(
                size,Image.ANTIALIAS)
            icon = make_transparent(icon)
            icon = icon.rotate(180-self.angle, expand=False)
            self.icons[name] = icon
            return True
        except IOError as e:
            self.log.warning('Error loading icon file: {} : {}'.format(filename, e))
            self.create_default_icon(name, size)
        return False
    
    @classmethod
    def make_icon(cls, input="./roomba.png", output="./roomba_mod.png"):
        #utility function to make roomba icon from generic roomba icon
        if not HAVE_PIL: #drawing library loaded?
            print("PIL module not loaded")
            return None
        try:
            roomba = Image.open(input).convert('RGBA')
            roomba = roomba.rotate(90, expand=False)
            roomba = make_transparent(roomba)
            draw_wedge = ImageDraw.Draw(roomba)
            draw_wedge.pieslice(
                [(5,0),(roomba.size[0]-5,roomba.size[1])],
                175, 185, fill="red", outline="red")
            roomba.save(output, "PNG")
            return roomba
        except Exception as e:
            print("ERROR: {}".format(e))
            return None
            
    def draw_base_icon(self, size=None):
        if not HAVE_PIL:
            return None
            
        icon = Image.new('RGBA', size if size else self.size, transparent)
        draw_icon = ImageDraw.Draw(icon)
        draw_icon.ellipse([(5,5),(icon.size[0]-5,icon.size[1]-5)],
                fill="green", outline="black")
        return icon

    def create_icon(self, icon_name, size=None):
        '''
        draw default icons, return icon drawing
        '''
        if not HAVE_PIL:
            return None
            
        if not size:
            size = self.size
            
        if icon_name in ['roomba', 'stuck', 'cancelled']:
            icon = self.base_icon.copy().resize(size,Image.ANTIALIAS)
        else:
            icon = Image.new('RGBA', size, transparent)
        draw_icon = ImageDraw.Draw(icon)
        if icon_name in ['stuck', 'cancelled']:
            draw_icon.pieslice([(5,5),(icon.size[0]-5,icon.size[1]-5)],
                175, 185, fill="red", outline="red")

        if icon_name == "roomba":
            draw_icon.pieslice([(5,5),(icon.size[0]-5,icon.size[1]-5)],
                355, 5, fill="red", outline="red")
        elif icon_name == "cancelled":
            if self.fnt is not None:
                draw_icon.text((4,-4), "X", font=self.fnt, fill=(255,0,0,255))
        elif icon_name == "stuck":
            draw_icon.polygon([(
                icon.size[0]//2,icon.size[1]), (0, 0), (0,icon.size[1])],
                fill = 'red')
            if self.fnt is not None:
                draw_icon.text((4,-4), "!", font=self.fnt,
                    fill=(255,255,255,255))
        elif icon_name == "bin full":
            draw_icon.rectangle([
                icon.size[0]-10, icon.size[1]-10,
                icon.size[0]+10, icon.size[1]+10],
                fill = "grey")
            if self.fnt is not None:
                draw_icon.text((4,-4), "F", font=self.fnt,
                    fill=(255,255,255,255))
        elif icon_name == "tank low":
            draw_icon.rectangle([
                icon.size[0]-10, icon.size[1]-10,
                icon.size[0]+10, icon.size[1]+10],
                fill = "blue")
            if self.fnt is not None:
                draw_icon.text((4,-4), "L", font=self.fnt,
                    fill=(255,255,255,255))
        elif icon_name == "battery":
            draw_icon.rectangle([icon.size[0]-10, icon.size[1]-10,
                icon.size[0]+10,icon.size[1]+10], fill = "orange")
            if self.fnt is not None:
                draw_icon.text((4,-4), "B", font=self.fnt,
                    fill=(255,255,255,255))
        elif icon_name == "home":
            draw_icon.rectangle([0,0,32,32], fill="red", outline="black")
            if self.fnt is not None:
                draw_icon.text((4,-4), "D", font=self.fnt,
                    fill=(255,255,255,255))
        else:
            return None
        #rotate icon 180 degrees
        icon = icon.rotate(180-self.angle, expand=False)
        return icon



class Roomba(object):
    '''
    This is a Class for Roomba WiFi connected Vacuum cleaners and mops
    Requires firmware version 2.0 and above (not V1.0). Tested with Roomba 980, s9
    and braava M6.
    username (blid) and password are required, and can be found using the
    Password() class (in password.py - or can be auto discovered)
    Most of the underlying info was obtained from here:
    https://github.com/koalazak/dorita980 many thanks!
    The values received from the Roomba as stored in a dictionary called
    master_state, and can be accessed at any time, the contents are live, and
    will build with time after connection.
    This is not needed if the forward to mqtt option is used, as the events will
    be decoded and published on the designated mqtt client topic.
    '''

    VERSION = __version__ = "2.0i"

    states = {"charge"          : "Charging",
              "new"             : "New Mission",
              "run"             : "Running",
              "resume"          : "Running",
              "hmMidMsn"        : "Docking",
              "recharge"        : "Recharging",
              "stuck"           : "Stuck",
              "hmUsrDock"       : "User Docking",
              "completed"       : "Mission Completed",
              "cancelled"       : "Cancelled",
              "stop"            : "Stopped",
              "pause"           : "Paused",
              "evac"            : "Emptying",
              "hmPostMsn"       : "Docking - End Mission",
              "chargingerror"   : "Base Unplugged",
              ""                :  None}
    
    # from various sources
    _ErrorMessages = {
        0: "None",
        1: "Left wheel off floor",
        2: "Main brushes stuck",
        3: "Right wheel off floor",
        4: "Left wheel stuck",
        5: "Right wheel stuck",
        6: "Stuck near a cliff",
        7: "Left wheel error",
        8: "Bin error",
        9: "Bumper stuck",
        10: "Right wheel error",
        11: "Bin error",
        12: "Cliff sensor issue",
        13: "Both wheels off floor",
        14: "Bin missing",
        15: "Reboot required",
        16: "Bumped unexpectedly",
        17: "Path blocked",
        18: "Docking issue",
        19: "Undocking issue",
        20: "Docking issue",
        21: "Navigation problem",
        22: "Navigation problem",
        23: "Battery issue",
        24: "Navigation problem",
        25: "Reboot required",
        26: "Vacuum problem",
        27: "Vacuum problem",
        29: "Software update needed",
        30: "Vacuum problem",
        31: "Reboot required",
        32: "Smart map problem",
        33: "Path blocked",
        34: "Reboot required",
        35: "Unrecognised cleaning pad",
        36: "Bin full",
        37: "Tank needed refilling",
        38: "Vacuum problem",
        39: "Reboot required",
        40: "Navigation problem",
        41: "Timed out",
        42: "Localization problem",
        43: "Navigation problem",
        44: "Pump issue",
        45: "Lid open",
        46: "Low battery",
        47: "Reboot required",
        48: "Path blocked",
        52: "Pad required attention",
        53: "Software update required",
        65: "Hardware problem detected",
        66: "Low memory",
        68: "Hardware problem detected",
        73: "Pad type changed",
        74: "Max area reached",
        75: "Navigation problem",
        76: "Hardware problem detected",
        88: "Back-up refused",
        89: "Mission runtime too long",
        101: "Battery isn't connected",
        102: "Charging error",
        103: "Charging error",
        104: "No charge current",
        105: "Charging current too low",
        106: "Battery too warm",
        107: "Battery temperature incorrect",
        108: "Battery communication failure",
        109: "Battery error",
        110: "Battery cell imbalance",
        111: "Battery communication failure",
        112: "Invalid charging load",
        114: "Internal battery failure",
        115: "Cell failure during charging",
        116: "Charging error of Home Base",
        118: "Battery communication failure",
        119: "Charging timeout",
        120: "Battery not initialized",
        122: "Charging system error",
        123: "Battery not initialized",
        216: "Charging base bag full",
    }

    def __init__(self, address=None, blid=None, password=None, topic="#",
                       roombaName="", file="./config.ini", log=None, webport=None):
        '''
        address is the IP address of the Roomba,
        leave topic as is, unless debugging (# = all messages).
        if a python standard logging object called 'Roomba' exists,
        it will be used for logging,
        or pass a logging object
        '''
        self.loop = asyncio.get_event_loop()
        self.debug = False
        if log:
            self.log = log
        else:
            self.log = logging.getLogger("Roomba.{}".format(roombaName if roombaName else __name__))
        if self.log.getEffectiveLevel() == logging.DEBUG:
            self.debug = True
        self.address = address
        # set the following to True to enable pretty printing of json data
        self.pretty_print = False
        self.roomba_port = 8883
        self.blid = blid
        self.password = password
        self.roombaName = roombaName
        self.file = file
        self.get_passwd = Password(file=file)
        self.topic = topic
        self.webport = webport
        self.ws = None
        self.args = None    #shadow class variable
        self.mqttc = None
        self.local_mqtt = False
        self.exclude = ""
        self.roomba_connected = False
        self.indent = 0
        self.master_indent = 0
        self.raw = False
        self.drawmap = False
        self.mapSize = None
        self.roomba_angle = 0
        self.old_x_y = None
        self.fnt = None
        self.home_pos = None
        self.angle = 0
        self.invert_x = self.invert_y = None    #mirror x,y
        self.current_state = None
        self.simulation = False
        self.simulation_reset = False
        self.max_distance = 500             #max distance to draw lines
        self.icons = icons(base_icon=None, angle=self.angle, fnt=self.fnt, size=(32,32), log=self.log)
        self.base = None                    #base map
        self.room_outline_contour = None
        self.room_outline = None
        self.floorplan = None
        self.floorplan_size = None
        self.previous_display_text = self.display_text = None
        self.master_state = {}
        self.update_seconds = 300           #update with all values every 5 minutes
        self.show_final_map = True
        self.client = None                  #Roomba MQTT client
        self.roombas_config = {}            #Roomba configuration loaded from config file
        self.history = {}
        self.timers = {}
        self.flags = {}
        self.max_sqft = None
        self.cb = None
        
        self.is_connected = asyncio.Event()
        self.q = asyncio.Queue()
        self.command_q = asyncio.Queue()            
        self.loop.create_task(self.process_q())
        self.loop.create_task(self.process_command_q())
        self.update = self.loop.create_task(self.periodic_update())

        if not all([self.address, self.blid, self.password]):
            if not self.configure_roomba():
                self.log.critical('Could not configure Roomba')
        else:
            self.roombas_config = {self.address: {
                                   "blid": self.blid,
                                   "password": self.password,
                                   "roomba_name": self.roombaName}}
                                   
        if self.webport:
            self.setup_webserver()
            
    def setup_webserver(self):
        from web_server import webserver
        self.ws = webserver(roomba=self, webport=self.webport)
                                   
    async def event_wait(self, evt, timeout):
        '''
        Event.wait() with timeout
        '''
        try:
            await asyncio.wait_for(evt.wait(), timeout)
        except asyncio.TimeoutError:
            pass
        return evt.is_set()

    def configure_roomba(self):
        self.log.info('configuring Roomba from file {}'.format(self.file))
        self.roombas_config = self.get_passwd.get_roombas()
        for ip, roomba in self.roombas_config.items():
            if any([self.address==ip, self.blid==roomba['blid'], roomba['roomba_name']==self.roombaName]):
                self.roombaName = roomba['roomba_name']
                self.address = ip
                self.blid = roomba['blid']
                self.password = roomba['password']
                self.max_sqft = roomba.get('max_sqft', 0)
                self.webport = roomba.get('webport', self.webport)
                return True        
        
        self.log.warning('No Roomba specified, or found, exiting')
        return False

    def setup_client(self):
        if self.client is None:
            if not HAVE_MQTT:
                print("Please install paho-mqtt 'pip install paho-mqtt' "
                      "to use this library")
                return False
            self.client = mqtt.Client(
                client_id=self.blid, clean_session=True,
                protocol=mqtt.MQTTv311)
            # Assign event callbacks
            self.client.on_message = self.on_message
            self.client.on_connect = self.on_connect
            self.client.on_publish = self.on_publish
            self.client.on_subscribe = self.on_subscribe
            self.client.on_disconnect = self.on_disconnect

            # Uncomment to enable debug messages
            #self.client.on_log = self.on_log

            self.log.info("Setting TLS")
            try:
                #self.client._ssl_context = None
                context = ssl.SSLContext()
                # Either of the following context settings works - choose one
                # Needed for 980 and earlier robots as their security level is 1.
                # context.set_ciphers('HIGH:!DH:!aNULL')
                context.set_ciphers('DEFAULT@SECLEVEL=1')
                self.client.tls_set_context(context)
            except Exception as e:
                self.log.exception("Error setting TLS: {}".format(e))

            # disables peer verification
            self.client.tls_insecure_set(True)
            self.client.username_pw_set(self.blid, self.password)
            self.log.info("Setting TLS - OK")
            return True
        return False

    def connect(self):
        '''
        just create async_connect task
        '''
        return self.loop.create_task(self.async_connect())

    async def async_connect(self):
        '''
        Connect to Roomba MQTT server
        '''
        if not all([self.address, self.blid, self.password]):
            self.log.critical("Invalid address, blid, or password! All these "
                              "must be specified!")
            return False
        count = 0
        max_retries = 3
        retry_timeout = 1
        while not self.roomba_connected:
            try:
                if self.client is None:
                    self.log.info("Connecting...")
                    self.setup_client()
                    await self.loop.run_in_executor(None, self.client.connect, self.address, self.roomba_port, 60)
                else:
                    self.log.info("Attempting to Reconnect...")
                    self.client.loop_stop()
                    await self.loop.run_in_executor(None, self.client.reconnect)
                self.client.loop_start()
                await self.event_wait(self.is_connected, 1)    #wait for MQTT on_connect to fire (timeout 1 second)
            except (ConnectionRefusedError, OSError) as e:
                if e.errno == 111:      #errno.ECONNREFUSED
                    self.log.error('Unable to Connect to roomba {}, make sure nothing else is connected (app?), '
                                   'as only one connection at a time is allowed'.format(self.roombaName))
                elif e.errno == 113:    #errno.No Route to Host
                    self.log.error('Unable to contact roomba {} on ip {}'.format(self.roombaName, self.address))
                else:
                    self.log.error("Connection Error: {} ".format(e))
                
                await asyncio.sleep(retry_timeout)
                self.log.error("Attempting retry Connection# {}".format(count))
                
                count += 1
                if count >= max_retries:
                    retry_timeout = 60
                    
            except asyncio.CancelledError:
                self.log.error('Connection Cancelled')
                break
            except Exception as e:
                #self.log.error("Error: {} ".format(e))
                self.log.exception(e)
                if count >= max_retries:
                    break
            
        if not self.roomba_connected:   
            self.log.error("Unable to connect to {}".format(self.roombaName))
        return self.roomba_connected

    def disconnect(self):
        try:
            self.loop.run_until_complete(self._disconnect())
        except RuntimeError:
            self.loop.create_task(self._disconnect())
    
    async def _disconnect(self):
        #if self.ws:
        #    await self.ws.cancel()
        tasks = [t for t in asyncio.Task.all_tasks() if t is not asyncio.Task.current_task()]
        [task.cancel() for task in tasks]
        self.log.info("Cancelling {} outstanding tasks".format(len(tasks)))
        await asyncio.gather(*tasks, return_exceptions=True)
        self.client.disconnect()
        if self.local_mqtt:
            self.mqttc.loop_stop()
        self.log.info('{} disconnected'.format(self.roombaName))
        
    def connected(self, state):
        self.roomba_connected = state
        self.publish('status', 'Online' if self.roomba_connected else 'Offline at {}'.format(time.ctime()))
        
    def on_connect(self, client, userdata, flags, rc):
        self.log.info("Roomba Connected")
        if rc == 0:
            self.connected(True)
            self.client.subscribe(self.topic)
            self.client.subscribe("$SYS/#")
        else:
            self.log.error("Connected with result code {}".format(str(rc)))
            self.log.error("Please make sure your blid and password are "
                           "correct for Roomba {}".format(self.roombaName))
            self.connected(False)
            self.client.disconnect()
        self.loop.call_soon_threadsafe(self.is_connected.set)

    def on_message(self, mosq, obj, msg):
        #print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
        if self.exclude != "" and self.exclude in msg.topic:
            return
            
        if self.indent == 0:
            self.master_indent = max(self.master_indent, len(msg.topic))
            
        if not self.simulation:
            asyncio.run_coroutine_threadsafe(self.q.put(msg), self.loop)
            
    async def process_q(self):
        '''
        Main processing loop, run until program exit
        '''
        while True:
            try:
                if self.q.qsize() > 0:
                    self.log.warning('Pending event queue size is: {}'.format(self.q.qsize()))
                msg = await self.q.get()
                
                if not self.command_q.empty():
                    self.log.info('Command waiting in queue')
                    await asyncio.sleep(1)
                    
                log_string, json_data = self.decode_payload(msg.topic,msg.payload)
                self.dict_merge(self.master_state, json_data)

                if self.pretty_print:
                    self.log.info("%-{:d}s : %s".format(self.master_indent) % (msg.topic, log_string))
                else:
                    self.log.info("Received Roomba Data: {}, {}".format(str(msg.topic), str(msg.payload)))

                if self.raw:
                    self.publish(msg.topic, msg.payload)
                else:
                    await self.loop.run_in_executor(None, self.decode_topics, json_data)
                    
                self.q.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log.exception(e)

    async def periodic_update(self):
        '''
        publish status peridically
        '''
        while True:
            # default every 5 minutes
            await asyncio.sleep(self.update_seconds)
            if self.roomba_connected:
                self.log.info("Publishing master_state")
                await self.loop.run_in_executor(None, self.decode_topics, self.master_state)

    def on_publish(self, mosq, obj, mid):
        pass

    def on_subscribe(self, mosq, obj, mid, granted_qos):
        self.log.debug("Subscribed: {} {}".format(str(mid), str(granted_qos)))

    def on_disconnect(self, mosq, obj, rc):
        self.loop.call_soon_threadsafe(self.is_connected.clear)
        self.connected(False)
        if rc != 0:
            self.log.warning("Unexpected Disconnect! - reconnecting")
        else:
            self.log.info("Disconnected")

    def on_log(self, mosq, obj, level, string):
        self.log.info(string)

    def set_mqtt_client(self, mqttc=None, brokerFeedback='/roomba/feedback'):
        self.mqttc = mqttc
        if self.mqttc is not None:
            self.brokerFeedback = self.set_mqtt_topic(brokerFeedback)
                
    def set_mqtt_topic(self, topic, subscribe=False):
        if self.roombaName:
            topic = '{}/{}{}'.format(topic, self.roombaName, '/#' if subscribe else '')
        return topic
                                     
    def setup_mqtt_client(self, broker=None,
                                port=1883,
                                user=None,
                                passwd=None,
                                brokerFeedback='/roomba/feedback',
                                brokerCommand='/roomba/command',
                                brokerSetting='/roomba/setting'):
        #returns an awaitable future
                                
        return self.loop.run_in_executor(None, self._setup_mqtt_client, broker,
                                               port, user, passwd,
                                               brokerFeedback, brokerCommand,
                                               brokerSetting)
            
    def _setup_mqtt_client(self, broker=None,
                                 port=1883,
                                 user=None,
                                 passwd=None,
                                 brokerFeedback='/roomba/feedback',
                                 brokerCommand='/roomba/command',
                                 brokerSetting='/roomba/setting'):
        '''
        setup local mqtt connection to broker for feedback,
        commands and settings
        '''
        try:
            # connect to broker
            self.mqttc = mqtt.Client()
            # Assign event callbacks
            self.mqttc.on_message = self.broker_on_message
            self.mqttc.on_connect = self.broker_on_connect
            self.mqttc.on_disconnect = self.broker_on_disconnect
            if user and passwd:
                self.mqttc.username_pw_set(user, passwd)
            self.mqttc.connect(broker, port, 60)
            self.brokerFeedback = self.set_mqtt_topic(brokerFeedback)
            self.brokerCommand = self.set_mqtt_topic(brokerCommand, True)
            self.brokerSetting = self.set_mqtt_topic(brokerSetting, True)
            self.mqttc.loop_start()
            self.local_mqtt = True
        except socket.error:
            self.log.error("Unable to connect to MQTT Broker")
            self.mqttc = None
        return self.mqttc
        
    def broker_on_connect(self, client, userdata, flags, rc):
        self.log.debug("Broker Connected with result code " + str(rc))
        #subscribe to roomba commands and settings messages
        if rc == 0:
            client.subscribe(self.brokerCommand)
            client.subscribe(self.brokerSetting)
            client.subscribe(self.brokerCommand.replace('command','simulate'))
            client.subscribe(self.brokerCommand.replace('command','json'))
            self.log.info('subscribed to {}, {}'.format(self.brokerCommand, self.brokerSetting))

    def broker_on_message(self, mosq, obj, msg):
        # receive commands and settings from broker
        payload = msg.payload.decode("utf-8")
        if "command" in msg.topic:
            self.log.info("Received COMMAND: {}".format(payload))
            self.send_command(payload)
        elif "setting" in msg.topic:
            self.log.info("Received SETTING: {}".format(payload))
            cmd = str(payload).split()
            self.set_preference(cmd[0], cmd[1])
        elif "json" in msg.topic:
            self.log.info("Received JSON: {}".format(payload))
            try:
                topic = msg.topic.split("/")[-1]
                topic = topic if topic != self.roombaName else "delta"
                cmd = json.dumps(json.loads(payload))
                self.client.publish(topic, cmd)
                self.log.info("Published to Roomba topic: {} json: {}".format(topic, cmd)) 
            except Exception as e:
                self.log.error("Error in json: {}".format(e))
        elif 'simulate' in msg.topic:
            self.log.info('received simulate command: {}'.format(payload))
            self.set_simulate(True)
            asyncio.run_coroutine_threadsafe(self.q.put(msg), self.loop)
        else:
            self.log.warn("Unknown topic: {}".format(str(msg.topic)))
            
    def set_simulate(self, value=False):
        if self.simulation != value:
            self.log.info('Set simulation to: {}'.format(value))
        self.simulation = value
        if self.simulation_reset:
            self.simulation_reset.cancel()    
        if value:
            self.simulation_reset = self.loop.call_later(10, self.set_simulate)  #reset simulation in 10s

    def broker_on_disconnect(self, mosq, obj, rc):
        self.log.debug("Broker disconnected")
        
    async def async_send_command(self, command):
        await self.command_q.put({'command':command})
        
    async def async_set_preference(self, preference, setting):
        await self.command_q.put({'setting':(preference, setting)})
        
    async def async_set_cleanSchedule(self, setting):
        await self.command_q.put({'schedule':setting})
                    
    def send_command(self, command):
        asyncio.run_coroutine_threadsafe(self.command_q.put({'command':command}), self.loop)
        
    def set_preference(self, preference, setting):
        asyncio.run_coroutine_threadsafe(self.command_q.put({'setting':(preference, setting)}), self.loop)
        
    def set_cleanSchedule(self, setting):
        asyncio.run_coroutine_threadsafe(self.command_q.put({'schedule':setting}), self.loop)
                    
    async def process_command_q(self):
        '''
        Command processing loop, run until program exit
        '''
        while True:
            value = await self.command_q.get()
            command = value.get('command')
            setting = value.get('setting')
            schedule = value.get('schedule')
            if command:
                await self.loop.run_in_executor(None, self._send_command, command)
            if setting:
                await self.loop.run_in_executor(None, self._set_preference, *setting)
            if schedule:
                await self.loop.run_in_executor(None, self._set_cleanSchedule, schedule)
            self.command_q.task_done()

    def _send_command(self, command):
        '''
        eg
        {"command": "reset", "initiator": "admin", "time": 1609950197}
        {"command": "find", "initiator": "rmtApp", "time": 1612462418, "robot_id": null, "select_all": null}}}}'
        '''
        self.log.info("Processing COMMAND: {}".format(command))
        if isinstance(command, dict):
            Command = command
        else:
            Command = {}
            try:
                Command = json.loads(command) #was command, object_pairs_hook=OrderedDict
            except json.decoder.JSONDecodeError:
                Command["command"] = command
        Command["time"] = self.totimestamp(datetime.datetime.now())
        Command["initiator"] = "localApp"
        myCommand = json.dumps(Command)
        self.log.info("Sending Command: {}".format(myCommand))
        self.client.publish("cmd", myCommand)
        
    def send_region_command(self, command):
        '''
        send region specific start command
        example command:
        "cmd": {
                    "command": "start",
                    "ordered": 1,
                    "pmap_id": "wpVy73n9R5GrVYtEPZJ5iA",
                    "regions": [
                        {
                            "region_id": "6",
                            "type": "rid"
                        }
                    ],
                    "user_pmapv_id": "201227T172634"
                }
        command is json string, or dictionary.
        need 'regions' defined, or else whole map will be cleaned.
        if 'pmap_id' is not specified, the first pmap_id found in roombas list is used.
        '''
        pmaps = self.get_property('pmaps')
        self.log.info('pmaps: {}'.format(pmaps))
        myCommand = {}
        if not isinstance(command, dict):
            command = json.loads(command)
            
        myCommand['command'] = command.get('command', 'start')
        myCommand['ordered'] = 1
        pmap_id = command.get('pmap_id')
        user_pmap_id = command.get('user_pmapv_id')
        
        if pmaps:
            found = False
            for pmap in pmaps:
                for k, v in pmap.items():
                    if pmap_id:
                        if k == pmap_id:
                            user_pmap_id = v
                            found = True
                            break
                    else:
                        pmap_id = k
                        user_pmap_id = v
                        found = True
                        break
                if found:
                    break
                    
        myCommand['pmap_id'] = pmap_id
        for region in command.get('regions', []):
            myCommand.setdefault('regions', [])
            if not isinstance(region, dict) and str(region).isdigit():
                region = {'region_id': str(region), 'type': 'rid'}
            if isinstance(region, dict):
                myCommand['regions'].append(region)
        myCommand['user_pmapv_id'] = user_pmap_id
        
        self._send_command(myCommand)

    def _set_preference(self, preference, setting):
        self.log.info("Received SETTING: {}, {}".format(preference, setting))
        if isinstance(setting, bool):
            val = setting
        elif setting.lower() == "true":
            val = True
        else:
            val = False
        Command = {"state": {preference: val}}
        myCommand = json.dumps(Command)
        self.log.info("Publishing Roomba {} Setting :{}".format(self.roombaName, myCommand))
        self.client.publish("delta", myCommand)
    
    def _set_cleanSchedule(self, setting):
        self.log.info("Received Roomba {} cleanSchedule:".format(self.roombaName))
        sched = "cleanSchedule"
        if self.is_setting("cleanSchedule2"):
            sched = "cleanSchedule2"
        Command = {"state": {sched: setting}}
        myCommand = json.dumps(Command)
        self.log.info("Publishing Roomba {} {} : {}".format(self.roombaName, sched, myCommand))
        self.client.publish("delta", myCommand)
    
    def publish(self, topic, message):
        if self.mqttc is not None and message is not None:
            topic = '{}/{}'.format(self.brokerFeedback, topic)
            self.log.debug("Publishing item: {}: {}".format(topic, message))
            self.mqttc.publish(topic, message)
            
    def set_callback(self, cb=None):
        self.cb = cb
        
    def get_colour(self, colour, default=(64,64,64,255)):
        try:
            if isinstance(colour, str):
                colour = ImageColor.getcolor(colour, 'RGBA')
            elif isinstance(colour, int):
                colour = (colour, colour, colour, 255)
            elif len(colour) == 1:
                colour = (colour[0],colour[0],colour[0],255)
            elif len(colour) == 3:
                colour += (255,)
        except ValueError as e:
            self.log.error('MAP: {}'.format(e))
            colour = default
        return colour
            
    def set_options(self, raw=False, indent=0, pretty_print=False, max_sqft=0):
        self.raw = raw
        self.indent = indent
        self.pretty_print = pretty_print
        self.max_sqft = int(max_sqft)
        if self.raw:
            self.log.info("Posting RAW data")
        else:
            self.log.info("Posting DECODED data")
                                        
    def enable_map(self, enable=False, mapSize="(800,1500,0,0,0,0)",
                   mapPath=".", iconPath = "./", roomOutline=True,
                   enableMapWithText=True,
                   fillColor="lawngreen", 
                   outlineColor=(64,64,64,255),
                   outlineWidth=1,
                   home_icon_file="home.png",
                   roomba_icon_file="roomba.png",
                   roomba_error_file="roombaerror.png",
                   roomba_cancelled_file="roombacancelled.png",
                   roomba_battery_file="roomba-charge.png",
                   bin_full_file="binfull.png",
                   tank_low_file="tanklow.png",
                   floorplan = None,
                   roomba_size=(50,50), draw_edges = 30, auto_rotate=False):
        #returns an awaitable future
        
        return self.loop.run_in_executor(None,  self._enable_map, enable,
                                                mapSize, mapPath, iconPath, roomOutline,
                                                enableMapWithText, fillColor, outlineColor, outlineWidth,
                                                home_icon_file, roomba_icon_file, roomba_error_file,
                                                roomba_cancelled_file, roomba_battery_file,
                                                bin_full_file, tank_low_file, floorplan, roomba_size, draw_edges,
                                                auto_rotate)

    def _enable_map(self, enable=False, mapSize="(800,1500,0,0,0,0)",
                   mapPath=".", iconPath = "./", roomOutline=True,
                   enableMapWithText=True,
                   fillColor="lawngreen", 
                   outlineColor=(64,64,64,255),
                   outlineWidth=1,
                   home_icon_file="home.png",
                   roomba_icon_file="roomba.png",
                   roomba_error_file="roombaerror.png",
                   roomba_cancelled_file="roombacancelled.png",
                   roomba_battery_file="roomba-charge.png",
                   bin_full_file="binfull.png",
                   tank_low_file="tanklow.png",
                   floorplan = None,
                   roomba_size=(50,50), draw_edges = 30, auto_rotate=False):
        '''
        Enable live map drawing. mapSize is x,y size, x,y offset of docking
        station ((0,0) is the center of the image) final value is map rotation
        (in case map is not straight up/down). These values depend on the
        size/shape of the area Roomba covers. Offset depends on where you place
        the docking station. This will need some experimentation to get right.
        You can supply 32x32 icons for dock and roomba etc. If the files don't
        exist, crude representations are made. If you specify home_icon_file as
        None, then no dock is drawn. Draw edges attempts to draw straight lines
        around the final (not live) map, and Auto_rotate (on/off) attempts to
        line the map up vertically. These only work if you have openCV
        installed. otherwise a PIL version is used, which is not as good (but
        less CPU intensive). roomOutline enables the previous largest saved
        outline to be overlayed on the map (so you can see where cleaning was
        missed). This is on by default, but the alignment doesn't work so well,
        so you can turn it off.
        Returns map enabled True/False
        '''
        if not HAVE_PIL: #can't draw a map without PIL!
            return False

        if Image.__version__ < "4.1.1":
            print("WARNING: PIL version is %s, this is not the latest! you "
                  "can get bad memory leaks with old versions of PIL"
                  % Image.__version__)
            print("run: 'pip install --upgrade pillow' to fix this")
        
        if enable:
            self.log.info("MAP: Maps Enabled")
            if isinstance(mapSize, str):
                mapSize = literal_eval(mapSize)
            self.mapSize = mapSize
            if len(self.mapSize) < 6:
                self.log.error("mapSize is required, and is of the form "
                               "(800,1500,0,0,0,0) - (x,y size, x,y dock loc,"
                               "theta1, theta2), map,roomba roatation")
                self.drawmap = False
                return False
            if self.roombas_config.get(self.address):
                self.roombas_config[self.address]['mapsize'] = self.mapSize
            self.angle = self.mapSize[4]
            self.roomba_angle = self.mapSize[5]
            if len(self.mapSize) >=7:
                self.invert_x = self.mapSize[6]
            if len(self.mapSize) >=8:
                self.invert_y = self.mapSize[7]
            self.mapPath = mapPath
            # get a font
            if self.fnt is None:
                try:
                    self.fnt = ImageFont.truetype('FreeMono.ttf', 40)
                except IOError as e:
                    self.log.warning("error loading font: %s, loading default font".format(e))
                    self.fnt = ImageFont.load_default()
            #load icons
            self.icons.set_font(self.fnt)
            self.icons.set_angle(self.angle)

            self.icons.load_icon_file('roomba', os.path.join(iconPath, roomba_icon_file), roomba_size)
            self.icons.load_icon_file('stuck', os.path.join(iconPath, roomba_error_file), roomba_size)
            self.icons.load_icon_file('cancelled', os.path.join(iconPath, roomba_cancelled_file), roomba_size)
            self.icons.load_icon_file('battery', os.path.join(iconPath, roomba_battery_file), roomba_size)
            self.icons.load_icon_file('bin full', os.path.join(iconPath, bin_full_file), roomba_size)
            self.icons.load_icon_file('tank low', os.path.join(iconPath, tank_low_file), roomba_size)
            if home_icon_file is not None:
                self.icons.load_icon_file('home', os.path.join(iconPath, home_icon_file), (32,32))  #make home base size adjustable?
            self.draw_edges = draw_edges // 10000
            self.auto_rotate = auto_rotate
            if not roomOutline:
                self.log.info("MAP: Not drawing Room Outline")
            self.roomOutline = roomOutline

            self.enableMapWithText = enableMapWithText
            self.fillColor = self.get_colour(fillColor, default=(124, 252, 0, 255))
            self.outlineColor = self.get_colour(outlineColor)
            self.outlineWidth = outlineWidth
            self.initialise_map(roomba_size)
            if floorplan:
                if isinstance(floorplan, str):
                    floorplan = literal_eval(floorplan)
                if floorplan and len(floorplan) != 6:
                    self.log.error('floorplan is of the form '
                                   '("res/first_floor.jpg",0,0,1.0,0) - (filename, x, y, scale, roatation, transparency)')
                else:
                    self.floorplan_size = floorplan
                    self.load_floorplan(floorplan[0], new_center=(floorplan[1], floorplan[2]), scale=floorplan[3], angle=floorplan[4], transparency=floorplan[5])
            self.drawmap = enable
            return True
        return False  
            
    def load_floorplan(self, filename, new_center=(0,0), scale=None, angle=0, transparency=0.2):
        if self.base is not None:
            self.log.info('MAP: loading floorplan: {}'.format(filename))
            try:
                floorplan_tmp = Image.open(filename).convert('L')
                floorplan_tmp = floorplan_tmp.rotate(angle, resample=Image.BICUBIC, expand=True, translate=new_center, fillcolor=255)
                if scale is not None:
                    if isinstance(scale, (float, int)):
                        scale=(float(scale), float(scale))
                    new_size = (int(floorplan_tmp.size[0]*scale[0]), int(floorplan_tmp.size[1]*scale[1]))
                    floorplan_tmp = floorplan_tmp.resize(new_size)
                floorplan_tmp.crop((0, 0 , self.base.size[0], self.base.size[1]))
                floorplan_tmp = self.transparent_paste(self.make_blank_image(), floorplan_tmp)
                floorplan_tmp.putalpha(int(transparency*255))
                if self.roombaName.lower() == 'upstairs':
                    floorplan_tmp.save('test_floorplan.png')
                self.floorplan = floorplan_tmp
                self.log.info('loaded floorplan: {}'.format(filename))
            except Exception as e:
                self.log.warning("MAP: unable to load {}: {}".format(filename,e))     

    def totimestamp(self, dt):
        td = dt - datetime.datetime(1970, 1, 1)
        return int(td.total_seconds())

    def dict_merge(self, dct, merge_dct):
        '''
        Recursive dict merge. Inspired by :meth:``dict.update()``, instead
        of updating only top-level keys, dict_merge recurses down into dicts
        nested to an arbitrary depth, updating keys. The ``merge_dct`` is
        merged into ``dct``.
        :param dct: dict onto which the merge is executed
        :param merge_dct: dct merged into dct
        :return: None
        '''
        for k, v in merge_dct.items():
            if (k in dct and isinstance(dct[k], dict)
                    and isinstance(merge_dct[k], Mapping)):
                self.dict_merge(dct[k], merge_dct[k])
            else:
                dct[k] = merge_dct[k]
                
    def recursive_lookup(self, search_dict, key, cap=False):
        '''
        recursive dictionary lookup
        if cap is true, return key if it's in the 'cap' dictionary,
        else return the actual key value
        '''
        for k, v in search_dict.items():
            if cap:
                if k == 'cap':
                    return self.recursive_lookup(v, key, False)
            elif k == key:
                return v 
            elif isinstance(v, dict) and k != 'cap':
                val = self.recursive_lookup(v, key, cap)
                if val is not None:
                    return val
        return None
        
    def is_setting(self, setting, search_dict=None):
        if search_dict is None:
            search_dict = self.master_state
        for k, v in search_dict.items():
            if k == setting:
                return True
            if isinstance(v, dict):
                if self.is_setting(setting, v):
                    return True
        return False

    def decode_payload(self, topic, payload):
        '''
        Format json for pretty printing, return string suitable for logging,
        and a dict of the json data
        '''
        indent = self.master_indent + 31 #number of spaces to indent json data

        try:
            # if it's json data, decode it (use OrderedDict to preserve keys
            # order), else return as is...
            json_data = json.loads(
                payload.decode("utf-8").replace(":nan", ":NaN").\
                replace(":inf", ":Infinity").replace(":-inf", ":-Infinity"))  #removed object_pairs_hook=OrderedDict
            # if it's not a dictionary, probably just a number
            if not isinstance(json_data, dict):
                return json_data, dict(json_data)
            json_data_string = "\n".join((indent * " ") + i for i in \
                (json.dumps(json_data, indent = 2)).splitlines())

            formatted_data = "Decoded JSON: \n%s" % (json_data_string)

        except ValueError:
            formatted_data = payload

        if self.raw:
            formatted_data = payload

        return formatted_data, dict(json_data)

    def decode_topics(self, state, prefix=None):
        '''
        decode json data dict, and publish as individual topics to
        brokerFeedback/topic the keys are concatenated with _ to make one unique
        topic name strings are expressly converted to strings to avoid unicode
        representations
        '''
        for k, v in state.items():
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
                            for ki, vi in i.items():
                                newlist.append((str(ki), vi))
                        else:
                            if not isinstance(i, str):
                                i = str(i)
                            newlist.append(i)
                    v = newlist
                if prefix is not None:
                    k = prefix+"_"+k
                # all data starts with this, so it's redundant
                k = k.replace("state_reported_","")
                    
                self.publish(k, str(v))

        if prefix is None:
            self.update_state_machine()
            
    async def get_settings(self, items):
        result = {}
        if not isinstance(items, list):
            items = [items]
        for item in items:
            value = await self.loop.run_in_executor(None, self.get_property, item)
            result[item] = value
        return result
        
    def get_error_message(self, error_num):
        try:
            error_message = self._ErrorMessages[error_num]
        except KeyError as e:
            self.log.warning(
                "Error looking up error message {}".format(e))
            error_message = "Unknown Error number: {}".format(error_num)
        return error_message
        
    def publish_error_message(self):
        self.publish("error_message", self.error_message)
            
    def get_property(self, property, cap=False):
        '''
        Only works correctly if property is a unique key
        '''
        if property in ['cleanSchedule', 'langs']:
            value = self.recursive_lookup(self.master_state, property+'2', cap)
            if value is not None:
                return value
        return self.recursive_lookup(self.master_state, property, cap)
        
    @property    
    def co_ords(self):
        co_ords = self.pose
        if isinstance(co_ords, dict):
            return {'x': -co_ords['point']['y'] if self.invert_x else co_ords['point']['y'],
                    'y': -co_ords['point']['x'] if self.invert_y else co_ords['point']['x'],
                    'theta':co_ords['theta']}
        return self.zero_coords()
        
    @property
    def error_num(self):
        try:
            return self.cleanMissionStatus.get('error')
        except AttributeError:
            pass
        return 0
        
    @property
    def error_message(self):
        return self.get_error_message(self.error_num)
        
    @property
    def cleanMissionStatus(self):
        return self.get_property("cleanMissionStatus")
        
    @property
    def pose(self):
        return self.get_property("pose")
        
    @property
    def batPct(self):
        return self.get_property("batPct")
        
            
    @property
    def bin_full(self):
        return self.get_property("bin_full")
        
    @property
    def tanklvl(self):
        return self.get_property("tankLvl")
        
    @property
    def rechrgM(self):
        return self.get_property("rechrgM")
        
    def calc_mssM(self):
        start_time = self.get_property("mssnStrtTm")
        if start_time:
            return int((datetime.datetime.now() - datetime.datetime.fromtimestamp(start_time)).total_seconds()//60)
        start = self.timers.get('start')
        if start:
            return int((time.time()-start)//60)
        return None
        
    @property
    def mssnM(self):
        mssM = self.get_property("mssnM")
        if not mssM:
            run_time = self.calc_mssM()
            return run_time if run_time else mssM
        return mssM
    
    @property
    def expireM(self):
        return self.get_property("expireM")
    
    @property
    def cap(self):
        return self.get_property("cap")
    
    @property
    def sku(self):
        return self.get_property("sku")
        
    @property
    def mission(self):
        return self.get_property("cycle")
        
    @property
    def phase(self):
        return self.get_property("phase")
        
    @property
    def cleanMissionStatus_phase(self):
        return self.phase
        
    @property
    def cleanMissionStatus(self):
        return self.get_property("cleanMissionStatus")
        
    @property
    def pmaps(self):
        return self.get_property("pmaps")
        
    @property
    def regions(self):
        return self.get_property("regions")
        
    @property
    def pcent_complete(self):
        return self.update_precent_complete()
        
    def set_flags(self, flags=None):
        self.handle_flags(flags, True)
        
    def clear_flags(self, flags=None):
        self.handle_flags(flags)
        
    def flag_set(self, flag):
        try:
            return self.master_state['state']['flags'].get(flag, False)
        except KeyError:
            pass
        return False
            
    def handle_flags(self, flags=None, set=False):
        self.master_state['state'].setdefault('flags', {})
        if isinstance(flags, str):
            flags = [flags]
        if flags:
            for flag in flags:
                if set:
                    if not self.flag_set(flag):
                        self.flags[flag] = True
                    self.master_state['state']['flags'].update(self.flags)
                else:
                    self.flags.pop(flag, None)
                    self.master_state['state']['flags'].pop(flag, None)
        else:
            self.flags = {}
            if not set:
                self.master_state['state']['flags'] = self.flags
        
    def update_precent_complete(self):
        try:
            sq_ft = self.get_property("sqft")
            if self.max_sqft and sq_ft is not None:
                percent_complete = int(sq_ft)*100//self.max_sqft
                self.publish("roomba_percent_complete", percent_complete)
                return percent_complete
        except (KeyError, TypeError):
            pass
        return None
        
    def update_history(self, property, value=None, cap=False):
        '''
        keep previous value
        '''
        if value is not None:
            current = value
        else:
            current = self.get_property(property, cap)
        if isinstance(current, dict):
            current = current.copy()
        previous = self.history.get(property, {}).get('current')
        if previous is None:
            previous = current
        self.history[property] = {'current' : current,
                                  'previous': previous}
        return current
        
    def set_history(self, property, value=None):
        if isinstance(value, dict):
            value = value.copy()
        self.history[property] = {'current' : value,
                                  'previous': value}
        
    def current(self, property):
        return self.history.get(property, {}).get('current')
        
    def previous(self, property):
        return self.history.get(property, {}).get('previous')
        
    def changed(self, property):
        changed = self.history.get(property, {}).get('current') != self.history.get(property, {}).get('previous')
        return changed
    
    def is_set(self, name):
        return self.timers.get(name, {}).get('value', False)
        
    def when_run(self, name):
        th = self.timers.get(name, {}).get('reset', None)
        if th:
            return max(0, int(th._when - self.loop.time()))
        return 0
    
    def timer(self, name, value=False, duration=10):
        self.timers.setdefault(name, {})
        self.timers[name]['value'] = value
        self.log.info('Set {} to: {}'.format(name, value))
        if self.timers[name].get('reset'):
            self.timers[name]['reset'].cancel()    
        if value:
            self.timers[name]['reset'] = self.loop.call_later(duration, self.timer, name)  #reset reset timer in duration seconds
            
    def roomba_type(self, type):
        '''
        returns True or False if the first letter of the sku is in type (a list)
        valid letters are:
        r   900 series
        e   e series
        i   i series
        s   s series
        '''
        if not isinstance(type, list):
            type = [type]
        if isinstance(self.sku, str):
            return self.sku[0].lower() in type
        return None
            
    def update_state_machine(self, new_state = None):
        '''
        Roomba progresses through states (phases), current identified states
        are:
        ""              : program started up, no state yet
        "run"           : running on a Cleaning Mission
        "hmUsrDock"     : returning to Dock
        "hmMidMsn"      : need to recharge
        "hmPostMsn"     : mission completed
        "charge"        : charging
        "stuck"         : Roomba is stuck
        "stop"          : Stopped
        "pause"         : paused
        "evac"          : emptying bin
        "chargingerror" : charging base is unplugged

        available states:
        states = {"charge"          : "Charging",
                  "new"             : "New Mission",
                  "run"             : "Running",
                  "resume"          : "Running",
                  "hmMidMsn"        : "Docking",
                  "recharge"        : "Recharging",
                  "stuck"           : "Stuck",
                  "hmUsrDock"       : "User Docking",
                  "completed"       : "Mission Completed",
                  "cancelled"       : "Cancelled",
                  "stop"            : "Stopped",
                  "pause"           : "Paused",
                  "evac"            : "Emptying",
                  "hmPostMsn"       : "Docking - End Mission",
                  "chargingerror"   : "Base Unplugged",
                  ""                :  None}

        Normal Sequence is "" -> charge -> run -> hmPostMsn -> charge
        Mid mission recharge is "" -> charge -> run -> hmMidMsn -> charge
                                   -> run -> hmPostMsn -> charge
        Stuck is "" -> charge -> run -> hmPostMsn -> stuck
                    -> run/charge/stop/hmUsrDock -> charge
        Start program during run is "" -> run -> hmPostMsn -> charge
        Note: Braava M6 goes run -> hmPostMsn -> run -> charge when docking
        Note: S9+ goes run -> hmPostMsn -> charge -> run -> charge on a training mission (ie cleanMissionStatus_cycle = 'train')
        Note: The first 3 "pose" (x, y) co-ordinate in the first 10 seconds during undocking at mission start seem to be wrong
              for example, during undocking:
              {"x": 0, "y": 0},
              {"x": -49, "y": 0},
              {"x": -47, "y": 0},
              {"x": -75, "y": -11}... then suddenly becomes normal co-ordinates
              {"x": -22, "y": 131}
              {"x": -91, "y": 211}
              also during "hmPostMsn","hmMidMsn", "hmUsrDock" the co-ordinates system also seems to change to bogus values
              For example, in "run" phase, co-ordinates are reported as:
              {"x": -324, "y": 824},
              {"x": -324, "y": 826} ... etc, then some time after hmMidMsn (for example) they change to:
              {"x": 417, "y": -787}, which continues for a while
              {"x": 498, "y": -679}, and then suddenly changes back to normal co-ordinates
              {"x": -348, "y": 787},
              {"x": -161, "y": 181},
              {"x": 0, "y": 0}
              
              For now use self.distance_betwwen() to ignore large changes in position

        Need to identify a new mission to initialize map, and end of mission to
        finalise map.
        mission goes from 'none' to 'clean' (or another mission name) at start of mission (init map)
        mission goes from 'clean' (or other mission) to 'none' at end of missions (finalize map)
        Anything else = continue with existing map
        '''
        if new_state is not None:
            self.current_state = self.states[new_state]
            self.log.info("set current state to: {}".format(self.current_state))
            self.draw_map(True)
            return    
            
        self.publish_error_message()                #publish error messages
        self.update_precent_complete()
        mission = self.update_history("cycle")      #mission
        phase = self.update_history("phase")        #mission phase
        self.update_history("pose")                 #update co-ordinates
        
        if self.cb is not None:                     #call callback if set
            self.cb(self.master_state)
        
        if phase is None or mission is None:
            return
        
        current_mission = self.current_state
        
        if self.debug:
            self.timer('ignore_coordinates')
            current_mission = None  #force update of map

        self.log.info('current_state: {}, current phase: {}, mission: {}, mission_min: {}, recharge_min: {}, co-ords changed: {}'.format(self.current_state,
                                                                                                                    phase,
                                                                                                                    mission,
                                                                                                                    self.mssnM,
                                                                                                                    self.rechrgM,
                                                                                                                    self.changed('pose')))

        if phase == "charge":
            #self.set_history('pose', self.zero_pose())
            current_mission = None
            
        if self.current_state == self.states["new"] and phase != 'run':
            self.log.info('waiting for run state for New Missions')
            if time.time() - self.timers['start'] >= 20:
                self.log.warning('Timeout waiting for run state')
                self.current_state = self.states[phase]

        elif phase == "run" and (self.is_set('ignore_run') or mission == 'none'):
            self.log.info('Ignoring bogus run state')
            
        elif phase == "charge" and mission == 'none' and self.is_set('ignore_run'):
            self.log.info('Ignoring bogus charge/mission state')
            self.update_history("cycle", self.previous('cycle'))
            
        elif phase in ["hmPostMsn","hmMidMsn", "hmUsrDock"]:
            self.timer('ignore_run', True, 10)
            self.current_state = self.states[phase]
            
        elif self.changed('cycle'): #if mission has changed
            if mission != 'none':
                self.current_state = self.states["new"]
                self.timers['start'] = time.time()
                if isinstance(self.sku, str) and self.sku[0].lower() in ['i', 's', 'm']:
                    #self.timer('ignore_coordinates', True, 30)  #ignore updates for 30 seconds at start of new mission
                    pass
            else:
                self.timers.pop('start', None)
                if self.bin_full:
                    self.current_state = self.states["cancelled"]
                else:
                    self.current_state = self.states["completed"]
                self.timer('ignore_run', True, 5)  #still get bogus 'run' states after mission complete.
            
        elif phase == "charge" and self.rechrgM:
            if self.bin_full:
                self.current_state = self.states["pause"]
            else:
                self.current_state = self.states["recharge"]
            
        else:
            try:
                self.current_state = self.states[phase]
            except KeyError:
                self.log.warning('phase: {} not found in self.states'.format(phase))

        if self.current_state != current_mission:
            self.log.info("updated state to: {}".format(self.current_state))

        self.publish("state", self.current_state)
        
        if self.is_set('ignore_coordinates') and self.current_state != self.states["new"]:
            self.log.info('Ignoring co-ordinate updates')
        else:
            self.draw_map(current_mission != self.current_state)
            
    def make_blank_image(self, x=None, y=None, colour=transparent, image=True):
        if image:
            if x is None:
                x = self.base.size[0]
            if y is None:
                y = self.base.size[1]
            return Image.new('RGBA',(x,y), colour)
        if HAVE_CV2:
            return np.array([(0,0),(0,0),(0,0),(0,0)], dtype=np.int)
        return None
        
    def clear_outline(self):
        self.room_outline = None
        self.room_outline_contour = None
        self.save_image(self.make_blank_image(), 'room.png')
        self.save_image(self.make_blank_image(image=False), 'room.npy')
        self.log.info('Erased room outline image')
            
    def load_image(self, name, make_none=False):
        self.log.info("MAP: opening existing {}".format(name))
        type = name.split('.')[-1]
        filename = '{}/{}{}'.format(self.mapPath, self.roombaName, name)
        if type == 'npy':
            try:
                image = np.load(filename)
            except IOError as e:
                self.log.warning("Unable to load {}: {}, setting "
                                 "to 0".format(filename,e))
                image = self.make_blank_image(image=False)
        else:
            try:
                image = Image.open(filename).convert('RGBA')
                if image.size != self.base.size:
                    raise IOError("Image is wrong size: {}".format(image.size))
            except IOError as e:
                if make_none:
                    self.log.warning("MAP: unable to load {}: {}: set to None".format(name, e))
                    return None
                else:
                    self.log.warning("MAP: unable to load {}: {}: "
                                     "created new image".format(name,e))
                    image = self.make_blank_image()
        return image
        
    def save_image(self, var, name='', final_name=None):
        if var is None or '.' not in name:
            self.log.warning('invalid save_image attempt')
            return
        self.log.debug("MAP: saving {}".format(final_name if final_name else name))
        type = name.split('.')[-1]
        filename = '{}/{}{}'.format(self.mapPath, self.roombaName, name)
        if type == 'npy':
            np.save(filename, var)
        else:
            var.save(filename, type.upper())
 
        if final_name:
            new_filename = '{}/{}{}'.format(self.mapPath, self.roombaName, final_name)
            # try to avoid other programs reading file while writing it,
            # rename should be atomic.
            os.rename(filename, new_filename)
        
    def load_existing_maps(self):
        self.base = self.load_image('lines.png')
        self.roomba_problem = self.load_image('problems.png')

    def initialise_map(self, roomba_size):
        '''
        Initialize all map items (base maps, overlay, icons fonts etc)
        '''
        # get base image of Roomba path
        #self.load_existing_maps()
        if self.base is None:
            self.base = self.make_blank_image(self.mapSize[0], self.mapSize[1])
            self.roomba_problem = self.make_blank_image()

            self.previous_map_no_text = None
            self.map_no_text = self.load_image('map_notext.png', True)
        # save x and y center of image, for centering of final map image
        self.cx = self.base.size[0] // 2
        self.cy = self.base.size[1] // 2

        #set dock home position
        self.home_pos = (
            self.mapSize[0] // 2 + self.mapSize[2],
            self.mapSize[1] // 2 + self.mapSize[3])
        self.log.info("MAP: home_pos: ({},{})".format(self.home_pos[0], self.home_pos[1]))
            
        self.dock_position = (
            self.home_pos[0] - self.icons['home'].size[0] // 2,
            self.home_pos[1] - self.icons['home'].size[1] // 2)

        self.log.info("MAP: Initialisation complete")

    def transparent_paste(self, base_image, icon, position=None):
        '''
        needed because PIL pasting of transparent images gives weird results
        '''
        image = self.make_blank_image()
        image.paste(icon,position)
        base_image = Image.alpha_composite(base_image, image)
        return base_image
        
    def img_to_png(self, name):
        '''
        convert name image to bytes in png format
        if name is a string (not an image variable) attempt to load it
        return blank image if image is None
        '''
        if isinstance(name, str):
            name = self.load_image(name)
        if name is None:
            name = self.make_blank_image()
        imgBytes = io.BytesIO()
        name.save(imgBytes, format='PNG')
        imgBytes.seek(0)
        return imgBytes.read()

    def zero_coords(self, theta=180):
        '''
        returns dictionary with default zero coords
        '''
        return {"x": 0, "y": 0, "theta": theta}
        
    def zero_pose(self, theta=180):
        '''
        returns dictionary with default zero coords
        '''
        return {"theta":theta,"point":{"x":0,"y":0}}

    def offset_coordinates(self, new_co_ords):
        '''
        offset coordinates according to mapSize settings, with 0,0 as center
        ''' 
        if new_co_ords is None: new_co_ords = self.zero_coords()
        x_y = (new_co_ords["x"] + self.mapSize[0] // 2 + self.mapSize[2],
               new_co_ords["y"] + self.mapSize[1] // 2 + self.mapSize[3])

        theta = int(new_co_ords["theta"] - 90 + self.roomba_angle)
        self.old_x_y = x_y  #save co-ordinates
        
        return x_y, theta%360

    def get_roomba_pos(self, x_y):
        '''
        calculate roomba position as list
        '''
        return [x_y[0] - self.icons['roomba'].size[0] // 2,
                x_y[1] - self.icons['roomba'].size[1] // 2,
                x_y[0] + self.icons['roomba'].size[0] // 2,
                x_y[1] + self.icons['roomba'].size[1] // 2]

    def draw_vacuum_lines(self, image, old_x_y, x_y, theta):
        '''
        draw lines on image from old_x_y to x_y representing vacuum coverage,
        taking into account angle theta (roomba angle).
        Do mnot draw if either co-ordinate is None
        '''
        if old_x_y is None or x_y is None or \
           x_y[0] > self.base.size[0] or x_y[1] > self.base.size[1] or \
           x_y[0] < 0 or x_y[1] < 0 or \
           old_x_y[0] > self.base.size[0] or old_x_y[1] > self.base.size[1] or \
           old_x_y[0] < 0 or old_x_y[1] < 0:
            self.log.warning('MAP: Not drawing line {}, {}: value out of range'.format(old_x_y, x_y))
            return
        if self.distance_between(x_y, old_x_y) > self.max_distance:
            self.log.warning('MAP: Not drawing line {}, {}: distance is greater than {}'.format(old_x_y, x_y, self.max_distance))
            return
        lines = ImageDraw.Draw(image)
        if x_y != old_x_y:
            self.log.info("MAP: drawing line: {}, {}".format(old_x_y, x_y))
            lines.line([old_x_y, x_y], fill=self.fillColor,
                       width=self.icons['roomba'].size[0] // 2)
        #draw circle over roomba vacuum area to give smooth edges.
        arcbox = [x_y[0]-self.icons['roomba'].size[0] // 4,
                  x_y[1]-self.icons['roomba'].size[0] // 4,
                  x_y[0]+self.icons['roomba'].size[0] // 4,
                  x_y[1]+self.icons['roomba'].size[0] // 4]
        lines.ellipse(arcbox, fill=self.fillColor)

    def draw_text(self, image, display_text, fnt, pos=(0,0),
                  colour=(0,0,255,255), rotate=False):
        #draw text - (WARNING old versions of PIL have huge memory leak here!)
        if display_text is None: return
        indent = display_text.find(':')+1
        max_len = image.size[0]//(fnt.getsize(display_text)[0]//len(display_text))
        display_text = textwrap.fill(display_text, max_len, subsequent_indent=' ' * indent)
        self.log.info("MAP: writing text: pos: {}, max_len: {}, text: {}".format(pos, max_len, display_text))
        if rotate:
            txt = self.make_blank_image(*fnt.getsize(display_text))
            text = ImageDraw.Draw(txt)
            # draw text rotated 180 degrees...
            text.text((0,0), display_text, font=fnt, fill=colour)
            image.paste(txt.rotate(180-self.angle, expand=True), pos)
        else:
            text = ImageDraw.Draw(image)
            text.text(pos, display_text, font=fnt, fill=colour)
            
    def distance_between(self, new_co_ords, old_co_ords):
        try:
            return int(math.sqrt( ((new_co_ords[0]-old_co_ords[0])**2)+((new_co_ords[1]-old_co_ords[1])**2) ))
        except Exception:
            return 0
            
    def draw_roomba(self, roomba_pos, theta):
        '''
        make a blank image for the text and Roomba overlay, initialized to
        transparent text color
        Paste various Roomba problem icons onto the problems image,
        Paste roomba icon onto roomba_sprite image
        Finally paste the dock icon over it
        add optional debug info, and return the new roomba_sprite image
        '''
        roomba_sprite = self.make_blank_image()
        self.log.info("MAP: drawing roomba: pos: {}, theta: {}".format(roomba_pos, theta))
        
        #draw roomba
        roomba_sprite = self.transparent_paste(
            roomba_sprite,
            self.icons['roomba'].rotate(theta, expand=False), roomba_pos)

        # paste dock over roomba_sprite
        roomba_sprite = self.transparent_paste(
            roomba_sprite, self.icons['home'], self.dock_position)
            
        if self.debug:
            #draw bounding box, plus overlay co-ordinates on roomba_sprite
            shape = [(10, 10), (self.base.size[0] - 20, self.base.size[1] - 20)]
            box = ImageDraw.Draw(roomba_sprite)
            box.rectangle(shape, fill=None, outline =(255,0,0,255))
            x_y = (roomba_pos[0], roomba_pos[1])
            self.draw_text(roomba_sprite, str(x_y), self.fnt, x_y, (255,0,0,255))
            self.draw_text(roomba_sprite, str(self.dock_position), self.fnt, self.dock_position, (0,0,255,255))
            
        return roomba_sprite
        
    def draw_problem_roombas(self, roomba_pos):
        '''
        Paste various Roomba problem icons onto the problems image
        '''
        if self.flags.get('stuck'):
            self.log.info("MAP: Drawing stuck Roomba")
            self.roomba_problem.paste(self.icons['stuck'],roomba_pos)
        if self.flags.get('cancelled'):
            self.log.info("MAP: Drawing cancelled Roomba")
            self.roomba_problem.paste(self.icons['cancelled'],roomba_pos)
        if self.flags.get('bin_full'):
            self.log.info("MAP: Drawing full bin")
            self.roomba_problem.paste(self.icons['bin full'],roomba_pos)
        if self.flags.get('battery_low'):
            self.log.info("MAP: Drawing low battery Roomba")
            self.roomba_problem.paste(self.icons['battery'],roomba_pos)
        if self.flags.get('tank_low'):
            self.log.info("MAP: Drawing tank low Braava")
            self.roomba_problem.paste(self.icons['tank low'],roomba_pos)

    def draw_map(self, force_redraw=False):
        '''
        Draw map of Roomba cleaning progress
        '''
        if (self.changed('pose') or self.changed('phase') or force_redraw) and self.drawmap:
            #program just started, initialize old_x_y
            if self.old_x_y is None:
                self.old_x_y, _ = self.offset_coordinates(self.co_ords)
            
            #set flags
            self.set_flags()
            if not self.bin_full:
                self.clear_flags('bin_full')
                
            if self.tanklvl is not None:
                if self.tanklvl < 100:
                    self.set_flags('tank_low')
                else:
                    self.clear_flags('tank_low')
            #make sure we have phase info
            if self.current_state is not None:
                self.render_map()
            
    def render_map(self):
        '''
        Actually draw the map
        '''
        draw_final = show_time =False
        #save self.old_x_y
        old_x_y = self.old_x_y
        #get x,y theta location note: this updates self.old_x_y with new x_y
        x_y, theta = self.offset_coordinates(self.co_ords)

        if self.show_final_map == False:
            self.log.info("MAP: received: new co-ords: {} "
                          "phase: {}, state: {}".format(self.co_ords,
                          self.phase, self.current_state))

        if  self.current_state == self.states["charge"]:
            x_y = None
            self.display_text = "Charging: Battery: {}%".format(self.batPct)
            self.clear_flags(['battery_low', 'stuck'])
            if self.is_set('update_after_completed'):
                self.log.info('not updating map/text (mission complete), resume in {}s'.format(self.when_run('update_after_completed')))
            else:
                self.save_text_and_map_on_whitebg(self.map_no_text)
            draw_final = True

        elif self.current_state == self.states["recharge"]:
            x_y = None
            self.display_text = "Recharging: Time: {}m, Bat: {}%".format(self.rechrgM,self.batPct)
            self.clear_flags(['battery_low', 'stuck'])
            self.save_text_and_map_on_whitebg(self.map_no_text)

        elif self.current_state == self.states["pause"]:
            self.display_text = "Paused: {}m, Bat: {}%".format(self.mssnM,self.batPct)
            self.save_text_and_map_on_whitebg(self.map_no_text)

        elif self.current_state == self.states["hmPostMsn"]:
            self.display_text = "End Mission: Docking"
            show_time = True
            self.log.info("MAP: end of mission")
            self.show_final_map = False

        elif self.current_state == self.states["evac"]:
            x_y = None
            self.display_text = "Emptying Bin"
            self.log.info("MAP: emptying bin")

        elif self.current_state == self.states["completed"]:
            self.display_text = "Completed"
            show_time = True
            self.log.info("MAP: mission completed")
            self.draw_final_map(True)
            draw_final = True
            
        elif self.current_state == self.states["run"]:
            self.display_text = '{} Time: {}m, Bat: {}%'.format(self.states["run"],self.mssnM,self.batPct)
            self.clear_flags(['stuck', 'new_mission'])
            self.show_final_map = False
            if self.co_ords == self.zero_coords(theta=0):
                #bogus pose received, can't have 0,0,0 when running, usually happens after recovering from an error condition
                self.log.warning('MAP: received 0,0,0 pose when running - ignoring')
                self.old_x_y = None
                return

        elif self.current_state == self.states["stop"]:
            self.display_text = "Stopped: {}m, Bat: {}%".format(self.mssnM,self.batPct)
            self.show_final_map = False

        elif self.current_state == self.states["new"]:
            self.angle = self.mapSize[4]    #reset angle
            self.base = self.make_blank_image()
            # overlay for roomba problem position
            self.roomba_problem = self.make_blank_image()
            # save x and y center of image, for centering of final map image
            self.cx = self.base.size[0] // 2
            self.cy = self.base.size[1] // 2                             
            self.room_outline_contour = self.room_outline = None
            self.show_final_map = False
            self.display_text = None
            self.timer('update_after_completed')
            self.log.info("MAP: created new image at start of new run")
            self.clear_flags()
            self.set_flags('new_mission')

        elif self.current_state == self.states["stuck"]:
            expire = self.expireM
            expire_text = 'Job Cancel in {}m'.format(expire) if expire else 'Job Cancelled'
            self.display_text = ("STUCK!: {} {}").format(self.error_message, expire_text)
            show_time = True
            self.draw_final_map(True)
            draw_final = True
            self.show_final_map = False
            self.set_flags('stuck')

        elif self.current_state == self.states["cancelled"]:
            self.display_text = "Cancelled"
            show_time = True
            self.set_flags('cancelled')

        elif self.current_state == self.states["hmMidMsn"]:
            self.display_text = "Docking"
            self.show_final_map = False
            if not self.is_set('ignore_run'):
                if self.bin_full:
                    self.set_flags('bin_full')
                else:
                    self.display_text = "Battery low: {}%, {}".format(self.batPct,self.display_text)
                    self.set_flags('battery_low')             
                
        elif self.current_state == self.states["hmUsrDock"]:
            self.display_text = "User Docking"
            show_time = True
            self.show_final_map = False
 
        else:
            self.log.warning("MAP: no special handling for state: {}".format(self.current_state))

        if self.base is None:
            self.log.warning("MAP: no image, exiting...")
            return

        if self.display_text is None:
            self.display_text = self.current_state
            
        if self.bin_full:
            self.display_text = "Bin Full: {}".format(self.display_text)
            
        #add date/time to display text
        if show_time:
            self.display_text = '{}: {}'.format(self.display_text, time.strftime("%a %b %d %H:%M:%S"))
        
        if self.show_final_map and not self.debug: #just display final map - not live
            self.log.debug("MAP: not updating map - Roomba not running")
            return

        if self.debug:
            # debug final map (careful, uses a lot of CPU power!)
            self.draw_final_map()
            
        if x_y is None:
            #set zero co_ordinates if x_y is None
            self.log.info("MAP: ignoring new co-ords in {} phase: {}".format(self.current_state, self.co_ords))
            x_y, theta = self.offset_coordinates(None)
            old_x_y = self.old_x_y
            
        #calculate co-ordinates, with 0,0 as center
        roomba_pos = self.get_roomba_pos(x_y)

        self.log.debug("MAP: old x,y: {} new x,y: {} theta: {} roomba pos: {}".format(old_x_y, x_y, theta, roomba_pos))

        #draw lines
        self.draw_vacuum_lines(self.base, old_x_y, x_y, theta)
        #draw roomba
        roomba_sprite = self.draw_roomba(roomba_pos, theta)
        #draw problem roombas
        self.draw_problem_roombas(roomba_pos)
        
        if self.roomOutline or self.auto_rotate:
            # draw room outline (saving results if this is a final map) update
            # x,y and angle if auto_rotate
            self.draw_room_outline(draw_final, x_y)
            
        out = self.base
        
        #merge floorplan into base
        if self.floorplan is not None:
            out = Image.alpha_composite(out, self.floorplan)
            
        # merge room outline into base
        if self.roomOutline:
            out = Image.alpha_composite(out, self.room_outline)
            
        #merge roomba lines (trail) with base
        out = Image.alpha_composite(out, roomba_sprite)

        #merge problem location for roomba into out
        out = Image.alpha_composite(out, self.roomba_problem)

        if draw_final and self.auto_rotate:
            #translate image to center it if auto_rotate is on
            out = self.transform_image(out)
            
        # map is upside down, so rotate 180 degrees, and size to fit
        #(NW 12/4/2018 fixed bug causing distorted maps when rotation is not 0)
        out_rotated = out.rotate(180, expand=False)
        # save composite image
        self.save_text_and_map_on_whitebg(out_rotated)
        if draw_final:
            self.show_final_map = True  # prevent re-drawing of map until reset

    def save_text_and_map_on_whitebg(self, map):
        # if no map or nothing changed
        if map is None or (map == self.previous_map_no_text and
                           self.previous_display_text == self.display_text):
            return
        self.map_no_text = map
        self.previous_map_no_text = self.map_no_text
        self.previous_display_text = self.display_text
        self.save_image(self.map_no_text, 'map_notext.png')
        
        if self.enableMapWithText:
            final = self.make_blank_image(colour=(255,255,255,255))    # white
            # paste onto a white background, so it's easy to see
            final = Image.alpha_composite(final, map)
            #(NW 12/4/2018 fixed bug causing distorted maps when rotation is not 0 - moved rotate to here)
            final = final.rotate(self.angle, expand=True) 
            # draw text
            self.draw_text(final, self.display_text, self.fnt)
            self.save_image(final, '_map.png', 'map.png')

    def ScaleRotateTranslate(self, image, angle=0, center=None, new_center=None,
                                   scale=None, expand=False):
        '''
        experimental - not used yet
        '''
        if center is None:
            return image.rotate(angle, expand)
        angle = -angle / 180.0 * math.pi
        nx, ny = x, y = center
        if new_center is not None and new_center != center:
            (nx, ny) = new_center
        sx = sy = 1.0
        if scale:
            (sx, sy) = scale, scale
        cosine = math.cos(angle)
        sine = math.sin(angle)
        a = cosine / sx
        b = sine / sx
        c = x - nx * a - ny * b
        d = -sine / sy
        e = cosine / sy
        f = y - nx * d - ny * e
        return image.transform(image.size, Image.AFFINE,
                               (a,b,c,d,e,f), resample=Image.BICUBIC)

    def draw_room_outline(self, overwrite=False, x_y=(0,0)):
        '''
        draw room outline
        '''
        if not self.roomOutline:
            return
        self.log.debug("MAP: checking room outline")
        if HAVE_CV2:
            if self.room_outline_contour is None: # or overwrite:
                self.room_outline_contour = self.load_image('room.npy')
                self.room_outline = None
            if self.room_outline is None:
                self.room_outline = self.make_new_outline_image(self.room_outline_contour)
            #is x_y inside(1), on(0) or outside(-1) contour?
            if cv2.pointPolygonTest(self.room_outline_contour, x_y, False) == -1:
                self.log.info("MAP: found new outline perimeter")
                img = Image.alpha_composite(self.base, self.room_outline)
                edgedata = np.array(img.convert('L'))
                # find external contour
                _, contours, _ = self.findContours(
                    edgedata,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
                if len(contours) == 0 or contours[0] is None: return
                if len(contours[0]) < 5: return
                self.room_outline_contour = contours[0]
                self.room_outline = self.make_new_outline_image(self.room_outline_contour)
        else:   #PIL
            if self.room_outline is None:# or overwrite:
                self.room_outline = self.load_image('room.png')
            self.room_outline = self.make_new_outline_image()

        if overwrite or self.debug:
            # save room outline
            self.save_image(self.room_outline, 'room.png')
            if HAVE_CV2:
                # save room outline contour as numpy array
                self.save_image(self.room_outline_contour, 'room.npy')
            if self.auto_rotate:
                # update outline centre
                self.get_image_parameters(
                    image=self.room_outline, contour=self.room_outline_contour,
                    final=overwrite)
                self.room_outline = self.transform_image(self.room_outline)
            self.log.info("MAP: Wrote new room outline files")
            
    def make_new_outline_image(self, contour=None):
        '''
        make image from contour
        '''
        if HAVE_CV2 and contour is not None:
            perimeter = cv2.arcLength(contour,True)
            outline = self.make_blank_image()
            edgeimage = np.array(outline)   # make blank RGBA image array
            # self.draw_edges is the max deviation from a line (set to 0.3%)
            # you can fiddle with this
            approx = cv2.approxPolyDP(contour, self.draw_edges * perimeter, True)
            # outline with grey, width 1
            cv2.drawContours(edgeimage,[approx] , -1, self.outlineColor, self.outlineWidth)
            return Image.fromarray(edgeimage)
        else:   #PIL
            if self.room_outline is None:
                self.room_outline = self.load_image('room.png')
            edges = ImageOps.invert(self.room_outline.convert('L'))
            edges.paste(self.base)
            edges = edges.convert('L').filter(ImageFilter.SMOOTH_MORE)
            edges = ImageOps.invert(edges.filter(ImageFilter.FIND_EDGES))
            return make_transparent(edges, (0, 0, 0, 255))
            
    def transform_image(self, image):
        self.log.info("MAP: calculation of center: ({},{}), "
                      "translating room outline to center it, "
                      "x:{}, y:{} deg: {:.2f}".format(
                      self.cx, self.cy,
                      self.cx - self.base.size[0] // 2,
                      self.cy - self.base.size[1] // 2,
                      self.angle))
        # center image on base map
        return image.transform(
            self.base.size, Image.AFFINE,
            (1, 0, self.cx - self.base.size[0] // 2,
             0, 1, self.cy - self.base.size[1] // 2))

    def PIL_get_image_parameters(self, image=None, start=90, end = 0, step=-1,
                                       recursion=0):
        '''
        updates angle of image, and centre using PIL.
        NOTE: this assumes the floorplan is rectangular! if you live in a
        lighthouse, the angle will not be valid!
        input is PIL image
        '''
        if image is not None and HAVE_PIL:
            imbw = image.convert('L')
            max_area = self.base.size[0] * self.base.size[1]
            x_y = (self.base.size[0] // 2, self.base.size[1] // 2)
            angle = self.angle
            div_by_10 = False
            if step >=10 or step <=-10:
                step /= 10
                div_by_10 = True
            for try_angle in range(start, end, step):
                if div_by_10:
                    try_angle /= 10.0
                #rotate image and resize to fit
                im = imbw.rotate(try_angle, expand=True)
                box = im.getbbox()
                if box is not None:
                    area = (box[2]-box[0]) * (box[3]-box[1])
                    if area < max_area:
                        angle = try_angle
                        x_y = ((box[2] - box[0]) // 2 + box[0],
                               (box[3] - box[1]) // 2 + box[1])
                        max_area = area

        if recursion >= 1:
            return x_y, angle

        x_y, angle = self.PIL_get_image_parameters(
            image,
            (angle + 1) * 10,
            (angle - 1) * 10, -10,
            recursion + 1)

        # self.log.info("MAP: PIL: image center: "
        #               "x:%d, y:%d, angle %.2f" % (x_y[0], x_y[1], angle))
        return x_y, angle

    def get_image_parameters(self, image=None, contour=None, final=False):
        '''
        updates angle of image, and centre using cv2 or PIL.
        NOTE: this assumes the floorplan is rectangular! if you live in a
        lighthouse, the angle will not be valid!
        input is cv2 contour or PIL image
        routines find the minnimum area rectangle that fits the image outline
        '''
        if contour is not None and HAVE_CV2:
            # find minnimum area rectangle that fits
            # returns (x,y), (width, height), theta - where (x,y) is the center
            x_y,l_w,angle = cv2.minAreaRect(contour)

        elif image is not None and HAVE_PIL:
            x_y, angle = self.PIL_get_image_parameters(image)

        else:
            return

        if angle < self.angle - 45:
            angle += 90
        if angle > 45-self.angle:
            angle -= 90

        if final:
            self.cx = x_y[0]
            self.cy = x_y[1]
            self.angle = angle
        self.log.info("MAP: image center: x:{}, y:{}, angle {:.2f}".format(
                      x_y[0], x_y[1], angle))

    def angle_between(self, p1, p2):
        '''
        clockwise angle between two points in degrees
        '''
        if HAVE_CV2:
            ang1 = np.arctan2(*p1[::-1])
            ang2 = np.arctan2(*p2[::-1])
            return np.rad2deg((ang1 - ang2) % (2 * np.pi))
        else:
            side1=math.sqrt(((p1[0] - p2[0]) ** 2))
            side2=math.sqrt(((p1[1] - p2[1]) ** 2))
            return math.degrees(math.atan(side2/side1))

    def findContours(self,image,mode,method):
        '''
        Version independent find contours routine. Works with OpenCV 2 or 3 or 4.
        Returns modified image (with contours applied), contours list, hierarchy
        '''
        ver = int(cv2.__version__.split(".")[0])
        im = image.copy()
        if ver == 2 or ver == 4: #NW fix for OpenCV V4 21st Dec 2018
            contours, hierarchy = cv2.findContours(im,mode,method)
            return im, contours, hierarchy
        else:
            im_cont, contours, hierarchy = cv2.findContours(im,mode,method)
            return im_cont, contours, hierarchy

    def draw_final_map(self, overwrite=False):
        '''
        draw map with outlines at end of mission. Called when mission has
        finished and Roomba has docked
        '''
        merge = self.make_blank_image()
        if HAVE_CV2:
            # NOTE: this is CPU intensive!
            edgedata = np.array(self.base.convert('L'), dtype=np.uint8)
            # find all contours
            _, contours, _ = self.findContours(
                edgedata,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
            # zero edge data for later use
            edgedata.fill(0)
            max_perimeter = 0
            max_contour = None
            for cnt in contours:
                perimeter = cv2.arcLength(cnt,True)
                if perimeter >= max_perimeter:
                    max_contour = cnt   # get the contour with maximum length
                    max_perimeter = perimeter
            if max_contour is None: return
            if len(max_contour) < 5: return
            try:
                contours.remove(max_contour)    # remove max contour from list
            except ValueError:
                self.log.warning("MAP: unable to remove contour")
                pass

            mask = np.full(edgedata.shape, 255, dtype=np.uint8) # white
            # create mask (of other contours) in black
            cv2.drawContours(mask,contours, -1, 0, -1)

            # self.draw_edges is the max deviation from a line
            # you can fiddle with this in enable_map
            approx = cv2.approxPolyDP(max_contour,
                self.draw_edges * max_perimeter,True)

            bgimage = np.array(merge)   # make blank RGBA image array
            # draw contour and fill with "lawngreen" (default)
            cv2.drawContours(bgimage,[approx] , -1, self.fillColor, -1)
            # mask image with internal contours
            bgimage = cv2.bitwise_and(bgimage,bgimage,mask = mask)
            # not dure if you really need this - uncomment if you want the
            # area outlined.
            # draw longest contour aproximated to lines (in black), width 1
            cv2.drawContours(edgedata,[approx] , -1, (255), 1)

            outline = Image.fromarray(edgedata) # outline
            base = Image.fromarray(bgimage)   # filled background image
        else:   #PIL
            base = self.base.filter(ImageFilter.SMOOTH_MORE)
            # draw edges at end of mission
            outline = base.convert('L').filter(ImageFilter.FIND_EDGES)
            # outline = ImageChops.subtract(
            #     base.convert('L').filter(ImageFilter.EDGE_ENHANCE),
            #     base.convert('L'))

        edges = ImageOps.invert(outline)
        edges = make_transparent(edges, (0, 0, 0, 255))
        if self.debug:
            self.save_image(edges, 'edges.png')
        merge = Image.alpha_composite(merge,base)
        if self.floorplan is None:
            merge = Image.alpha_composite(merge,edges)
        if overwrite:
            self.log.info("MAP: Drawing final map")
            self.timer('update_after_completed', True, 3600)
            self.base=merge

        if self.debug:
            merge_rotated = merge.rotate(180+self.angle, expand=True)
            self.save_image(merge_rotated, 'final_map.png')
                
if __name__ == '__main__':
    from roomba_direct import main
    main()
