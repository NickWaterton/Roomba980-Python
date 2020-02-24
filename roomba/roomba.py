#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Python 2.7/Python 3.5/3.6 (thanks to pschmitt for adding Python 3 compatibility)
Program to connect to Roomba 980 vacuum cleaner, dcode json, and forward to mqtt
server

Nick Waterton 24th April 2017: V 1.0: Initial Release
Nick Waterton 4th July   2017  V 1.1.1: Fixed MQTT protocol version, and map
paths, fixed paho-mqtt tls changes
Nick Waterton 5th July   2017  V 1.1.2: Minor fixes, CV version 3 .2 support
Nick Waterton 7th July   2017  V1.2.0: Added -o option "roomOutline" allows
enabling/disabling of room outline drawing, added auto creation of css/html files
Nick Waterton 11th July  2017  V1.2.1: Quick (untested) fix for room outlines
if you don't have OpenCV
"""

from __future__ import print_function
from __future__ import absolute_import

__version__ = "1.2.1"

from ast import literal_eval
from collections.abc import Mapping
from collections import OrderedDict
from roomba.mqttclient import RoombaMQTTClient
import datetime
import json
import math
import logging
import os
import six
import threading
import time

global HAVE_CV2
global HAVE_PIL
HAVE_CV2 = False
HAVE_PIL = False

try:
    import cv2
    import numpy as np

    HAVE_CV2 = True
except ImportError:
    print("CV or numpy module not found, falling back to PIL")

# NOTE: MUST use Pillow Pillow 4.1.1 to avoid some horrible memory leaks in the
# text handling!
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

    HAVE_PIL = True
except ImportError:
    print("PIL module not found, maps are disabled")

MAX_CONNECTION_RETRIES = 3


class RoombaConnectionError(Exception):
    pass


class Roomba:
    """
    This is a Class for Roomba 900 series WiFi connected Vacuum cleaners
    Requires firmware version 2.0 and above (not V1.0). Tested with Roomba 980
    username (blid) and password are required, and can be found using the
    password() class above (or can be auto discovered)
    Most of the underlying info was obtained from here:
    https://github.com/koalazak/dorita980 many thanks!
    The values received from the Roomba as stored in a dictionay called
    master_state, and can be accessed at any time, the contents are live, and
    will build with time after connection.
    This is not needed if the forward to mqtt option is used, as the events will
    be decoded and published on the designated mqtt client topic.
    """

    states = {
        "charge": "Charging",
        "new": "New Mission",
        "run": "Running",
        "resume": "Running",
        "hmMidMsn": "Recharging",
        "recharge": "Recharging",
        "stuck": "Stuck",
        "hmUsrDock": "User Docking",
        "dock": "Docking",
        "dockend": "Docking - End Mission",
        "cancelled": "Cancelled",
        "stop": "Stopped",
        "pause": "Paused",
        "hmPostMsn": "End Mission",
        "": None,
    }

    # From http://homesupport.irobot.com/app/answers/detail/a_id/9024/~/roomba-900-error-messages
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
        65: "Hardware problem detected",
        66: "Low memory",
        68: "Hardware problem detected",
        73: "Pad type changed",
        74: "Max area reached",
        75: "Navigation problem",
        76: "Hardware problem detected"
    }

    def __init__(
        self,
        address=None,
        blid=None,
        password=None,
        topic="#",
        continuous=True,
        delay=1,
        cert_name=None,
        roombaName=""
    ):
        """
        address is the IP address of the Roomba, the continuous flag enables a
        continuous mqtt connection, if this is set to False, the client connects
        and disconnects every 'delay' seconds (1 by default, but can be
        changed). This is to allow other programs access, as there can only be
        one Roomba connection at a time.
        As cloud connections are unaffected, I reccomend leaving this as True.
        leave topic as is, unless debugging (# = all messages).
        if a python standard logging object exists, it will be used for logging.
        """

        self.debug = False
        self.log = logging.getLogger(__name__)
        if self.log.getEffectiveLevel() == logging.DEBUG:
            self.debug = True
        self.address = address
        self.continuous = continuous
        if self.continuous:
            self.log.debug("CONTINUOUS connection")
        else:
            self.log.debug("PERIODIC connection")
        # set the following to True to enable pretty printing of json data
        self.pretty_print = False
        self.stop_connection = False
        self.periodic_connection_running = False
        self.roombaName = roombaName
        self.topic = topic
        self.mqttc = None
        self.exclude = ""
        self.delay = delay
        self.periodic_connection_duration = 10
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
        self.base = None  # base map
        self.dock_icon = None  # dock icon
        self.roomba_icon = None  # roomba icon
        self.roomba_cancelled_icon = None  # roomba cancelled icon
        self.roomba_battery_icon = None  # roomba battery low icon
        self.roomba_error_icon = None  # roomba error icon
        self.bin_full_icon = None  # bin full icon
        self.room_outline_contour = None
        self.room_outline = None
        self.transparent = (0, 0, 0, 0)  # transparent
        self.previous_display_text = self.display_text = None
        self.master_state = {}  # all info from roomba stored here
        self.time = time.time()
        self.update_seconds = 300  # update with all values every 5 minutes
        self.show_final_map = True
        self.client = self._get_client(address, blid, password, cert_name)
        self._thread = threading.Thread(target=self.periodic_connection)

    def _get_client(self, address, blid, password, cert_path):
        client = RoombaMQTTClient(
            address=address,
            blid=blid,
            password=password,
            cert_path=cert_path)
        client.set_on_message(self.on_message)
        client.set_on_connect(self.on_connect)
        client.set_on_publish(self.on_publish)
        client.set_on_subscribe(self.on_subscribe)
        client.set_on_disconnect(self.on_disconnect)
        return client

    def connect(self):
        if self.roomba_connected or self.periodic_connection_running:
            return

        if self.continuous:
            if not self._connect():
                if self.mqttc is not None:
                    self.mqttc.disconnect()
                raise Exception("failed to connect!")
        else:
            self._thread.daemon = True
            self._thread.start()

        self.time = time.time()  # save connection time

    def _connect(self):
        attempt = 1
        while attempt <= MAX_CONNECTION_RETRIES:
            try:
                self.log.debug("Connecting to %s, attempt %s", self.address, attempt)
                self.client.connect()
                return True
            except Exception as e:
                self.log.error("Error: %s ", e)
                self.log.debug("Can't connect to %s, retrying", self.address)
            attempt += 1

        self.log.error("Unable to connect to %s", self.address)
        raise RoombaConnectionError("Unable to connect to Roomba at {}".format(self.address))

    def disconnect(self):
        if self.continuous:
            self.client.disconnect()
        else:
            self.stop_connection = True

    def periodic_connection(self):
        # only one connection thread at a time!
        if self.periodic_connection_running:
            return
        self.periodic_connection_running = True
        while not self.stop_connection:
            if self._connect():
                time.sleep(self.periodic_connection_duration)
                self.client.disconnect()
            time.sleep(self.delay)

        self.client.disconnect()
        self.periodic_connection_running = False

    def on_connect(self, client, userdata, flags, rc):
        self.log.info("Connected to Roomba %s", self.roombaName)
        if rc == 0:
            self.roomba_connected = True
            self.client.subscribe(self.topic)
        else:
            self.log.error("Roomba Connected with result code %s", str(rc))
            self.log.error("Please make sure your blid and password are correct %s", self.roombaName)
            if self.mqttc is not None:
                self.mqttc.disconnect()
            raise Exception("Failure in on_connect")

    def on_message(self, mosq, obj, msg):
        # print("on_message", msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
        if self.exclude != "":
            if self.exclude in msg.topic:
                return

        if self.indent == 0:
            self.master_indent = max(self.master_indent, len(msg.topic))

        log_string, json_data = self.decode_payload(msg.topic, msg.payload)
        self.dict_merge(self.master_state, json_data)

        if self.pretty_print:
            self.log.debug("%-{:d}s : %s".format(self.master_indent), msg.topic, log_string)
        else:
            self.log.debug(
                "Received Roomba Data %s: %s, %s",
                self.roombaName,
                str(msg.topic),
                str(msg.payload),
            )

        if self.raw:
            self.publish(msg.topic, msg.payload)
        else:
            self.decode_topics(json_data)

        # default every 5 minutes
        if time.time() - self.time > self.update_seconds:
            self.log.debug("Publishing master_state %s", self.roombaName)
            self.decode_topics(self.master_state)  # publish all values
            self.time = time.time()

    def on_publish(self, mosq, obj, mid):
        pass

    def on_subscribe(self, mosq, obj, mid, granted_qos):
        self.log.debug("Subscribed: %s %s", str(mid), str(granted_qos))

    def on_disconnect(self, mosq, obj, rc):
        self.roomba_connected = False
        if rc != 0:
            self.log.warning(
                "Unexpectedly disconnected from Roomba %s! - reconnecting",
                self.roombaName,
            )
        else:
            self.log.info("Disconnected from Roomba %s", self.roombaName)

    def on_log(self, mosq, obj, level, string):
        self.log.debug(string)

    def set_mqtt_client(self, mqttc=None, brokerFeedback=""):
        self.mqttc = mqttc
        if self.mqttc is not None:
            if self.roombaName != "":
                self.brokerFeedback = brokerFeedback + "/" + self.roombaName
            else:
                self.brokerFeedback = brokerFeedback

    def send_command(self, command):
        self.log.debug("Send command: %s", command)
        roomba_command = OrderedDict()
        roomba_command["command"] = command
        roomba_command["time"] = self.totimestamp(datetime.datetime.now())
        roomba_command["initiator"] = "localApp"
        str_command = json.dumps(roomba_command)
        self.log.debug("Publishing Roomba Command : %s", str_command)
        self.client.publish("cmd", str_command)

    def set_preference(self, preference, setting):
        self.log.debug("Set preference: %s, %s", preference, setting)
        val = False
        if setting.lower() == "true":
            val = True
        tmp = {preference: val}
        roomba_command = {"state": tmp}
        str_command = json.dumps(roomba_command)
        self.log.debug("Publishing Roomba Setting : %s" % str_command)
        self.client.publish("delta", str_command)

    def publish(self, topic, message):
        if self.mqttc is not None and message is not None:
            self.log.debug("Publishing item: %s: %s" % (self.brokerFeedback + "/" + topic, message))
            self.mqttc.publish(self.brokerFeedback + "/" + topic, message)

    def set_options(self, raw=False, indent=0, pretty_print=False):
        self.raw = raw
        self.indent = indent
        self.pretty_print = pretty_print
        if self.raw:
            self.log.debug("Posting RAW data")
        else:
            self.log.debug("Posting DECODED data")

    def enable_map(
        self,
        enable=False,
        mapSize="(800,1500,0,0,0,0)",
        mapPath=".",
        iconPath="./",
        roomOutline=True,
        home_icon_file="home.png",
        roomba_icon_file="roomba.png",
        roomba_error_file="roombaerror.png",
        roomba_cancelled_file="roombacancelled.png",
        roomba_battery_file="roomba-charge.png",
        bin_full_file="binfull.png",
        roomba_size=(50, 50),
        draw_edges=30,
        auto_rotate=True,
    ):
        """
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
        """

        if not HAVE_PIL:  # can't draw a map without PIL!
            return False

        if Image.PILLOW_VERSION < "4.1.1":
            print(
                "WARNING: PIL version is %s, this is not the latest! you "
                "can get bad memory leaks with old versions of PIL"
                % Image.PILLOW_VERSION
            )
            print("run: 'pip install --upgrade pillow' to fix this")

        self.drawmap = enable
        if self.drawmap:
            self.log.info("MAP: Maps Enabled")
            self.mapSize = literal_eval(mapSize)
            if len(mapSize) < 6:
                self.log.error(
                    "mapSize is required, and is of the form "
                    "(800,1500,0,0,0,0) - (x,y size, x,y dock loc,"
                    "theta1, theta2), map,roomba roatation"
                )
                self.drawmap = False
                return False
            self.angle = self.mapSize[4]
            self.roomba_angle = self.mapSize[5]
            self.mapPath = mapPath
            if home_icon_file is None:
                self.home_icon_file = None
            else:
                self.home_icon_file = os.path.join(iconPath, home_icon_file)
            self.roomba_icon_file = os.path.join(iconPath, roomba_icon_file)
            self.roomba_error_file = os.path.join(iconPath, roomba_error_file)
            self.roomba_cancelled_file = os.path.join(iconPath, roomba_cancelled_file)
            self.roomba_battery_file = os.path.join(iconPath, roomba_battery_file)
            self.bin_full_file = os.path.join(iconPath, bin_full_file)
            self.draw_edges = draw_edges // 10000
            self.auto_rotate = auto_rotate
            if not roomOutline:
                self.log.info("MAP: Not drawing Room Outline")
            self.roomOutline = roomOutline

            self.initialise_map(roomba_size)
            return True
        return False

    def totimestamp(self, dt):
        td = dt - datetime.datetime(1970, 1, 1)
        return int(td.total_seconds())

    def dict_merge(self, dct, merge_dct):
        """
        Recursive dict merge. Inspired by :meth:``dict.update()``, instead
        of updating only top-level keys, dict_merge recurses down into dicts
        nested to an arbitrary depth, updating keys. The ``merge_dct`` is
        merged into ``dct``.
        :param dct: dict onto which the merge is executed
        :param merge_dct: dct merged into dct
        :return: None
        """
        for k, v in six.iteritems(merge_dct):
            if (
                k in dct
                and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], Mapping)
            ):
                self.dict_merge(dct[k], merge_dct[k])
            else:
                dct[k] = merge_dct[k]

    def decode_payload(self, topic, payload):
        """
        Format json for pretty printing, return string sutiable for logging,
        and a dict of the json data
        """
        indent = self.master_indent + 31  # number of spaces to indent json data

        try:
            # if it's json data, decode it (use OrderedDict to preserve keys
            # order), else return as is...
            json_data = json.loads(
                payload.decode("utf-8")
                .replace(":nan", ":NaN")
                .replace(":inf", ":Infinity")
                .replace(":-inf", ":-Infinity"),
                object_pairs_hook=OrderedDict,
            )
            # if it's not a dictionary, probably just a number
            if not isinstance(json_data, dict):
                return json_data, dict(json_data)
            json_data_string = "\n".join(
                (indent * " ") + i
                for i in (json.dumps(json_data, indent=2)).splitlines()
            )

            formatted_data = "Decoded JSON: \n%s" % json_data_string

        except ValueError:
            formatted_data = payload

        if self.raw:
            formatted_data = payload

        return formatted_data, dict(json_data)

    def decode_topics(self, state, prefix=None):
        """
        decode json data dict, and publish as individual topics to
        brokerFeedback/topic the keys are concatinated with _ to make one unique
        topic name strings are expressely converted to strings to avoid unicode
        representations
        """
        for k, v in six.iteritems(state):
            if isinstance(v, dict):
                if prefix is None:
                    self.decode_topics(v, k)
                else:
                    self.decode_topics(v, prefix + "_" + k)
            else:
                if isinstance(v, list):
                    newlist = []
                    for i in v:
                        if isinstance(i, dict):
                            for ki, vi in six.iteritems(i):
                                newlist.append((str(ki), vi))
                        else:
                            if isinstance(i, six.string_types):
                                i = str(i)
                            newlist.append(i)
                    v = newlist
                if prefix is not None:
                    k = prefix + "_" + k
                # all data starts with this, so it's redundant
                k = k.replace("state_reported_", "")
                # save variables for drawing map
                if k == "pose_theta":
                    self.co_ords["theta"] = v
                if k == "pose_point_x":  # x and y are reversed...
                    self.co_ords["y"] = v
                if k == "pose_point_y":
                    self.co_ords["x"] = v
                if k == "bin_full":
                    self.bin_full = v
                if k == "cleanMissionStatus_error":
                    try:
                        self.error_message = self._ErrorMessages[v]
                    except KeyError as e:
                        self.log.warning(
                            "Error looking up Roomba error " "message: %s", e
                        )
                        self.error_message = "Unknown Error number: %d" % v
                    self.publish("error_message", self.error_message)
                if k == "cleanMissionStatus_phase":
                    self.previous_cleanMissionStatus_phase = (
                        self.cleanMissionStatus_phase
                    )
                    self.cleanMissionStatus_phase = v

                self.publish(k, str(v))

        if prefix is None:
            self.update_state_machine()

    def update_state_machine(self, new_state=None):
        """
        Roomba progresses through states (phases), current identified states
        are:
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
        Mid mission recharge is "" -> charge -> run -> hmMidMsn -> charge
                                   -> run -> hmPostMsn -> charge
        Stuck is "" -> charge -> run -> hmPostMsn -> stuck
                    -> run/charge/stop/hmUsrDock -> charge
        Start program during run is "" -> run -> hmPostMsn -> charge

        Need to identify a new mission to initialize map, and end of mission to
        finalise map.
        Assume  charge -> run = start of mission (init map)
                stuck - > charge = init map
        Assume hmPostMsn -> charge = end of mission (finalize map)
        Anything else = continue with existing map
        """

        current_mission = self.current_state

        # if self.current_state == None: #set initial state here for debugging
        #    self.current_state = self.states["recharge"]
        #    self.show_final_map = False

        #  deal with "bin full" timeout on mission
        try:
            if (
                self.master_state["state"]["reported"]["cleanMissionStatus"]["mssnM"]
                == "none"
                and self.cleanMissionStatus_phase == "charge"
                and (
                    self.current_state == self.states["pause"]
                    or self.current_state == self.states["recharge"]
                )
            ):
                self.current_state = self.states["cancelled"]
        except KeyError:
            pass

        if (
            self.current_state == self.states["charge"]
            and self.cleanMissionStatus_phase == "run"
        ):
            self.current_state = self.states["new"]
        elif (
            self.current_state == self.states["run"]
            and self.cleanMissionStatus_phase == "hmMidMsn"
        ):
            self.current_state = self.states["dock"]
        elif (
            self.current_state == self.states["dock"]
            and self.cleanMissionStatus_phase == "charge"
        ):
            self.current_state = self.states["recharge"]
        elif (
            self.current_state == self.states["recharge"]
            and self.cleanMissionStatus_phase == "charge"
            and self.bin_full
        ):
            self.current_state = self.states["pause"]
        elif (
            self.current_state == self.states["run"]
            and self.cleanMissionStatus_phase == "charge"
        ):
            self.current_state = self.states["recharge"]
        elif (
            self.current_state == self.states["recharge"]
            and self.cleanMissionStatus_phase == "run"
        ):
            self.current_state = self.states["pause"]
        elif (
            self.current_state == self.states["pause"]
            and self.cleanMissionStatus_phase == "charge"
        ):
            self.current_state = self.states["pause"]
            # so that we will draw map and can update recharge time
            current_mission = None
        elif (
            self.current_state == self.states["charge"]
            and self.cleanMissionStatus_phase == "charge"
        ):
            # so that we will draw map and can update charge status
            current_mission = None
        elif (
            self.current_state == self.states["stop"]
            or self.current_state == self.states["pause"]
        ) and self.cleanMissionStatus_phase == "hmUsrDock":
            self.current_state = self.states["cancelled"]
        elif (
            self.current_state == self.states["hmUsrDock"]
            or self.current_state == self.states["cancelled"]
        ) and self.cleanMissionStatus_phase == "charge":
            self.current_state = self.states["dockend"]
        elif (
            self.current_state == self.states["hmPostMsn"]
            and self.cleanMissionStatus_phase == "charge"
        ):
            self.current_state = self.states["dockend"]
        elif (
            self.current_state == self.states["dockend"]
            and self.cleanMissionStatus_phase == "charge"
        ):
            self.current_state = self.states["charge"]

        else:
            self.current_state = self.states[self.cleanMissionStatus_phase]

        if new_state is not None:
            self.current_state = self.states[new_state]
            self.log.debug("Current state: %s", self.current_state)

        if self.current_state != current_mission:
            self.log.debug("State updated to: %s", self.current_state)

        self.publish("state", self.current_state)
        self.draw_map(current_mission != self.current_state)

    def make_transparent(self, image, colour=None):
        """
        take image and make white areas transparent
        return transparent image
        """
        image = image.convert("RGBA")
        datas = image.getdata()
        new_data = []
        for item in datas:
            # white (ish)
            if item[0] >= 254 and item[1] >= 254 and item[2] >= 254:
                new_data.append(self.transparent)
            else:
                if colour:
                    new_data.append(colour)
                else:
                    new_data.append(item)

        image.putdata(new_data)
        return image

    def make_icon(self, input="./roomba.png", output="./roomba_mod.png"):
        # utility function to make roomba icon from generic roomba icon
        if not HAVE_PIL:  # drawing library loaded?
            self.log.error("PIL module not loaded")
            return None
        try:
            roomba = Image.open(input).convert("RGBA")
            roomba = roomba.rotate(90, expand=False)
            roomba = self.make_transparent(roomba)
            draw_wedge = ImageDraw.Draw(roomba)
            draw_wedge.pieslice(
                [(5, 0), (roomba.size[0] - 5, roomba.size[1])],
                175,
                185,
                fill="red",
                outline="red",
            )
            roomba.save(output, "PNG")
            return roomba
        except Exception as e:
            self.log.error("ERROR: %s", e)
            return None

    def load_icon(
        self, filename="", icon_name=None, fnt=None, size=(32, 32), base_icon=None
    ):
        """
        Load icon from file, or draw icon if file not found.
        returns icon object
        """
        if icon_name is None:
            return None

        try:
            icon = Image.open(filename).convert("RGBA").resize(size, Image.ANTIALIAS)
            icon = self.make_transparent(icon)
        except IOError as e:
            self.log.warning(
                "Error loading %s: %s, using default icon " "instead", icon_name, e
            )
            if base_icon is None:
                icon = Image.new("RGBA", size, self.transparent)
            else:
                icon = base_icon

            draw_icon = ImageDraw.Draw(icon)

            if icon_name == "roomba":
                if base_icon is None:
                    draw_icon.ellipse(
                        [(5, 5), (icon.size[0] - 5, icon.size[1] - 5)],
                        fill="green",
                        outline="black",
                    )
                draw_icon.pieslice(
                    [(5, 5), (icon.size[0] - 5, icon.size[1] - 5)],
                    355,
                    5,
                    fill="red",
                    outline="red",
                )
            elif icon_name == "stuck":
                if base_icon is None:
                    draw_icon.ellipse(
                        [(5, 5), (icon.size[0] - 5, icon.size[1] - 5)],
                        fill="green",
                        outline="black",
                    )
                    draw_icon.pieslice(
                        [(5, 5), (icon.size[0] - 5, icon.size[1] - 5)],
                        175,
                        185,
                        fill="red",
                        outline="red",
                    )
                draw_icon.polygon(
                    [(icon.size[0] // 2, icon.size[1]), (0, 0), (0, icon.size[1])],
                    fill="red",
                )
                if fnt is not None:
                    draw_icon.text((4, -4), "!", font=fnt, fill=(255, 255, 255, 255))
            elif icon_name == "cancelled":
                if base_icon is None:
                    draw_icon.ellipse(
                        [(5, 5), (icon.size[0] - 5, icon.size[1] - 5)],
                        fill="green",
                        outline="black",
                    )
                    draw_icon.pieslice(
                        [(5, 5), (icon.size[0] - 5, icon.size[1] - 5)],
                        175,
                        185,
                        fill="red",
                        outline="red",
                    )
                if fnt is not None:
                    draw_icon.text((4, -4), "X", font=fnt, fill=(255, 0, 0, 255))
            elif icon_name == "bin full":
                draw_icon.rectangle(
                    [
                        icon.size[0] - 10,
                        icon.size[1] - 10,
                        icon.size[0] + 10,
                        icon.size[1] + 10,
                    ],
                    fill="grey",
                )
                if fnt is not None:
                    draw_icon.text((4, -4), "F", font=fnt, fill=(255, 255, 255, 255))
            elif icon_name == "battery":
                draw_icon.rectangle(
                    [
                        icon.size[0] - 10,
                        icon.size[1] - 10,
                        icon.size[0] + 10,
                        icon.size[1] + 10,
                    ],
                    fill="orange",
                )
                if fnt is not None:
                    draw_icon.text((4, -4), "B", font=fnt, fill=(255, 255, 255, 255))
            elif icon_name == "home":
                draw_icon.rectangle([0, 0, 32, 32], fill="red", outline="black")
                if fnt is not None:
                    draw_icon.text((4, -4), "D", font=fnt, fill=(255, 255, 255, 255))
            else:
                icon = None
        # rotate icon 180 degrees
        icon = icon.rotate(180 - self.angle, expand=False)
        return icon

    def initialise_map(self, roomba_size):
        """
        Initialize all map items (base maps, overlay, icons fonts etc)
        """
        # get base image of Roomba path
        if self.base is None:
            try:
                self.log.debug("MAP: openening existing line image")
                self.base = Image.open(
                    self.mapPath + "/" + self.roombaName + "lines.png"
                ).convert("RGBA")
                if self.base.size != (self.mapSize[0], self.mapSize[1]):
                    raise IOError("Image is wrong size")
            except IOError as e:
                self.base = Image.new(
                    "RGBA", (self.mapSize[0], self.mapSize[1]), self.transparent
                )
                self.log.warning("MAP: line image problem: %s: created new " "image", e)

            try:
                self.log.debug("MAP: openening existing problems image")
                self.roomba_problem = Image.open(
                    self.mapPath + "/" + self.roombaName + "problems.png"
                ).convert("RGBA")
                if self.roomba_problem.size != self.base.size:
                    raise IOError("Image is wrong size")
            except IOError as e:
                self.roomba_problem = Image.new(
                    "RGBA", self.base.size, self.transparent
                )
                self.log.warning(
                    "MAP: problems image problem: %s: created new image", e
                )

            try:
                self.log.debug("MAP: openening existing map no text image")
                self.previous_map_no_text = None
                self.map_no_text = Image.open(
                    "{}/{}map_no_text.png".format(self.mapPath, self.roombaName)
                ).convert("RGBA")
                if self.map_no_text.size != self.base.size:
                    raise IOError("Image is wrong size")
            except IOError as e:
                self.map_no_text = None
                self.log.warning(
                    "MAP: map no text image problem: %s: set ", "to None", e
                )
        # save x and y center of image, for centering of final map image
        self.cx = self.base.size[0]
        self.cy = self.base.size[1]

        # get a font
        if self.fnt is None:
            try:
                self.fnt = ImageFont.truetype("FreeMono.ttf", 40)
            except IOError as e:
                self.log.warning("Error loading font: %s, loading default " "font", e)
                self.fnt = ImageFont.load_default()

        # set dock home position
        if self.home_pos is None:
            self.home_pos = (
                self.mapSize[0] // 2 + self.mapSize[2],
                self.mapSize[1] // 2 + self.mapSize[3],
            )
            self.log.debug("MAP: home_pos: (%d,%d)", self.home_pos[0], self.home_pos[1])

        # get icons
        if self.roomba_icon is None:
            self.roomba_icon = self.load_icon(
                filename=self.roomba_icon_file,
                icon_name="roomba",
                fnt=self.fnt,
                size=roomba_size,
                base_icon=None,
            )

        if self.roomba_error_icon is None:
            self.roomba_error_icon = self.load_icon(
                filename=self.roomba_error_file,
                icon_name="stuck",
                fnt=self.fnt,
                size=roomba_size,
                base_icon=self.roomba_icon,
            )

        if self.roomba_cancelled_icon is None:
            self.roomba_cancelled_icon = self.load_icon(
                filename=self.roomba_cancelled_file,
                icon_name="cancelled",
                fnt=self.fnt,
                size=roomba_size,
                base_icon=self.roomba_icon,
            )

        if self.roomba_battery_icon is None:
            self.roomba_battery_icon = self.load_icon(
                filename=self.roomba_battery_file,
                icon_name="battery",
                fnt=self.fnt,
                size=roomba_size,
                base_icon=self.roomba_icon,
            )

        if self.dock_icon is None and self.home_icon_file is not None:
            self.dock_icon = self.load_icon(
                filename=self.home_icon_file, icon_name="home", fnt=self.fnt
            )
            self.dock_position = (
                self.home_pos[0] - self.dock_icon.size[0] // 2,
                self.home_pos[1] - self.dock_icon.size[1] // 2,
            )

        if self.bin_full_icon is None:
            self.bin_full_icon = self.load_icon(
                filename=self.bin_full_file,
                icon_name="bin full",
                fnt=self.fnt,
                size=roomba_size,
                base_icon=self.roomba_icon,
            )

        self.log.debug("MAP: Initialisation complete")

    def transparent_paste(self, base_image, icon, position):
        """
        needed because PIL pasting of transparent imges gives weird results
        """
        image = Image.new("RGBA", self.base.size, self.transparent)
        image.paste(icon, position)
        base_image = Image.alpha_composite(base_image, image)
        return base_image

    def zero_coords(self):
        """
        returns dictionary with default zero coords
        """
        return {"x": 0, "y": 0, "theta": 180}

    def offset_coordinates(self, old_co_ords, new_co_ords):
        """
        offset coordinates according to mapSize settings, with 0,0 as center
        """
        x_y = (
            new_co_ords["x"] + self.mapSize[0] // 2 + self.mapSize[2],
            new_co_ords["y"] + self.mapSize[1] // 2 + self.mapSize[3],
        )
        old_x_y = (
            old_co_ords["x"] + self.mapSize[0] // 2 + self.mapSize[2],
            old_co_ords["y"] + self.mapSize[1] // 2 + self.mapSize[3],
        )

        theta = int(new_co_ords["theta"] - 90 + self.roomba_angle)
        while theta > 359:
            theta = 360 - theta
        while theta < 0:
            theta = 360 + theta

        return old_x_y, x_y, theta

    def get_roomba_pos(self, x_y):
        """
        calculate roomba position as list
        """
        return [
            x_y[0] - self.roomba_icon.size[0] // 2,
            x_y[1] - self.roomba_icon.size[1] // 2,
            x_y[0] + self.roomba_icon.size[0] // 2,
            x_y[1] + self.roomba_icon.size[1] // 2,
        ]

    def draw_vacuum_lines(self, image, old_x_y, x_y, theta, colour="lawngreen"):
        """
        draw lines on image from old_x_y to x_y reepresenting vacuum coverage,
        taking into account angle theta (roomba angle).
        """
        lines = ImageDraw.Draw(image)
        if x_y != old_x_y:
            self.log.debug("MAP: drawing line: %s, %s", old_x_y, x_y)
            lines.line([old_x_y, x_y], fill=colour, width=self.roomba_icon.size[0] // 2)
        # draw circle over roomba vacuum area to give smooth edges.
        arcbox = [
            x_y[0] - self.roomba_icon.size[0] // 4,
            x_y[1] - self.roomba_icon.size[0] // 4,
            x_y[0] + self.roomba_icon.size[0] // 4,
            x_y[1] + self.roomba_icon.size[0] // 4,
        ]
        lines.ellipse(arcbox, fill=colour)

    def draw_text(
        self,
        image,
        display_text,
        fnt,
        pos=(0, 0),
        colour=(0, 0, 255, 255),
        rotate=False,
    ):
        # draw text - (WARNING old versions of PIL have huge memory leak here!)
        if display_text is None:
            return
        self.log.debug("MAP: writing text: pos: %s, text: %s", pos, display_text)
        if rotate:
            txt = Image.new("RGBA", (fnt.getsize(display_text)), self.transparent)
            text = ImageDraw.Draw(txt)
            # draw text rotated 180 degrees...
            text.text((0, 0), display_text, font=fnt, fill=colour)
            image.paste(txt.rotate(180 - self.angle, expand=True), pos)
        else:
            text = ImageDraw.Draw(image)
            text.text(pos, display_text, font=fnt, fill=colour)

    def draw_map(self, force_redraw=False):
        """
        Draw map of Roomba cleaning progress
        """
        if (
            (
                self.co_ords != self.previous_co_ords
                or self.cleanMissionStatus_phase
                != self.previous_cleanMissionStatus_phase
            )
            or force_redraw
        ) and self.drawmap:
            self.render_map(self.co_ords, self.previous_co_ords)
            self.previous_co_ords = self.co_ords.copy()
            self.previous_cleanMissionStatus_phase = self.cleanMissionStatus_phase

    def render_map(self, new_co_ords, old_co_ords):
        """
        draw map
        """
        draw_final = False
        stuck = False
        cancelled = False
        bin_full = False
        battery_low = False

        # program just started, and we don't have phase yet.
        if self.current_state is None:
            return

        if not self.show_final_map:
            self.log.debug(
                "MAP: received: new_co_ords: %s old_co_ords: %s "
                "phase: %s, state: %s",
                new_co_ords,
                old_co_ords,
                self.cleanMissionStatus_phase,
                self.current_state,
            )

        if self.current_state == self.states["charge"]:
            self.log.debug("MAP: Ignoring new co-ords in charge phase")
            new_co_ords = old_co_ords = self.zero_coords()
            self.display_text = (
                "Charging: Battery: "
                + str(self.master_state["state"]["reported"]["batPct"])
                + "%"
            )
            if self.bin_full:
                self.display_text = "Bin Full," + self.display_text.replace(
                    "Charging", "Not Ready"
                )
            if (
                self.last_completed_time is None
                or time.time() - self.last_completed_time > 3600
            ):
                self.save_text_and_map_on_whitebg(self.map_no_text)
            draw_final = True

        elif self.current_state == self.states["recharge"]:
            self.log.debug("MAP: ignoring new co-ords in recharge phase")
            new_co_ords = old_co_ords = self.zero_coords()
            self.display_text = (
                "Recharging:"
                + " Time: "
                + str(
                    self.master_state["state"]["reported"]["cleanMissionStatus"][
                        "rechrgM"
                    ]
                )
                + "m"
            )
            if self.bin_full:
                self.display_text = "Bin Full," + self.display_text
            self.save_text_and_map_on_whitebg(self.map_no_text)

        elif self.current_state == self.states["pause"]:
            self.log.debug("MAP: ignoring new co-ords in pause phase")
            new_co_ords = old_co_ords
            self.display_text = (
                "Paused: "
                + str(
                    self.master_state["state"]["reported"]["cleanMissionStatus"][
                        "mssnM"
                    ]
                )
                + "m, Bat: "
                + str(self.master_state["state"]["reported"]["batPct"])
                + "%"
            )
            if self.bin_full:
                self.display_text = "Bin Full," + self.display_text
                # assume roomba is docked...
                new_co_ords = old_co_ords = self.zero_coords()
            self.save_text_and_map_on_whitebg(self.map_no_text)

        elif self.current_state == self.states["hmPostMsn"]:
            self.display_text = "Completed: " + time.strftime("%a %b %d %H:%M:%S")
            self.log.debug("MAP: end of mission")

        elif self.current_state == self.states["dockend"]:
            self.log.debug(
                "MAP: mission completed: ignoring new co-ords in " "docking phase"
            )
            new_co_ords = old_co_ords = self.zero_coords()
            self.draw_final_map(True)
            draw_final = True

        elif (
            self.current_state == self.states["run"]
            or self.current_state == self.states["stop"]
            or self.current_state == self.states["pause"]
        ):
            if self.current_state == self.states["run"]:
                self.display_text = (
                    self.states["run"]
                    + " Time: "
                    + str(
                        self.master_state["state"]["reported"]["cleanMissionStatus"][
                            "mssnM"
                        ]
                    )
                    + "m, Bat: "
                    + str(self.master_state["state"]["reported"]["batPct"])
                    + "%"
                )
            else:
                self.display_text = None
            self.show_final_map = False

        elif self.current_state == self.states["new"]:
            self.angle = self.mapSize[4]  # reset angle
            self.base = Image.new("RGBA", self.base.size, self.transparent)
            # overlay for roomba problem position
            self.roomba_problem = Image.new("RGBA", self.base.size, self.transparent)
            self.show_final_map = False
            self.display_text = None
            self.log.debug("MAP: created new image at start of new run")

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
                self.display_text = (
                    "Battery low: "
                    + str(self.master_state["state"]["reported"]["batPct"])
                    + "%, "
                    + self.display_text
                )
                battery_low = True

        else:
            self.log.warning(
                "MAP: no special handling for state: %s", self.current_state
            )

        if self.base is None:
            self.log.warning("MAP: no image, exiting...")
            return

        if self.display_text is None:
            self.display_text = self.current_state

        if self.show_final_map:  # just display final map - not live
            self.log.debug("MAP: not updating map - Roomba not running")
            return

        if self.debug:
            # debug final map (careful, uses a lot of CPU power!)
            self.draw_final_map()

        # calculate co-ordinates, with 0,0 as center
        old_x_y, x_y, theta = self.offset_coordinates(old_co_ords, new_co_ords)
        roomba_pos = self.get_roomba_pos(x_y)

        self.log.debug(
            "MAP: old x,y: %s new x,y: %s theta: %s roomba pos: %s",
            old_x_y,
            x_y,
            theta,
            roomba_pos,
        )

        # draw lines
        self.draw_vacuum_lines(self.base, old_x_y, x_y, theta)

        # make a blank image for the text and Roomba overlay, initialized to
        # transparent text color
        roomba_sprite = Image.new("RGBA", self.base.size, self.transparent)

        # draw roomba
        self.log.debug("MAP: drawing roomba: pos: %s, theta: %s", roomba_pos, theta)
        if stuck:
            self.log.debug("MAP: Drawing stuck Roomba")
            self.roomba_problem.paste(self.roomba_error_icon, roomba_pos)
        if cancelled:
            self.log.debug("MAP: Drawing cancelled Roomba")
            self.roomba_problem.paste(self.roomba_cancelled_icon, roomba_pos)
        if bin_full:
            self.log.debug("MAP: Drawing full bin")
            self.roomba_problem.paste(self.bin_full_icon, roomba_pos)
        if battery_low:
            self.log.debug("MAP: Drawing low battery Roomba")
            self.roomba_problem.paste(self.roomba_battery_icon, roomba_pos)

        roomba_sprite = self.transparent_paste(
            roomba_sprite, self.roomba_icon.rotate(theta, expand=False), roomba_pos
        )

        # paste dock over roomba_sprite
        if self.dock_icon is not None:
            roomba_sprite = self.transparent_paste(
                roomba_sprite, self.dock_icon, self.dock_position
            )

        # save base lines
        self.base.save(self.mapPath + "/" + self.roombaName + "lines.png", "PNG")
        # save problem overlay
        self.roomba_problem.save(
            self.mapPath + "/" + self.roombaName + "problems.png", "PNG"
        )
        if self.roomOutline or self.auto_rotate:
            # draw room outline (saving results if this is a final map) update
            # x,y and angle if auto_rotate
            self.draw_room_outline(draw_final)
        # merge room outline into base
        if self.roomOutline:
            # if we want to draw the room outline
            out = Image.alpha_composite(self.base, self.room_outline)
        else:
            out = self.base
        # merge roomba lines (trail) with base
        out = Image.alpha_composite(out, roomba_sprite)
        # merge problem location for roomba into out
        out = Image.alpha_composite(out, self.roomba_problem)
        if draw_final and self.auto_rotate:
            # translate image to center it if auto_rotate is on
            self.log.debug(
                "MAP: calculation of center: (%d,%d), "
                "translating final map to center it, x:%d, y:%d "
                "deg: %.2f"
                % (
                    self.cx,
                    self.cy,
                    self.cx - out.size[0] // 2,
                    self.cy - out.size[1] // 2,
                    self.angle,
                )
            )
            out = out.transform(
                out.size,
                Image.AFFINE,
                (1, 0, self.cx - out.size[0] // 2, 0, 1, self.cy - out.size[1] // 2),
            )
        # map is upside down, so rotate 180 degrees, and size to fit
        out_rotated = out.rotate(180 + self.angle, expand=True).resize(self.base.size)
        # save composite image
        self.save_text_and_map_on_whitebg(out_rotated)
        if draw_final:
            self.show_final_map = True  # prevent re-drawing of map until reset

    def save_text_and_map_on_whitebg(self, map):
        # if no map or nothing changed
        if map is None or (
            map == self.previous_map_no_text
            and self.previous_display_text == self.display_text
        ):
            return
        self.map_no_text = map
        self.previous_map_no_text = self.map_no_text
        self.previous_display_text = self.display_text
        self.map_no_text.save(
            self.mapPath + "/" + self.roombaName + "map_notext.png", "PNG"
        )
        final = Image.new("RGBA", self.base.size, (255, 255, 255, 255))  # white
        # paste onto a white background, so it's easy to see
        final = Image.alpha_composite(final, map)
        # draw text
        self.draw_text(final, self.display_text, self.fnt)
        final.save(self.mapPath + "/" + self.roombaName + "_map.png", "PNG")
        # try to avoid other programs reading file while writing it,
        # rename should be atomic.
        os.rename(
            self.mapPath + "/" + self.roombaName + "_map.png",
            self.mapPath + "/" + self.roombaName + "map.png",
        )

    def ScaleRotateTranslate(
        self, image, angle, center=None, new_center=None, scale=None, expand=False
    ):
        """
        experimental - not used yet
        """
        if center is None:
            return image.rotate(angle, expand)
        angle = -angle / 180.0 * math.pi
        nx, ny = x, y = center
        if new_center != center:
            (nx, ny) = new_center
        sx = sy = 1.0
        if scale:
            (sx, sy) = scale
        cosine = math.cos(angle)
        sine = math.sin(angle)
        a = cosine / sx
        b = sine / sx
        c = x - nx * a - ny * b
        d = -sine / sy
        e = cosine / sy
        f = y - nx * d - ny * e
        return image.transform(
            image.size, Image.AFFINE, (a, b, c, d, e, f), resample=Image.BICUBIC
        )

    def match_outlines(self, orig_image, skewed_image):
        orig_image = np.array(orig_image)
        skewed_image = np.array(skewed_image)
        try:
            surf = cv2.xfeatures2d.SURF_create(400)
        except Exception:
            surf = cv2.SIFT(400)
        kp1, des1 = surf.detectAndCompute(orig_image, None)
        kp2, des2 = surf.detectAndCompute(skewed_image, None)

        FLANN_INDEX_KDTREE = 0
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        matches = flann.knnMatch(des1, des2, k=2)

        # store all the good matches as per Lowe's ratio tests.
        good = []
        for m, n in matches:
            if m.distance < 0.7 * n.distance:
                good.append(m)

        MIN_MATCH_COUNT = 10
        if len(good) > MIN_MATCH_COUNT:
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

            # see https://ch.mathworks.com/help/images/examples/find-image-rotation-and-scale-using-automated-feature-matching.html for details
            ss = M[0, 1]
            sc = M[0, 0]
            scale_recovered = math.sqrt(ss * ss + sc * sc)
            theta_recovered = math.atan2(ss, sc) * 180 / math.pi
            self.log.debug(
                "MAP: Calculated scale difference: %.2f, "
                "Calculated rotation difference: %.2f"
                % (scale_recovered, theta_recovered)
            )

            # deskew image
            im_out = cv2.warpPerspective(
                skewed_image,
                np.linalg.inv(M),
                (orig_image.shape[1], orig_image.shape[0]),
            )
            return im_out

        else:
            self.log.warning(
                "MAP: Not enough matches found - %d/%d", len(good), MIN_MATCH_COUNT
            )
            return skewed_image

    def draw_room_outline(self, overwrite=False, colour=(64, 64, 64, 255), width=1):
        """
        draw room outline
        """
        self.log.debug("MAP: checking room outline")
        if HAVE_CV2:
            if self.room_outline_contour is None or overwrite:
                try:
                    self.room_outline_contour = np.load(
                        self.mapPath + "/" + self.roombaName + "room.npy"
                    )
                except IOError as e:
                    self.log.warning("Unable to load room outline: %s, setting to 0", e)
                    self.room_outline_contour = np.array(
                        [(0, 0), (0, 0), (0, 0), (0, 0)], dtype=np.int
                    )

                try:
                    self.log.debug("MAP: openening existing room outline image")
                    self.room_outline = Image.open(
                        self.mapPath + "/" + self.roombaName + "room.png"
                    ).convert("RGBA")
                    if self.room_outline.size != self.base.size:
                        raise IOError("Image is wrong size")
                except IOError as e:
                    self.room_outline = Image.new(
                        "RGBA", self.base.size, self.transparent
                    )
                    self.log.warning(
                        "MAP: room outline image problem: %s: set to New" % e
                    )

            room_outline_area = cv2.contourArea(self.room_outline_contour)
            # edgedata = cv2.add(
            #     np.array(self.base.convert('L'), dtype=np.uint8),
            #     np.array(self.room_outline.convert('L'), dtype=np.uint8))
            edgedata = np.array(self.base.convert("L"))
            # find external contour
            _, contours, _ = self.findContours(
                edgedata, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if contours[0] is None:
                return
            if len(contours[0]) < 5:
                return
            max_area = cv2.contourArea(contours[0])
            # experimental shape matching
            # note cv2.cv.CV_CONTOURS_MATCH_I1 does not exist in CV 3.0,
            # so just use 1
            match = cv2.matchShapes(self.room_outline_contour, contours[0], 1, 0.0)
            self.log.debug("MAP: perimeter/outline match is: %.4f" % match)
            # if match is less than 0.35 - shapes are similar (but if it's 0 -
            # then they are the same shape..) try auto rotating map to fit.
            if 0.35 > match > 0:
                # self.match_outlines(self.room_outline, self.base)
                pass
            if max_area > room_outline_area:
                self.log.debug("MAP: found new outline perimiter")
                self.room_outline_contour = contours[0]
                perimeter = cv2.arcLength(self.room_outline_contour, True)
                outline = Image.new("RGBA", self.base.size, self.transparent)
                edgeimage = np.array(outline)  # make blank RGBA image array
                # self.draw_edges is the max deviation from a line (set to 0.3%)
                # you can fiddle with this
                approx = cv2.approxPolyDP(
                    self.room_outline_contour, self.draw_edges * perimeter, True
                )
                # outline with grey, width 1
                cv2.drawContours(edgeimage, [approx], -1, colour, width)
                self.room_outline = Image.fromarray(edgeimage)

        else:
            if self.room_outline is None or overwrite:
                try:
                    self.log.debug("MAP: openening existing room outline image")
                    self.room_outline = Image.open(
                        self.mapPath + "/" + self.roombaName + "room.png"
                    ).convert("RGBA")
                    if self.room_outline.size != self.base.size:
                        raise IOError("Image is wrong size")
                except IOError as e:
                    self.room_outline = Image.new(
                        "RGBA", self.base.size, self.transparent
                    )
                    self.log.warning(
                        "MAP: room outline image problem: %s: set to New", e
                    )
            edges = ImageOps.invert(self.room_outline.convert("L"))
            edges.paste(self.base)
            edges = edges.convert("L").filter(ImageFilter.SMOOTH_MORE)
            edges = ImageOps.invert(edges.filter(ImageFilter.FIND_EDGES))
            self.room_outline = self.make_transparent(edges, (0, 0, 0, 255))

        if overwrite or self.debug:
            # save room outline
            self.room_outline.save(
                self.mapPath + "/" + self.roombaName + "room.png", "PNG"
            )
            if HAVE_CV2:
                # save room outline contour as numpy array
                np.save(
                    self.mapPath + "/" + self.roombaName + "room.npy",
                    self.room_outline_contour,
                )
            if self.auto_rotate:
                # update outline centre
                self.get_image_parameters(
                    image=self.room_outline,
                    contour=self.room_outline_contour,
                    final=overwrite,
                )
                self.log.debug(
                    "MAP: calculation of center: (%d,%d), "
                    "translating room outline to center it, "
                    "x:%d, y:%d deg: %.2f",
                    self.cx,
                    self.cy,
                    self.cx - self.base.size[0] // 2,
                    self.cy - self.base.size[1] // 2,
                    self.angle,
                )
                # center room outline, same as map.
                self.room_outline = self.room_outline.transform(
                    self.base.size,
                    Image.AFFINE,
                    (
                        1,
                        0,
                        self.cx - self.base.size[0] // 2,
                        0,
                        1,
                        self.cy - self.base.size[1] // 2,
                    ),
                )
            self.log.debug("MAP: Wrote new room outline files")

    def PIL_get_image_parameters(
        self, image=None, start=90, end=0, step=-1, recursion=0
    ):
        """
        updates angle of image, and centre using PIL.
        NOTE: this assumes the floorplan is rectangular! if you live in a
        lighthouse, the angle will not be valid!
        input is PIL image
        """
        if image is not None and HAVE_PIL:
            imbw = image.convert("L")
            max_area = self.base.size[0] * self.base.size[1]
            x_y = (self.base.size[0] // 2, self.base.size[1] // 2)
            angle = self.angle
            div_by_10 = False
            if step >= 10 or step <= -10:
                step /= 10
                div_by_10 = True
            for try_angle in range(start, end, step):
                if div_by_10:
                    try_angle /= 10.0
                # rotate image and resize to fit
                im = imbw.rotate(try_angle, expand=True)
                box = im.getbbox()
                if box is not None:
                    area = (box[2] - box[0]) * (box[3] - box[1])
                    if area < max_area:
                        angle = try_angle
                        x_y = (
                            (box[2] - box[0]) // 2 + box[0],
                            (box[3] - box[1]) // 2 + box[1],
                        )
                        max_area = area

        if recursion >= 1:
            return x_y, angle

        x_y, angle = self.PIL_get_image_parameters(
            image, (angle + 1) * 10, (angle - 1) * 10, -10, recursion + 1
        )

        # self.log.info("MAP: PIL: image center: "
        #               "x:%d, y:%d, angle %.2f" % (x_y[0], x_y[1], angle))
        return x_y, angle

    def get_image_parameters(self, image=None, contour=None, final=False):
        """
        updates angle of image, and centre using cv2 or PIL.
        NOTE: this assumes the floorplan is rectangular! if you live in a
        lighthouse, the angle will not be valid!
        input is cv2 contour or PIL image
        routines find the minnimum area rectangle that fits the image outline
        """
        if contour is not None and HAVE_CV2:
            # find minnimum area rectangle that fits
            # returns (x,y), (width, height), theta - where (x,y) is the center
            x_y, l_w, angle = cv2.minAreaRect(contour)

        elif image is not None and HAVE_PIL:
            x_y, angle = self.PIL_get_image_parameters(image)

        else:
            return

        if angle < self.angle - 45:
            angle += 90
        if angle > 45 - self.angle:
            angle -= 90

        if final:
            self.cx = x_y[0]
            self.cy = x_y[1]
            self.angle = angle
        self.log.debug(
            "MAP: image center: x:%d, y:%d, angle %.2f", x_y[0], x_y[1], angle
        )

    def angle_between(self, p1, p2):
        """
        clockwise angle between two points in degrees
        """
        if HAVE_CV2:
            ang1 = np.arctan2(*p1[::-1])
            ang2 = np.arctan2(*p2[::-1])
            return np.rad2deg((ang1 - ang2) % (2 * np.pi))
        else:
            side1 = math.sqrt(((p1[0] - p2[0]) ** 2))
            side2 = math.sqrt(((p1[1] - p2[1]) ** 2))
            return math.degrees(math.atan(side2 / side1))

    def findContours(self, image, mode, method):
        """
        Version independent find contours routine. Works with OpenCV 2 or 3.
        Returns modified image (with contours applied), contours list, hierarchy
        """
        ver = int(cv2.__version__.split(".")[0])
        im = image.copy()
        if ver == 2:
            contours, hierarchy = cv2.findContours(im, mode, method)
            return im, contours, hierarchy
        else:
            im_cont, contours, hierarchy = cv2.findContours(im, mode, method)
            return im_cont, contours, hierarchy

    def draw_final_map(self, overwrite=False):
        """
        draw map with outlines at end of mission. Called when mission has
        finished and Roomba has docked
        """
        merge = Image.new("RGBA", self.base.size, self.transparent)
        if HAVE_CV2:
            # NOTE: this is CPU intensive!
            edgedata = np.array(self.base.convert("L"), dtype=np.uint8)
            # find all contours
            _, contours, _ = self.findContours(
                edgedata, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
            )
            # zero edge data for later use
            edgedata.fill(0)
            max_perimeter = 0
            max_contour = None
            for cnt in contours:
                perimeter = cv2.arcLength(cnt, True)
                if perimeter >= max_perimeter:
                    max_contour = cnt  # get the contour with maximum length
                    max_perimeter = perimeter
            if max_contour is None:
                return
            if len(max_contour) < 5:
                return
            try:
                contours.remove(max_contour)  # remove max contour from list
            except ValueError:
                self.log.warning("MAP: unable to remove contour")

            mask = np.full(edgedata.shape, 255, dtype=np.uint8)  # white
            # create mask (of other contours) in black
            cv2.drawContours(mask, contours, -1, 0, -1)

            # self.draw_edges is the max deviation from a line
            # you can fiddle with this in enable_map
            approx = cv2.approxPolyDP(
                max_contour, self.draw_edges * max_perimeter, True
            )

            bgimage = np.array(merge)  # make blank RGBA image array
            # draw contour and fill with "lawngreen"
            cv2.drawContours(bgimage, [approx], -1, (124, 252, 0, 255), -1)
            # mask image with internal contours
            bgimage = cv2.bitwise_and(bgimage, bgimage, mask=mask)
            # not dure if you really need this - uncomment if you want the
            # area outlined.
            # draw longest contour aproximated to lines (in black), width 1
            cv2.drawContours(edgedata, [approx], -1, (255), 1)

            outline = Image.fromarray(edgedata)  # outline
            base = Image.fromarray(bgimage)  # filled background image
        else:
            base = self.base.filter(ImageFilter.SMOOTH_MORE)
            # draw edges at end of mission
            outline = base.convert("L").filter(ImageFilter.FIND_EDGES)
            # outline = ImageChops.subtract(
            #     base.convert('L').filter(ImageFilter.EDGE_ENHANCE),
            #     base.convert('L'))

        edges = ImageOps.invert(outline)
        edges = self.make_transparent(edges, (0, 0, 0, 255))
        if self.debug:
            edges.save(self.mapPath + "/" + self.roombaName + "edges.png", "PNG")
        merge = Image.alpha_composite(merge, base)
        merge = Image.alpha_composite(merge, edges)
        if overwrite:
            self.log.debug("MAP: Drawing final map")
            self.last_completed_time = time.time()
            self.base = merge

        if self.debug:
            merge_rotated = merge.rotate(180 + self.angle, expand=True)
            merge_rotated.save(
                self.mapPath + "/" + self.roombaName + "final_map.png", "PNG"
            )
