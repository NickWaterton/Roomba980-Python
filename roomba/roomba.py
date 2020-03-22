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

from collections.abc import Mapping
from collections import OrderedDict
from roomba.mqttclient import RoombaMQTTClient
import datetime
import json
import logging
import threading
import time

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
        continuous=True,
        delay=1,
        cert_name=None
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
        self.log = logging.getLogger(__name__)
        self.address = address
        self.continuous = continuous
        if self.continuous:
            self.log.debug("CONTINUOUS connection")
        else:
            self.log.debug("PERIODIC connection")

        self.stop_connection = False
        self.periodic_connection_running = False
        self.topic = '#'
        self.mqttc = None
        self.brokerFeedback = ''
        self.exclude = ''
        self.delay = delay
        self.periodic_connection_duration = 10
        self.roomba_connected = False
        self.indent = 0
        self.master_indent = 0
        self.raw = False
        self.co_ords = {"x": 0, "y": 0, "theta": 180}
        self.cleanMissionStatus_phase = ''
        self.previous_cleanMissionStatus_phase = ''
        self.current_state = None
        self.bin_full = False
        self.master_state = {}  # all info from roomba stored here
        self.time = time.time()
        self.update_seconds = 300  # update with all values every 5 minutes
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
        self.log.info("Connected to Roomba %s", self.address)
        if rc == 0:
            self.roomba_connected = True
            self.client.subscribe(self.topic)
        else:
            self.log.error("Roomba Connected with result code %s", str(rc))
            self.log.error("Please make sure your blid and password are correct %s", self.address)
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

        self.log.debug("Received Roomba Data %s: %s, %s", self.address, str(msg.topic), str(msg.payload))

        if self.raw:
            self.publish(msg.topic, msg.payload)
        else:
            self.decode_topics(json_data)

        # default every 5 minutes
        if time.time() - self.time > self.update_seconds:
            self.log.debug("Publishing master_state %s", self.address)
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
                self.address,
            )
        else:
            self.log.info("Disconnected from Roomba %s", self.address)

    def send_command(self, command):
        self.log.debug("Send command: %s", command)
        roomba_command = OrderedDict()
        roomba_command["command"] = command
        roomba_command["time"] = self.to_timestamp(datetime.datetime.now())
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

    def to_timestamp(self, dt):
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
        for k, v in merge_dct.items():
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

        json_data = None
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
        for k, v in state.items():
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
                            for ki, vi in i.items():
                                newlist.append((str(ki), vi))
                        else:
                            if isinstance(i, str):
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
                        error_message = self._ErrorMessages[v]
                    except KeyError as e:
                        self.log.warning("Error looking up Roomba error " "message: %s", e)
                        error_message = "Unknown Error number: %d" % v
                    self.publish("error_message", error_message)
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
