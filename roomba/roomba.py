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
from datetime import datetime
import json
import logging
import threading
import time
from roomba.const import ROOMBA_ERROR_MESSAGES, ROOMBA_STATES

MAX_CONNECTION_RETRIES = 3


class RoombaConnectionError(Exception):
    pass


class RoombaInfo:
    hostname = None
    firmware = None
    ip = None
    mac = None
    robot_name = None
    sku = None
    capabilities = None
    blid = None
    password = None

    def __init__(self, hostname, robot_name, ip, mac, firmware, sku, capabilities):
        self.hostname = hostname
        self.firmware = firmware
        self.ip = ip
        self.mac = mac
        self.robot_name = robot_name
        self.sku = sku
        self.capabilities = capabilities
        self.blid = hostname.split('-')[1]

    def __str__(self) -> str:
        return ', '.join(['{key}={value}'.format(key=key, value=self.__dict__.get(key)) for key in self.__dict__])

    def __hash__(self) -> int:
        return hash(self.mac)

    def __eq__(self, o: object) -> bool:
        return isinstance(o, RoombaInfo) and self.mac == o.mac


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

    def __init__(
        self,
        address=None,
        blid=None,
        password=None,
        continuous=True,
        delay=1
    ):
        """
        Roomba client initialization
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
        self.exclude = ''
        self.delay = delay
        self.periodic_connection_duration = 10
        self.roomba_connected = False
        self.indent = 0
        self.master_indent = 0
        self.co_ords = {"x": 0, "y": 0, "theta": 180}
        self.cleanMissionStatus_phase = ''
        self.previous_cleanMissionStatus_phase = ''
        self.current_state = None
        self.bin_full = False
        self.master_state = {}  # all info from roomba stored here
        self.time = time.time()
        self.update_seconds = 300  # update with all values every 5 minutes
        self.client = self._get_client(address, blid, password)
        self._thread = threading.Thread(target=self.periodic_connection)
        self.on_message_callbacks = []
        self.error_code = None
        self.error_message = None
        self.client_error = None

    def register_on_message_callback(self, callback):
        self.on_message_callbacks.append(callback)

    def _get_client(self, address, blid, password):
        client = RoombaMQTTClient(
            address=address,
            blid=blid,
            password=password)
        client.set_on_message(self.on_message)
        client.set_on_connect(self.on_connect)
        client.set_on_disconnect(self.on_disconnect)
        return client

    def connect(self):
        if self.roomba_connected or self.periodic_connection_running:
            return

        if self.continuous:
            if not self._connect():
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

    def on_connect(self, error):
        self.log.info("Connecting to Roomba %s", self.address)
        self.client_error = error
        if error is not None:
            self.log.error("Roomba %s connection error, code %s", self.address, error)
            return

        self.roomba_connected = True
        self.client.subscribe(self.topic)

    def on_disconnect(self, error):
        self.roomba_connected = False
        self.client_error = error
        if error is not None:
            self.log.warning("Unexpectedly disconnected from Roomba %s, code %s", self.address, error)
            return

        self.log.info("Disconnected from Roomba %s", self.address)

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

        self.decode_topics(json_data)

        # default every 5 minutes
        if time.time() - self.time > self.update_seconds:
            self.log.debug("Publishing master_state %s", self.address)
            self.decode_topics(self.master_state)  # publish all values
            self.time = time.time()

        # call the callback functions
        for callback in self.on_message_callbacks:
            callback(json_data)

    def send_command(self, command, params=None):
        if params is None:
            params = {}

        self.log.debug("Send command: %s", command)
        roomba_command = {
            "command": command,
            "time": int(datetime.timestamp(datetime.now())),
            "initiator": "localApp"
        }
        roomba_command.update(params)

        str_command = json.dumps(roomba_command)
        self.log.debug("Publishing Roomba Command : %s", str_command)
        self.client.publish("cmd", str_command)

    def set_preference(self, preference, setting):
        self.log.debug("Set preference: %s, %s", preference, setting)
        val = setting
        # Parse boolean string
        if isinstance(setting, str):
            if setting.lower() == "true":
                val = True
            elif setting.lower() == "false":
                val = False
        tmp = {preference: val}
        roomba_command = {"state": tmp}
        str_command = json.dumps(roomba_command)
        self.log.debug("Publishing Roomba Setting : %s" % str_command)
        self.client.publish("delta", str_command)

    def publish(self, topic, message):
        pass

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
        return formatted_data, dict(json_data)

    def decode_topics(self, state, prefix=None):
        """
        decode json data dict, and publish as individual topics to
        brokerFeedback/topic the keys are concatinated with _ to make one unique
        topic name strings are expressely converted to strings to avoid unicode
        representations
        """
        for key, value in state.items():
            if isinstance(value, dict):
                if prefix is None:
                    self.decode_topics(value, key)
                else:
                    self.decode_topics(value, prefix + "_" + key)
            else:
                if isinstance(value, list):
                    newlist = []
                    for i in value:
                        if isinstance(i, dict):
                            for ki, vi in i.items():
                                newlist.append((str(ki), vi))
                        else:
                            if isinstance(i, str):
                                i = str(i)
                            newlist.append(i)
                    value = newlist
                if prefix is not None:
                    key = prefix + "_" + key
                # all data starts with this, so it's redundant
                key = key.replace("state_reported_", "")
                # save variables for drawing map
                if key == "pose_theta":
                    self.co_ords["theta"] = value
                if key == "pose_point_x":  # x and y are reversed...
                    self.co_ords["y"] = value
                if key == "pose_point_y":
                    self.co_ords["x"] = value
                if key == "bin_full":
                    self.bin_full = value
                if key == "cleanMissionStatus_error":
                    try:
                        self.error_code = value
                        self.error_message = ROOMBA_ERROR_MESSAGES[value]
                    except KeyError as e:
                        self.log.warning("Error looking up Roomba error message: %s", e)
                        self.error_message = "Unknown Error number: %s" % value
                    self.publish("error_message", self.error_message)
                if key == "cleanMissionStatus_phase":
                    self.previous_cleanMissionStatus_phase = (
                        self.cleanMissionStatus_phase
                    )
                    self.cleanMissionStatus_phase = value

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

        try:
            if (
                self.master_state["state"]["reported"]["cleanMissionStatus"]["mssnM"]
                == "none"
                and self.cleanMissionStatus_phase == "charge"
                and (self.current_state == ROOMBA_STATES["pause"] or self.current_state == ROOMBA_STATES["recharge"])
            ):
                self.current_state = ROOMBA_STATES["cancelled"]
        except KeyError:
            pass

        if (
            self.current_state == ROOMBA_STATES["charge"]
            and self.cleanMissionStatus_phase == "run"
        ):
            self.current_state = ROOMBA_STATES["new"]
        elif (
            self.current_state == ROOMBA_STATES["run"]
            and self.cleanMissionStatus_phase == "hmMidMsn"
        ):
            self.current_state = ROOMBA_STATES["dock"]
        elif (
            self.current_state == ROOMBA_STATES["dock"]
            and self.cleanMissionStatus_phase == "charge"
        ):
            self.current_state = ROOMBA_STATES["recharge"]
        elif (
            self.current_state == ROOMBA_STATES["recharge"]
            and self.cleanMissionStatus_phase == "charge"
            and self.bin_full
        ):
            self.current_state = ROOMBA_STATES["pause"]
        elif (
            self.current_state == ROOMBA_STATES["run"]
            and self.cleanMissionStatus_phase == "charge"
        ):
            self.current_state = ROOMBA_STATES["recharge"]
        elif (
            self.current_state == ROOMBA_STATES["recharge"]
            and self.cleanMissionStatus_phase == "run"
        ):
            self.current_state = ROOMBA_STATES["pause"]
        elif (
            self.current_state == ROOMBA_STATES["pause"]
            and self.cleanMissionStatus_phase == "charge"
        ):
            self.current_state = ROOMBA_STATES["pause"]
            # so that we will draw map and can update recharge time
            current_mission = None
        elif (
            self.current_state == ROOMBA_STATES["charge"]
            and self.cleanMissionStatus_phase == "charge"
        ):
            # so that we will draw map and can update charge status
            current_mission = None
        elif (
            self.current_state == ROOMBA_STATES["stop"]
            or self.current_state == ROOMBA_STATES["pause"]
        ) and self.cleanMissionStatus_phase == "hmUsrDock":
            self.current_state = ROOMBA_STATES["cancelled"]
        elif (
            self.current_state == ROOMBA_STATES["hmUsrDock"]
            or self.current_state == ROOMBA_STATES["cancelled"]
        ) and self.cleanMissionStatus_phase == "charge":
            self.current_state = ROOMBA_STATES["dockend"]
        elif (
            self.current_state == ROOMBA_STATES["hmPostMsn"]
            and self.cleanMissionStatus_phase == "charge"
        ):
            self.current_state = ROOMBA_STATES["dockend"]
        elif (
            self.current_state == ROOMBA_STATES["dockend"]
            and self.cleanMissionStatus_phase == "charge"
        ):
            self.current_state = ROOMBA_STATES["charge"]

        else:
            self.current_state = ROOMBA_STATES[self.cleanMissionStatus_phase]

        if new_state is not None:
            self.current_state = ROOMBA_STATES[new_state]
            self.log.debug("Current state: %s", self.current_state)

        if self.current_state != current_mission:
            self.log.debug("State updated to: %s", self.current_state)
