#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from ast import literal_eval
from logging.handlers import RotatingFileHandler
import sys
if sys.version_info[0] < 3 or (sys.version_info[0] == 3 and sys.version_info[1] < 5):  #added for python 2.7 and < 3.4 fix NW 15/9/2017
    import roomba
    try:
        from roomba import Password
    except ImportError:
        from password  import Password
else:
    from roomba import roomba
    try:
        from roomba.password import Password
    except ImportError:
        from password  import Password
import argparse
import json
import logging
import os
import six
import socket
import time
# Import trickery
global HAVE_CV2
global HAVE_MQTT
global HAVE_PIL
HAVE_CV2 = HAVE_MQTT = HAVE_PIL = False #fix for if neither PIL or OPENCV is installed (RPI versions) NW 3/2/2018
try:
    import configparser
except:
    from six.moves import configparser
try:
    import paho.mqtt.client as mqtt
    HAVE_MQTT = True
except ImportError:
    print("paho mqtt client not found")
try:
    import cv2
    HAVE_CV2 = True
except ImportError:
    print("CV or numpy module not found, falling back to PIL")

# NOTE: MUST use Pillow Pillow 4.1.1 to avoid some horrible memory leaks in the
# text handling!
try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    print("PIL module not found, maps are disabled")

def parse_args():
    default_icon_path = os.path.join(os.path.dirname(__file__), 'res')
    #-------- Command Line -----------------
    parser = argparse.ArgumentParser(
        description='Forward MQTT data from Roomba 980 to local MQTT broker')
    parser.add_argument(
        '-f', '--configfile',
        action='store',
        type=str,
        default="./config.ini",
        help='config file name (default: ./config.ini)')
    parser.add_argument(
        '-n', '--roombaName',
        action='store',
        type=str,
        default="", help='optional Roomba name (default: "")')
    parser.add_argument(
        '-t', '--topic',
        action='store',
        type=str,
        default="#",
        help='Roomba MQTT Topic to subscribe to (can use wildcards # and '
             '+ default: #)')
    parser.add_argument(
        '-T', '--brokerFeedback',
        action='store',
        type=str,
        default="/roomba/feedback",
        help='Topic on broker to publish feedback to (default: '
             '/roomba/feedback</name>)')
    parser.add_argument(
        '-C', '--brokerCommand',
        action='store',
        type=str,
        default="/roomba/command",
        help='Topic on broker to publish commands to (default: '
             '/roomba/command</name>)')
    parser.add_argument(
        '-S', '--brokerSetting',
        action='store',
        type=str,
        default="/roomba/setting",
        help='Topic on broker to publish settings to (default: '
             '/roomba/setting</name>)')
    parser.add_argument(
        '-b', '--broker',
        action='store',
        type=str,
        default=None,
        help='ipaddress of MQTT broker (default: None)')
    parser.add_argument(
        '-p', '--port',
        action='store',
        type=int,
        default=1883,
        help='MQTT broker port number (default: 1883)')
    parser.add_argument(
        '-U', '--user',
        action='store',
        type=str,
        default=None,
        help='MQTT broker user name (default: None)')
    parser.add_argument(
        '-P', '--password',
        action='store',
        type=str,
        default=None,
        help='MQTT broker password (default: None)')
    parser.add_argument(
        '-R', '--roombaIP',
        action='store',
        type=str,
        default=None,
        help='ipaddress of Roomba 980 (default: None)')
    parser.add_argument(
        '-u', '--blid',
        action='store',
        type=str,
        default=None,
        help='Roomba 980 blid (default: None)')
    parser.add_argument(
        '-w', '--roombaPassword',
        action='store',
        type=str,
        default=None,
        help='Roomba 980 password (default: None)')
    parser.add_argument(
        '-i', '--indent',
        action='store',
        type=int,
        default=0,
        help='Default indentation=auto')
    parser.add_argument(
        '-l', '--log',
        action='store',
        type=str,
        default="./Roomba.log",
        help='path/name of log file (default: ./Roomba.log)')
    parser.add_argument(
        '-e', '--echo',
        action='store_false',
        default = True,
        help='Echo to Console (default: True)')
    parser.add_argument(
        '-D', '--debug',
        action='store_true',
        default = False,
        help='debug mode')
    parser.add_argument(
        '-r', '--raw',
        action='store_true',
        default = False,
        help='Output raw data to mqtt, no decoding of json data')
    parser.add_argument(
        '-j', '--pretty_print',
        action='store_true',
        default = False,
        help='pretty print json in logs')
    parser.add_argument(
        '-c','--continuous',
        action='store_false',
        default = True,
        help='Continuous connection to Roomba (default: True)')
    parser.add_argument(
        '-d', '--delay',
        action='store',
        type=int,
        default=1000,
        help='Disconnect period for non-continuous connection (default: '
             '1000ms)')
    parser.add_argument(
        '-m', '--drawmap',
        action='store_false',
        default = True,
        help='Draw Roomba cleaning map (default: True)')
    parser.add_argument(
        '-M', '--mapPath',
        action='store',
        type=str,
        default=".",
        help='Location to store maps to (default: .)')
    parser.add_argument(
        '-s', '--mapSize',
        action='store',
        type=str,
        default="(800,1500,0,0,0,0)",
        help='Map Size, Dock offset and skew for the map. (800,1500) is the '
             'size, (0,0) is the dock location, in the center of the map, 0 '
             'is the rotation of the map, 0 is the rotation of the roomba. '
             'Use single quotes around the string. (default: '
             '"(800,1500,0,0,0,0)")')
    parser.add_argument(
        '-I', '--iconPath',
        action='store',
        type=str,
        default=default_icon_path,
        help='location of icons. (default: "./")')
    parser.add_argument(
        '-o', '--roomOutline',
        action='store_false',
        default = True,
        help='Draw room outline (default: True)')
    parser.add_argument(
        '-x', '--exclude',
        action='store',type=str, default="", help='Exclude topics that have this in them (default: "")')
    parser.add_argument(
        '--cert',
        action='store',
        type=str,
        default='/etc/ssl/certs/ca-certificates.crt',
        help='Set the certificate to use for MQTT communication with the Roomba')
    parser.add_argument(
        '--version',
        action='version',
        version="%(prog)s ({})".format(roomba.__version__),
        help='Display version of this program')
    return parser.parse_args()

def main():

    #----------- Local Routines ------------

    def broker_on_connect(client, userdata, flags, rc):
        log.debug("Broker Connected with result code " + str(rc))
        #subscribe to roomba feedback, if there is more than one roomba, the
        # roombaName is added to the topic to subscribe to
        if rc == 0:
            if brokerCommand != "":
                if len(roombas) == 1:
                    mqttc.subscribe(brokerCommand)
                else:
                    for myroomba in roomba_list:
                        mqttc.subscribe(
                            brokerCommand + "/" + myroomba.roombaName)
            if brokerSetting != "":
                if len(roombas) == 1:
                    mqttc.subscribe(brokerSetting)
                else:
                    for myroomba in roomba_list:
                        mqttc.subscribe(
                            brokerSetting + "/" + myroomba.roombaName)

    def broker_on_message(mosq, obj, msg):
        # publish to roomba, if there is more than one roomba, the roombaName
        # is added to the topic to publish to
        msg.payload = msg.payload.decode("utf-8")
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
        Config = configparser.ConfigParser()
        try:
            Config.read(file)
            log.info("reading info from config file %s" % file)
            roombas = {}
            for address in Config.sections():
                roomba_data = literal_eval(Config.get(address, "data"))
                roombas[address] = {
                    "blid": Config.get(address, "blid"),
                    "password": Config.get(address, "password"),
                    "roombaName": roomba_data.get("robotname", None)}
        except Exception as e:
            log.warn("Error reading config file %s" %e)
        return roombas

    def create_html(myroomba,mapPath="."):
        '''
        Create html files for live display of roomba maps - but only if they
        don't already exist
        '''
        #default css and html
        css='''body {
    background-color: white;
    color: white;
    margin: 0;
    padding: 0;
    }
img,video {
    width: auto;
    max-height:100%;
    }
'''
        html='''<!DOCTYPE html>
<html>
<head>
<link href="style.css" rel="stylesheet" type="text/css">
</head>
<script>

function refresh(node)
{
   var times = 1000; // gap in Milli Seconds;

   (function startRefresh()
   {
      var address;
      if(node.src.indexOf('?')>-1)
       address = node.src.split('?')[0];
      else
       address = node.src;
      node.src = address+"?time="+new Date().getTime();

      setTimeout(startRefresh,times);
   })();

}

window.onload = function()
{
  var node = document.getElementById('img');
  refresh(node);
  // you can refresh as many images you want just repeat above steps
}
</script>

<body>
'''
        html +='<img id="img" src="%smap.png" alt="Roomba Map Live" style="position:absolute;top:0;left:0"/>' % myroomba.roombaName
        html +='''
</body>
</html>
'''
        #python 3 workaround
        try:
            FileNotFoundError
        except NameError:
            #py2
            FileNotFoundError = PermissionError = IOError

        #check is style.css exists, if not create it
        css_path = mapPath+"/style.css"
        try:
            fn = open(css_path , "r")  #check if file exists (or is readable)
            fn.close()
        except (IOError,FileNotFoundError):
            log.warn("CSS file not found, creating %s" % css_path)
            try:
                with open(css_path , "w") as fn:
                    fn.write(css)
            except (IOError, PermissionError) as e:
                log.error("unable to create file %s, error: %s" % css_path, e)
        #check is html exists, if not create it
        html_path = mapPath+"/"+ myroomba.roombaName + "roomba_map.html"
        try:
            fn = open(html_path, "r")  #check if file exists (or is readable)
            fn.close()
        except (IOError,FileNotFoundError):
            log.warn("html file not found, creating %s" % html_path)
            try:
                with open(html_path, "w") as fn:
                    fn.write(html)
                make_executable(html_path)
            except (IOError, PermissionError) as e:
                log.error("unable to create file %s, error: %s" % html_path, e)

    def make_executable(path):
        mode = os.stat(path).st_mode
        mode |= (mode & 0o444) >> 2    # copy R bits to X
        os.chmod(path, mode)

    def setup_logger(logger_name, log_file, level=logging.DEBUG, console=False):
        try:
            l = logging.getLogger(logger_name)
            if logger_name ==__name__:
                formatter = logging.Formatter(
                    '[%(levelname)1.1s %(asctime)s] %(message)s')
            else:
                formatter = logging.Formatter('%(message)s')
            fileHandler = RotatingFileHandler(
                log_file, mode='a', maxBytes=2000000, backupCount=5)
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
                print("Error: %s: You probably don't have permission to "
                      "write to the log file/directory - try sudo" % e)
            else:
                print("Log Error: %s" % e)
            sys.exit(1)

    #args = parse_args()    #don't know what this is for - removed NW 3/2/2018
    arg = parse_args()
    
    if arg.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    #setup logging
    setup_logger(__name__, arg.log,level=log_level,console=arg.echo)

    log = logging.getLogger(__name__)

    log.info("*******************")
    log.info("* Program Started *")
    log.info("*******************")

    log.info("Roomba.py Version: %s" % roomba.__version__)

    log.info("Python Version: %s" % sys.version.replace('\n',''))

    if HAVE_MQTT:
        import paho.mqtt # bit of a kludge, just to get the version number
        log.info("Paho MQTT Version: %s" % paho.mqtt.__version__)
        if (sys.version_info.major == 2 and sys.version_info.minor == 7 and
            sys.version_info.micro < 9 and
            int(paho.mqtt.__version__.split(".")[0]) >= 1 and
            int(paho.mqtt.__version__.split(".")[1]) > 2):
            log.error("NOTE: if your python version is less than 2.7.9, "
                      "and Paho MQTT verion is not 1.2.3 or lower, this "
                      "program will NOT WORK")
            log.error("Please use <sudo> pip install paho-mqtt==1.2.3 to "
                      "downgrade paho-mqtt, or use a later version of python")
            sys.exit(1)

    if HAVE_CV2:
        log.info("CV Version: %s" % cv2.__version__)

    if HAVE_PIL:
        import PIL #bit of a kludge, just to get the version number
        log.info("PIL Version: %s" % PIL.__version__)
        if int(PIL.__version__.split(".")[0]) < 4:
            log.warn("WARNING: PIL version is %s, this is not the latest! "
                     "You can get bad memory leaks with old versions of PIL"
                     % Image.PILLOW_VERSION)
            log.warn("run: 'pip install --upgrade pillow' to fix this")

    log.debug("-- DEBUG Mode ON -")
    log.info("<CNTRL C> to Exit")
    log.info("Roomba 980 MQTT data Interface")

    roombas = {}

    if arg.blid is None or arg.roombaPassword is None:
        roombas = read_config_file(arg.configfile)
        if len(roombas) == 0:
            log.warn("No roomba or config file defined, I will attempt to "
                     "discover Roombas, please put the Roomba on the dock "
                     "and follow the instructions:")
            if arg.roombaIP is None:
                Password(file=arg.configfile)
            else:
                Password(arg.roombaIP,file=arg.configfile)
            roombas = read_config_file(arg.configfile)
            if len(roombas) == 0:
                log.error("No Roombas found! You must specify RoombaIP, blid "
                          "and roombaPassword to run this program, or have "
                          "a config file, use -h to show options.")
                sys.exit(0)
            else:
                log.info("Success! %d Roombas Found!" % len(roombas))
    else:
        roombas[arg.roombaIP] = {
            "blid": arg.blid,
            "password": arg.roombaPassword,
            "roombaName": arg.roombaName}

    # set broker = "127.0.0.1"  # mosquitto broker is running on localhost
    mqttc = None
    if arg.broker is not None:
        brokerCommand = arg.brokerCommand
        brokerSetting = arg.brokerSetting

        # connect to broker
        mqttc = mqtt.Client()
        # Assign event callbacks
        mqttc.on_message = broker_on_message
        mqttc.on_connect = broker_on_connect
        mqttc.on_disconnect = broker_on_disconnect
        mqttc.on_publish = broker_on_publish
        mqttc.on_subscribe = broker_on_subscribe
        # uncomment to enable logging
        # mqttc.on_log = broker_on_log

        try:
            if arg.user != None:
                mqttc.username_pw_set(arg.user, arg.password)
            log.info("connecting to broker")
            # Ping MQTT broker every 60 seconds if no data is published
            # from this script.
            mqttc.connect(arg.broker, arg.port, 60)

        except socket.error:
            log.error("Unable to connect to MQTT Broker")
            mqttc = None

    roomba_list = []
    for addr, info in six.iteritems(roombas):
        log.info("Creating Roomba object %s" % addr)
        #NOTE: cert_name is a default certificate. change this if your
        # certificates are in a different place. any valid certificate will
        # do, it's not used but needs to be there to enable mqtt TLS encryption
        # instansiate Roomba object
        # minnimum required to connect on Linux Debian system
        # myroomba = Roomba(address, blid, roombaPassword)
        roomba_list.append(
            roomba.Roomba(addr, blid=info["blid"],
            password=info["password"],
            topic=arg.topic, continuous=arg.continuous,
            clean=False,
            cert_name=arg.cert,
            roombaName=info["roombaName"]))

    for myroomba in roomba_list:
        log.info("connecting Roomba %s" % myroomba.address)
        # auto create html files (if they don't exist)
        create_html(myroomba,arg.mapPath)
        # all these are optional, if you don't include them, the defaults
        # will work just fine
        if arg.exclude != "":
            myroomba.exclude = arg.exclude
        myroomba.set_options(
            raw=arg.raw, indent=arg.indent, pretty_print=arg.pretty_print)
        if not arg.continuous:
            myroomba.delay = arg.delay//1000
        if arg.mapSize != "" and arg.mapPath != "":
            # enable live maps, class default is no maps
            myroomba.enable_map(enable=True, mapSize=arg.mapSize,
                                mapPath=arg.mapPath, iconPath=arg.iconPath,
                                roomOutline=arg.roomOutline)
        if arg.broker is not None:
            # if you want to publish Roomba data to your own mqtt broker
            # (default is not to) if you have more than one roomba, and
            # assign a roombaName, it is addded to this topic
            # (ie brokerFeedback/roombaName)
            myroomba.set_mqtt_client(mqttc, arg.brokerFeedback)
        # finally connect to Roomba - (required!)
        myroomba.connect()

    try:
        if mqttc is not None:
            mqttc.loop_forever()
        else:
            while True:
                log.info("Roomba Data: %s" %
                         json.dumps(myroomba.master_state, indent=2))
                time.sleep(5)

    except (KeyboardInterrupt, SystemExit):
        log.info("System exit Received - Exiting program")
        mqttc.disconnect()
        sys.exit(0)


if __name__ == '__main__':
    main()
