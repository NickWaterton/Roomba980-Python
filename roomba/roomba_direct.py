#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# hacky fixes NW 30th Nov 2019
# Pillow fix for V 7 __version__ replaced with __version__
# Jan 8th 2021 NW Complete re-write

__version__ = "2.0a"

import logging
from logging.handlers import RotatingFileHandler
import sys
from roomba import Roomba
from password  import Password
from ast import literal_eval
import argparse
import os
import time
import textwrap
# Import trickery
global HAVE_CV2
global HAVE_MQTT
global HAVE_PIL
HAVE_CV2 = HAVE_MQTT = HAVE_PIL = False
import configparser
import asyncio

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

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    print("PIL module not found, maps are disabled")
    
import asyncio
if sys.version_info < (3, 7):
    asyncio.get_running_loop = asyncio.get_event_loop

def parse_args():
    default_icon_path = os.path.join(os.path.dirname(__file__), 'res')
    #-------- Command Line -----------------
    parser = argparse.ArgumentParser(
        description='Forward MQTT data from Roomba to local MQTT broker')
    parser.add_argument(
        '-f', '--configfile',
        action='store',
        type=str,
        default="./config.ini",
        help='config file name (default: %(default)s)')
    parser.add_argument(
        '-n', '--roomba_name',
        action='store',
        type=str,
        default="", help='optional Roomba name (default: "%(default)s")')
    parser.add_argument(
        '-t', '--topic',
        action='store',
        type=str,
        default="#",
        help='Roomba MQTT Topic to subscribe to (can use wildcards # and '
             '+ default: %(default)s)')
    parser.add_argument(
        '-T', '--broker_feedback',
        action='store',
        type=str,
        default="/roomba/feedback",
        help='Topic on broker to publish feedback to (default: '
             '%(default)s</name>)')
    parser.add_argument(
        '-C', '--broker_command',
        action='store',
        type=str,
        default="/roomba/command",
        help='Topic on broker to publish commands to (default: '
             '%(default)s</name>)')
    parser.add_argument(
        '-S', '--broker_setting',
        action='store',
        type=str,
        default="/roomba/setting",
        help='Topic on broker to publish settings to (default: '
             '%(default)s</name>)')
    parser.add_argument(
        '-b', '--broker',
        action='store',
        type=str,
        default=None,
        help='ipaddress of MQTT broker (default: %(default)s)')
    parser.add_argument(
        '-p', '--port',
        action='store',
        type=int,
        default=1883,
        help='MQTT broker port number (default: %(default)s)')
    parser.add_argument(
        '-U', '--user',
        action='store',
        type=str,
        default=None,
        help='MQTT broker user name (default: %(default)s)')
    parser.add_argument(
        '-P', '--broker_password',
        action='store',
        type=str,
        default=None,
        help='MQTT broker password (default: %(default)s)')
    parser.add_argument(
        '-R', '--roomba_ip',
        action='store',
        type=str,
        default='255.255.255.255',
        help='ipaddress of Roomba (default: %(default)s)')
    parser.add_argument(
        '-u', '--blid',
        action='store',
        type=str,
        default=None,
        help='Roomba blid (default: %(default)s)')
    parser.add_argument(
        '-w', '--password',
        action='store',
        type=str,
        default=None,
        help='Roomba password (default: %(default)s)')
    parser.add_argument(
        '-wp', '--webport',
        action='store',
        type=int,
        default=None,
        help='Optional web server port number (default: %(default)s)')
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
        default="./roomba.log",
        help='path/name of log file (default: %(default)s)')
    parser.add_argument(
        '-e', '--echo',
        action='store_false',
        default = True,
        help='Echo to Console (default: %(default)s)')
    parser.add_argument(
        '-D', '--debug',
        action='store_true',
        default = False,
        help='debug mode')
    parser.add_argument(
        '-r', '--raw',
        action='store_true',
        default = False,
        help='Output raw data to mqtt, no decoding of json data (default: %(default)s)')
    parser.add_argument(
        '-j', '--pretty_print',
        action='store_true',
        default = False,
        help='pretty print json in logs (default: %(default)s)')
    parser.add_argument(
        '-m', '--drawmap',
        action='store_false',
        default = True,
        help='Draw Roomba cleaning map (default: %(default)s)')
    parser.add_argument(
        '-M', '--mappath',
        action='store',
        type=str,
        default=".",
        help='Location to store maps to (default: %(default)s)')
    parser.add_argument(
        '-sq', '--max_sqft',
        action='store',
        type=int,
        default=0,
        help='Max Square Feet of map (default: %(default)s)')
    parser.add_argument(
        '-s', '--mapsize',
        action='store',
        type=str,
        default="(800,1500,0,0,0,0)",
        help='Map Size, Dock offset and skew for the map.'
             '(800,1500) is the size, (0,0) is the dock location, '
             'in the center of the map, 0 is the rotation of the map, '
             '0 is the rotation of the roomba. '
             'Use single quotes around the string. (default: '
             '"%(default)s")')
    parser.add_argument(
        '-I', '--iconpath',
        action='store',
        type=str,
        default=default_icon_path,
        help='location of icons. (default: "%(default)s")')
    parser.add_argument(
        '-o', '--room_outline',
        action='store_false',
        default = True,
        help='Draw room outline (default: %(default)s)')
    parser.add_argument(
        '-x', '--exclude',
        action='store',type=str, default="", help='Exclude topics that have this in them (default: "%(default)s")')
    parser.add_argument(
        '--cert',
        action='store',
        type=str,
        default='/etc/ssl/certs/ca-certificates.crt',
        help='Set the certificate to use for MQTT communication with the Roomba (depreciated)')
    parser.add_argument(
        '--version',
        action='version',
        version="%(prog)s ({}) Roomba {}".format(__version__, Roomba.__version__),
        help='Display version of this program')
    return parser.parse_args()

def main():

    #----------- Local Routines ------------

    def create_html(myroomba,mappath="."):
        '''
        Create html files for live display of roomba maps - but only if they
        don't already exist
        NOTE add {{ for { in html where you need variable substitution
        '''
        #default css and html
        css =   '''\
                body {
                    background-color: white;
                    margin: 0;
                    color: white;
                    padding: 0;
                    }
                img,video {
                    width: auto;
                    max-height:100%;
                    }
                '''
        html = '''\
                <!DOCTYPE html>
                <html>
                <head>
                <link href="style.css" rel="stylesheet" type="text/css">
                </head>
                <script>

                function refresh(node)
                {{
                   var times = 1000; // gap in Milli Seconds;

                   (function startRefresh()
                   {{
                      var address;
                      if(node.src.indexOf('?')>-1)
                       address = node.src.split('?')[0];
                      else
                       address = node.src;
                      node.src = address+"?time="+new Date().getTime();

                      setTimeout(startRefresh,times);
                   }})();

                }}

                window.onload = function()
                {{
                  var node = document.getElementById('img');
                  refresh(node);
                  // you can refresh as many images you want just repeat above steps
                }}
                </script>

                <body>
                <img id="img" src="{}map.png" alt="Roomba Map Live" style="position:absolute;top:0;left:0"/>
                </body>
                </html>
                '''.format(myroomba.roombaName)
                
        def write_file(fname, data, mode=0o666):
            if not os.path.isfile(fname):
                log.warn("{} file not found, creating".format(fname))
                try:
                    with open(fname , "w") as fn:
                        fn.write(textwrap.dedent(data))
                    os.chmod(fname, mode)
                except (IOError, PermissionError) as e:
                    log.error("unable to create file {}, error: {}".format(fname, e))
                    
        #check if style.css exists, if not create it
        css_path = '{}/style.css'.format(mappath)
        write_file(css_path, css)
                
        #check if html exists, if not create it
        html_path = '{}/{}roomba_map.html'.format(mappath, myroomba.roombaName)
        write_file(html_path, html, 0o777)

    def setup_logger(logger_name, log_file, level=logging.DEBUG, console=False):
        try: 
            l = logging.getLogger(logger_name)
            formatter = logging.Formatter('[%(asctime)s][%(levelname)5.5s](%(name)-20s) %(message)s')
            if log_file is not None:
                fileHandler = logging.handlers.RotatingFileHandler(log_file, mode='a', maxBytes=10000000, backupCount=10)
                fileHandler.setFormatter(formatter)
            if console == True:
                #formatter = logging.Formatter('[%(levelname)1.1s %(name)-20s] %(message)s')
                streamHandler = logging.StreamHandler()
                streamHandler.setFormatter(formatter)

            l.setLevel(level)
            if log_file is not None:
                l.addHandler(fileHandler)
            if console == True:
              l.addHandler(streamHandler)
                 
        except Exception as e:
            print("Error in Logging setup: %s - do you have permission to write the log file??" % e)
            sys.exit(1)

    arg = parse_args()  #note: all options can be included in the config file
    
    if arg.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    #setup logging
    setup_logger('Roomba', arg.log, level=log_level,console=arg.echo)
    
    #log = logging.basicConfig(level=logging.DEBUG, 
    #    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    log = logging.getLogger('Roomba')

    log.info("*******************")
    log.info("* Program Started *")
    log.info("*******************")
    
    log.debug('Debug Mode')

    log.info("Roomba.py Version: %s" % Roomba.__version__)

    log.info("Python Version: %s" % sys.version.replace('\n',''))

    if HAVE_MQTT:
        import paho.mqtt
        log.info("Paho MQTT Version: %s" % paho.mqtt.__version__)

    if HAVE_CV2:
        log.info("CV Version: %s" % cv2.__version__)

    if HAVE_PIL:
        import PIL #bit of a kludge, just to get the version number
        log.info("PIL Version: %s" % PIL.__version__)

    log.debug("-- DEBUG Mode ON -")
    log.info("<CNTRL C> to Exit")
    log.info("Roomba MQTT data Interface")
    
    group = None
    options = vars(arg) #use args as dict

    if arg.blid is None or arg.password is None:
        get_passwd = Password(arg.roomba_ip,file=arg.configfile)
        roombas = get_passwd.get_roombas()
    else:
        roombas = {arg.roomba_ip: {"blid": arg.blid,
                                   "password": arg.password,
                                   "roomba_name": arg.roomba_name}}
                                   
    roomba_list = []
    for addr, info in roombas.items():
        log.info("Creating Roomba object {}, {}".format(addr, info.get("roomba_name", addr)))
        #get options from config (if they exist) this overrides command line options.
        for opt, value in options.copy().items():
            config_value = info.get(opt)
            if config_value is None:
               options[opt] = value
            elif value is None or isinstance(value, str):
                options[opt] = config_value
            else:
                options[opt] = literal_eval(config_value)
                
        # minnimum required to connect on Linux Debian system
        # myroomba = Roomba(address, blid, roombaPassword)
        myroomba =  Roomba(addr,
                           blid=arg.blid,
                           password=arg.password,
                           topic=arg.topic,
                           roombaName=arg.roomba_name,
                           webport=arg.webport)
                           
        if arg.webport:
            arg.webport+=1
                    
        if arg.exclude:
            myroomba.exclude = arg.exclude
            
        #set various options
        myroomba.set_options(raw=arg.raw,
                             indent=arg.indent,
                             pretty_print=arg.pretty_print,
                             max_sqft=arg.max_sqft)
            
        if arg.mappath and arg.mapsize and arg.drawmap:
            # auto create html files (if they don't exist)
            create_html(myroomba, arg.mappath)
            # enable live maps, class default is no maps
            myroomba.enable_map(enable=True,
                                mapSize=arg.mapsize,
                                mapPath=arg.mappath,
                                iconPath=arg.iconpath,
                                roomOutline=arg.room_outline)
                                
        if arg.broker is not None:
            # if you want to publish Roomba data to your own mqtt broker
            # (default is not to) if you have more than one roomba, and
            # assign a roombaName, it is addded to this topic
            # (ie brokerFeedback/roombaName)
            myroomba.setup_mqtt_client(arg.broker,
                                       arg.port,
                                       arg.user,
                                       arg.broker_password,
                                       arg.broker_feedback,
                                       arg.broker_command,
                                       arg.broker_setting)
             
        roomba_list.append(myroomba)   
        
    
    loop = asyncio.get_event_loop()
    loop.set_debug(arg.debug)
    
    group = asyncio.gather(*[myroomba.async_connect() for myroomba in roomba_list])
    
    if not group:
        for myroomba in roomba_list:
            myroomba.connect()            #start each roomba connection individually
    
    try:
        loop.run_forever()
            
    except (KeyboardInterrupt, SystemExit):
        log.info("System exit Received - Exiting program")
        for myroomba in roomba_list:
                myroomba.disconnect()
        
    finally:
        pass


if __name__ == '__main__':
    main()
