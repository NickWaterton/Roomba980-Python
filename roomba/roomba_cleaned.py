#!/usr/bin/env python
# coding: utf-8

"""
Program to connect to control wifi-enabled Roomba vacuum cleaners
"""

from __future__ import print_function
from __future__ import absolute_import
from ast import literal_eval
from collections import OrderedDict, Mapping
import datetime
import json
import logging
import os
import socket
import ssl
import sys
import threading
import time

import paho.mqtt.client as mqtt
import six

from roomba.password import Password


LOGGER = logging.getLogger(__name__)


class RoombaConnectionError(Exception):
    pass


class Roomba(object):
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
    This is not needed if the forward to mqtt option is used, as the events
    will be decoded and published on the designated mqtt client topic.
    """

    STATES = {
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

    # From http://homesupport.irobot.com/app/answers/detail/a_id/9024/~/roomba-900-error-messages   # noqa: E501
    ERROR_MESSAGES = {
        0: "None",
        1: "Roomba is stuck with its left or right wheel hanging down.",
        2: "The debris extractors can't turn.",
        5: "The left or right wheel is stuck.",
        6: "The cliff sensors are dirty, it is hanging over a drop, "
        "or it is stuck on a dark surface.",
        8: "The fan is stuck or its filter is clogged.",
        9: "The bumper is stuck, or the bumper sensor is dirty.",
        10: "The left or right wheel is not moving.",
        11: "Roomba has an internal error.",
        14: "The bin has a bad connection to the robot.",
        15: "Roomba has an internal error.",
        16: "Roomba has started while moving or at an angle, or was bumped "
        "while running.",
        17: "The cleaning job is incomplete.",
        18: "Roomba cannot return to the Home Base or starting position.",
    }

    def __init__(
        self,
        address=None,
        blid=None,
        password=None,
        topic="#",
        continuous=True,
        clean=False,
        cert="",
        name="",
        file="./config.ini",
        debug=False,
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

        self.debug = debug
        self.address = address
        self.cert = cert
        if not cert:
            self.cert = "/etc/ssl/certs/ca-certificates.crt"
        self.continuous = continuous
        if self.continuous:
            LOGGER.debug("CONTINUOUS connection")
        else:
            LOGGER.debug("PERIODIC connection")
        # set the following to True to enable pretty printing of json data
        self.pretty_print = False
        self.stop_connection = False
        self.periodic_connection_running = False
        self.clean = clean
        self.port = 8883
        self.blid = blid
        self.password = password
        self.name = name
        self.topic = topic
        self.mqttc = None
        self.exclude = ""
        self.delay = 1
        self.connected = False
        self.indent = 0
        self.master_indent = 0
        self.raw = False
        self.clean_mission_status_phase = ""
        self.previous_clean_mission_status_phase = ""
        self.current_state = None
        self.last_completed_time = None
        self.bin_full = False
        self.master_state = {}
        self.time = time.time()
        self.update_interval = 300  # update with all values every 5 minutes
        self.client = None
        self._thread = None

    def setup_client(self):
        if self.client is None:
            self.client = mqtt.Client(
                client_id=self.blid, clean_session=self.clean, protocol=mqtt.MQTTv311
            )
            # Assign event callbacks
            self.client.on_message = self.on_message
            self.client.on_connect = self.on_connect
            self.client.on_publish = self.on_publish
            self.client.on_subscribe = self.on_subscribe
            self.client.on_disconnect = self.on_disconnect

            # Uncomment to enable debug messages
            # client.on_log = self.on_log

            # set TLS, self.cert is required by paho-mqtt, even if the
            # certificate is not used...
            # but v1.3 changes all this, so have to do the following:

            LOGGER.debug("Setting up TLS")
            try:
                self.client.tls_set(
                    self.cert, cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLSv1
                )
            except ValueError:  # try V1.3 version
                self.log.warning("TLS Setting failed - trying 1.3 version")
                self.client._ssl_context = None
                context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
                context.verify_mode = ssl.CERT_NONE
                context.load_default_certs()
                self.client.tls_set_context(context)

            # disables peer verification
            self.client.tls_insecure_set(True)
            self.client.username_pw_set(self.blid, self.password)
            # Disable peer verification
            self.client.tls_insecure_set(True)
            self.client.username_pw_set(self.blid, self.password)
            return True
        return False

    def connect(self):
        if self.address is None or self.blid is None or self.password is None:
            LOGGER.critical(
                "Invalid address, blid, or password! All these " "must be specified!"
            )
            sys.exit(1)
        if self.connected or self.periodic_connection_running:
            return

        if self.continuous:
            if not self._connect():
                if self.mqttc is not None:
                    self.mqttc.disconnect()
                sys.exit(1)
        else:
            self._thread = threading.Thread(target=self.periodic_connection)
            self._thread.daemon = True
            self._thread.start()

        self.time = time.time()  # save connection time

    def _connect(self, count=0, new_connection=False):
        max_retries = 3
        try:
            if self.client is None or new_connection:
                LOGGER.info("Connecting to %s", self.name)
                self.setup_client()
                self.client.connect(self.address, self.port, 60)
            else:
                LOGGER.info("Attempting to reconnect to %s", self.name)
                self.client.loop_stop()
                self.client.reconnect()
            self.client.loop_start()
            return True
        except Exception as e:
            LOGGER.error("Error: %s " % e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            # LOGGER.error("Exception: %s" % exc_type)
            # if e[0] == 111: #errno.ECONNREFUSED - does not work with
            # python 3.0 so...
            if exc_type == socket.error or exc_type == ConnectionRefusedError:
                count += 1
                if count <= max_retries:
                    LOGGER.debug("Attempting connection #%d" % count)
                    time.sleep(1)
                    self._connect(count, True)
        if count >= max_retries:
            LOGGER.error("Unable to connect to %s", self.address)
            raise RoombaConnectionError(
                "Unable to connect to Roomba at {}".format(self.address)
            )
        return False

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
                time.sleep(self.delay)
                self.client.disconnect()
            time.sleep(self.delay)

        self.client.disconnect()
        self.periodic_connection_running = False

    def on_connect(self, client, userdata, flags, rc):
        LOGGER.info("Connected to Roomba %s", self.name)
        if rc == 0:
            self.connected = True
            self.client.subscribe(self.topic)
        else:
            LOGGER.error("Roomba Connected with result code %s", rc)
            LOGGER.error(
                "Please make sure your blid and password are " "correct %s", self.name
            )
            raise RoombaConnectionError(
                "Roomba connection failed. Please " "check the credentials."
            )
            if self.mqttc is not None:
                self.mqttc.disconnect()
            sys.exit(1)

    def on_message(self, mosq, obj, msg):
        # print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
        if self.exclude != "":
            if self.exclude in msg.topic:
                return

        if self.indent == 0:
            self.master_indent = max(self.master_indent, len(msg.topic))

        log_string, json_data = self.decode_payload(msg.topic, msg.payload)
        self.dict_merge(self.master_state, json_data)

        if self.pretty_print:
            LOGGER.debug(
                "%-{:d}s : %s".format(self.master_indent), msg.topic, log_string
            )
        else:
            LOGGER.debug(
                "Received Roomba Data %s: %s, %s",
                self.name,
                str(msg.topic),
                str(msg.payload),
            )

        if self.raw:
            self.publish(msg.topic, msg.payload)
        else:
            self.decode_topics(json_data)

        # Default to every 5 minutes
        if time.time() - self.time > self.update_interval:
            LOGGER.debug("Publishing master_state %s", self.name)
            self.decode_topics(self.master_state)  # publish all values
            self.time = time.time()

    def on_publish(self, mosq, obj, mid):
        pass

    def on_subscribe(self, mosq, obj, mid, granted_qos):
        LOGGER.debug("Subscribed: %s %s", str(mid), str(granted_qos))

    def on_disconnect(self, mosq, obj, rc):
        self.connected = False
        if rc != 0:
            LOGGER.warning(
                "Unexpectedly disconnected from Roomba %s! " "- reconnecting", self.name
            )
        else:
            LOGGER.info("Disconnected from Roomba %s", self.name)

    def on_log(self, mosq, obj, level, string):
        LOGGER.debug(string)

    def set_mqtt_client(self, mqttc=None, brokerFeedback=""):
        self.mqttc = mqttc
        if self.mqttc is not None:
            if self.name != "":
                self.brokerFeedback = brokerFeedback + "/" + self.name
            else:
                self.brokerFeedback = brokerFeedback

    def send_command(self, command):
        LOGGER.debug("Send command: %s", command)
        command = OrderedDict()
        command["command"] = command
        # command["time"] = self.totimestamp(datetime.datetime.now())
        command["time"] = int(time.time())  # self.totimestamp(datetime.datetime.now())
        command["initiator"] = "localApp"
        json_cmd = json.dumps(command)
        LOGGER.debug("Publishing Roomba Command : %s", json_cmd)
        self.client.publish("cmd", json_cmd)

    def set_preference(self, preference, setting):
        LOGGER.debug("Set preference: %s, %s", preference, setting)
        val = False
        if setting.lower() == "true":
            val = True
        tmp = {preference: val}
        command = {"state": tmp}
        json_cmd = json.dumps(command)
        LOGGER.debug("Publishing Roomba Setting : %s", json_cmd)
        self.client.publish("delta", json_cmd)

    def publish(self, topic, message):
        if self.mqttc is not None and message is not None:
            LOGGER.debug(
                "Publishing item: %s: %s", (self.brokerFeedback + "/" + topic, message)
            )
            self.mqttc.publish(self.brokerFeedback + "/" + topic, message)

    def set_options(self, raw=False, indent=0, pretty_print=False):
        self.raw = raw
        self.indent = indent
        self.pretty_print = pretty_print
        if self.raw:
            LOGGER.debug("Posting RAW data")
        else:
            LOGGER.debug("Posting DECODED data")

    def dict_merge(self, dct, merge_dct):
        """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead
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

            formatted_data = "Decoded JSON: \n%s" % (json_data_string)

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
                            for key, val in six.iteritems(i):
                                newlist.append((str(key), val))
                        else:
                            if isinstance(i, six.string_types):
                                i = str(i)
                            newlist.append(i)
                    v = newlist
                if prefix is not None:
                    k = prefix + "_" + k
                # all data starts with this, so it's redundant
                k = k.replace("state_reported_", "")
                if k == "bin_full":
                    self.bin_full = v
                if k == "cleanMissionStatus_error":
                    try:
                        self.error_message = self.ERROR_MESSAGES[v]
                    except KeyError as err:
                        LOGGER.warning(
                            "Error looking up Roomba error " "message: %s", err
                        )
                        self.error_message = "Unknown Error: {}".format(v)
                    self.publish("error_message", self.error_message)
                if k == "clean_mission_status_phase":
                    self.previous_clean_mission_status_phase = (
                        self.clean_mission_status_phase
                    )
                    self.clean_mission_status_phase = v

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
        #    self.current_state = self.STATES["recharge"]

        #  deal with "bin full" timeout on mission
        try:
            if (
                self.master_state["state"]["reported"]["cleanMissionStatus"]["mssnM"]
                == "none"
                and self.clean_mission_status_phase == "charge"
                and (
                    self.current_state == self.STATES["pause"]
                    or self.current_state == self.STATES["recharge"]
                )
            ):
                self.current_state = self.STATES["cancelled"]
        except KeyError:
            pass

        if (
            self.current_state == self.STATES["charge"]
            and self.clean_mission_status_phase == "run"
        ):
            self.current_state = self.STATES["new"]
        elif (
            self.current_state == self.STATES["run"]
            and self.clean_mission_status_phase == "hmMidMsn"
        ):
            self.current_state = self.STATES["dock"]
        elif (
            self.current_state == self.STATES["dock"]
            and self.clean_mission_status_phase == "charge"
        ):
            self.current_state = self.STATES["recharge"]
        elif (
            self.current_state == self.STATES["recharge"]
            and self.clean_mission_status_phase == "charge"
            and self.bin_full
        ):
            self.current_state = self.STATES["pause"]
        elif (
            self.current_state == self.STATES["run"]
            and self.clean_mission_status_phase == "charge"
        ):
            self.current_state = self.STATES["recharge"]
        elif (
            self.current_state == self.STATES["recharge"]
            and self.clean_mission_status_phase == "run"
        ):
            self.current_state = self.STATES["pause"]
        elif (
            self.current_state == self.STATES["pause"]
            and self.clean_mission_status_phase == "charge"
        ):
            self.current_state = self.STATES["pause"]
            # so that we will draw map and can update recharge time
            current_mission = None
        elif (
            self.current_state == self.STATES["charge"]
            and self.clean_mission_status_phase == "charge"
        ):
            # so that we will draw map and can update charge status
            current_mission = None
        elif (
            self.current_state == self.STATES["stop"]
            or self.current_state == self.STATES["pause"]
        ) and self.clean_mission_status_phase == "hmUsrDock":
            self.current_state = self.STATES["cancelled"]
        elif (
            self.current_state == self.STATES["hmUsrDock"]
            or self.current_state == self.STATES["cancelled"]
        ) and self.clean_mission_status_phase == "charge":
            self.current_state = self.STATES["dockend"]
        elif (
            self.current_state == self.STATES["hmPostMsn"]
            and self.clean_mission_status_phase == "charge"
        ):
            self.current_state = self.STATES["dockend"]
        elif (
            self.current_state == self.STATES["dockend"]
            and self.clean_mission_status_phase == "charge"
        ):
            self.current_state = self.STATES["charge"]
        else:
            self.current_state = self.STATES[self.clean_mission_status_phase]

        if new_state is not None:
            self.current_state = self.STATES[new_state]
            LOGGER.debug("Current state: %s", self.current_state)

        if self.current_state != current_mission:
            LOGGER.debug("State updated to: %s", self.current_state)

        self.publish("state", self.current_state)
