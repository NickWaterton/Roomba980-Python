Roomba980-Python
================

Unofficial iRobot Roomba 980 python library (SDK).

Thanks to https://github.com/koalazak/dorita980 where much of the inner workings were derived from.

This is version 1.0 so it may be buggy!

## Advice

If you enjoy python980 and it works nice for you, I recommend blocking the internet access to your robot to avoid the OTA firmware updates. New firmware changes can cause python980 to stop working. Blocking firmware updates can be performed using the parental control options on your router.

When a new firmware is published, you can come here to verify if python980 is still compatible. Once python980 is compatible you can temporarily enable internet access for your robot to get the firmware upgrade.

## Firmware 2.x.x documentation

**This library is only for firmware 2.x.x.** [Check your robot version!](http://homesupport.irobot.com/app/answers/detail/a_id/529) **and is for python 2.7**

Tested with firmware version V2.2.5-2/ubuntu 14.04

## Features

* Get your username/password easily
* Auto discovery robot IP (optional)
* Local API control (from your MQTT broker)
* Simplified Cleaning Preferences settings.
* **NOT Firmware 1.6.x compatible.**
* Firmware 2.x.x compatible.
* Multiple Roombas supported (but not tested)
* Live Maps
* Maps show locations of errors, bin full, cancelled runs
* auto map translation and rotation (at cleaning completion/error etc.)
* designed for openhab2 compatibility

## Live Maps

![iRobot Roomba 980 cleaning map using python980 lib](/map.png)

## Dependancies

This script/library is intended to forward roomba data/commands to/from a local MQTT server (this is optional though). In this case, you need paho-mqtt installed
```bash
<sudo> pip install paho-mqtt
```

For map drawing, you need at least PIL installed (preferably the latest version of pillow)
```bash
<sudo> pip install pillow
```

For fancy maps, you need openCV installed (V2). The installation of this can be complex, so I leave that up to you. Maps works without it, but it's nicer with it.

## Install

First you need python 2.7 installed (note: this library is not python 3!) and then:

clone this repository:
```bash
git clone https://github.com/NickWaterton/Roomba980-Python.git
cd Roomba980-Python
```

run `./roomba.py -h` to get the options. This what you will get:

```bash
nick@proliant:~/Scripts/roomba/Roomba980-Python$ ./roomba.py -h
usage: roomba.py [-h] [-f CONFIGFILE] [-n ROOMBANAME] [-t TOPIC]
                 [-T BROKERFEEDBACK] [-C BROKERCOMMAND] [-S BROKERSETTING]
                 [-b BROKER] [-p PORT] [-U USER] [-P PASSWORD] [-R ROOMBAIP]
                 [-u BLID] [-w ROOMBAPASSWORD] [-i INDENT] [-l LOG] [-e] [-D]
                 [-r] [-j] [-c] [-d DELAY] [-m] [-M MAPPATH] [-s MAPSIZE]
                 [-I ICON] [-x EXCLUDE] [--version]

Forward MQTT data from Roomba 980 to local MQTT broker

optional arguments:
  -h, --help            show this help message and exit
  -f CONFIGFILE, --configfile CONFIGFILE
                        config file name, default: ./config.ini)
  -n ROOMBANAME, --roombaName ROOMBANAME
                        optional Roomba name, default: "")
  -t TOPIC, --topic TOPIC
                        Roomba MQTT Topic to subscribe to (can use wildcards #
                        and + default: #)
  -T BROKERFEEDBACK, --brokerFeedback BROKERFEEDBACK
                        Topic on broker to publish feedback to (default:
                        /roomba/feedback)
  -C BROKERCOMMAND, --brokerCommand BROKERCOMMAND
                        Topic on broker to publish commands to (default:
                        /roomba/command
  -S BROKERSETTING, --brokerSetting BROKERSETTING
                        Topic on broker to publish settings to (default:
                        /roomba/setting
  -b BROKER, --broker BROKER
                        ipaddress of MQTT broker (default: None)
  -p PORT, --port PORT  MQTT broker port number (default: 1883)
  -U USER, --user USER  MQTT broker user name (default: None)
  -P PASSWORD, --password PASSWORD
                        MQTT broker password (default: None)
  -R ROOMBAIP, --roombaIP ROOMBAIP
                        ipaddress of Roomba 980 (default: None)
  -u BLID, --blid BLID  Roomba 980 blid (default: None)
  -w ROOMBAPASSWORD, --roombaPassword ROOMBAPASSWORD
                        Roomba 980 password (default: None)
  -i INDENT, --indent INDENT
                        Default indentation=auto
  -l LOG, --log LOG     path/name of log file (default: ./Roomba.log)
  -e, --echo            Echo to Console (default: True)
  -D, --debug           debug mode
  -r, --raw             Output raw data to mqtt, no decoding of json data
  -j, --pretty_print    pretty print json in logs
  -c, --continuous      Continuous connection to Roomba (default: True)
  -d DELAY, --delay DELAY
                        Disconnect period for non-continuous connection
                        (default: 1000ms)
  -m, --drawmap         Draw Roomba cleaning map (default: True)
  -M MAPPATH, --mapPath MAPPATH
                        Location to store maps to (default: ./)
  -s MAPSIZE, --mapSize MAPSIZE
                        Map Size, Dock offset and skew for the map. (800,1500)
                        is the size, (0,0) is the dock location, in the center
                        of the map, 0 is the rotation of the map, 0 is the
                        rotation of the roomba. use single quotes around the
                        string. (default: '(800,1500,0,0,0,0)')
  -I ICON, --icon ICON  location of dock icon. (default: "./home.png")
  -x EXCLUDE, --exclude EXCLUDE
                        Exclude topics that have this in them (default: "")
  --version             show program's version number and exit
```

## quick start
With the roomba 980 on the dock and charged, stand by the roomba and run
```bash
./roomba.py
```
or
```bash
python roomba.py
```

Follow the instructions, the script will attempt to find the roomba, obtain the IP, blid, and password - then save these to a local configuration file. If this works, the program will then start displaying messages from your Roomba, and printing the maste_state every few seconds. the results are logged to a log file (Roomba.log by default).

On future runs (Once successful), these values will be taken from the configuration file, so you only have to do this once. You can manually specify these on the command line, some example start up bash scripts are supplied.
I advice you to experiment with the map size (if you are using maps), as that is the one variable that isn't totally automatic. the size, position of the dock etc depend on your house layout.
the syntax of the map layout is (map x,map y, dock x, dock y, map rotation, roomba rotation). See the examples.

## How to get your username/blid and password

You can get it automatically as described in quick start, or you can run:
```bash
./getpassword.py
```

either with or without the IP address of your roomba.
```bash
./getpassword.py -R <roomba IP>
```

You can also specify a config file other than the default (-h for options). Results are displayed and saved to the config file.

## Using the library in your python script

```python
    from roomba import Roomba
    import paho.mqtt.client as mqtt
    import time
    
    def broker_on_connect(client, userdata, flags, rc):
        print("Broker Connected with result code "+str(rc))
        #subscribe to roomba feedback
        if rc == 0:
            mqttc.subscribe(brokerCommand)
            mqttc.subscribe(brokerSetting)
                        
    def broker_on_message(mosq, obj, msg):
        #publish to roomba
        if "command" in msg.topic:
            print("Received COMMAND: %s" % str(msg.payload))
            myroomba.send_command(str(msg.payload))
        elif "setting" in msg.topic:
            print("Received SETTING: %s" % str(msg.payload))
            cmd = str(msg.payload).split()
            myroomba.set_preference(cmd[0], cmd[1])
        
    def broker_on_publish(mosq, obj, mid):
        pass

    def broker_on_subscribe(mosq, obj, mid, granted_qos):
        print("Broker Subscribed: %s %s" % (str(mid), str(granted_qos)))

    def broker_on_disconnect(mosq, obj, rc):
        print("Broker disconnected")

    def broker_on_log(mosq, obj, level, string):
        print(string)
    
    
    broker = 'localhost'    #ip of mqtt broker
    #broker = None if not using local mqtt broker
    
    mqttc = None
    if broker is not None:
        brokerCommand = "/roomba/command"
        brokerSetting = "/roomba/setting"
        
        #connect to broker
        mqttc = mqtt.Client()
        # Assign event callbacks
        mqttc.on_message = broker_on_message
        mqttc.on_connect = broker_on_connect
        mqttc.on_disconnect = broker_on_disconnect
        mqttc.on_publish = broker_on_publish
        mqttc.on_subscribe = broker_on_subscribe
        
        try:
            mqttc.username_pw_set("user", "password")   #put your own user and password here if you are using them, otherwise comment out
            mqttc.connect(broker, 1883, 60) # Ping MQTT broker every 60 seconds if no data is published from this script.
            
        except Exception as e:
            print("Unable to connect to MQTT Broker: %s" % e)
            mqttc = None

    #myroomba = Roomba(address, blid, roombaPassword)  #minnimum required to connect on Linux Debian system
    myroomba = Roomba(address, blid, roombaPassword, topic="#", continuous=True, clean=False, cert_name = "./ca-certificates.crt")
 
    #all these are optional, if you don't include them, the defaults will work just fine
    #if you are using maps
    myroomba.enable_map(enable=True, mapSize=(800,1650,-300,-50,2,0), mapPath="./", home_icon_file="./home.png")  #enable live maps, class default is no maps
    if broker is not None:
        myroomba.set_mqtt_client(mqttc, brokerFeedback) #if you want to publish Roomba data to your own mqtt broker (default is not to) if you have more than one roomba, and assign a roombaName, it is addded to this topic (ie brokerFeedback/roombaName)
    #finally connect to Roomba - (required!)
    myroomba.connect()
    
    try:
        if mqttc is not None:
            mqttc.loop_forever()
        else:
            while True:
                print("Roomba Data: %s" % json.dumps(myroomba.master_state, indent=2))
                time.sleep(5)
            
    except (KeyboardInterrupt, SystemExit):
        print("System exit Received - Exiting program")
        if mqttc is not None:
            mqttc.disconnect()
```
master_state starts empty, and fills with time, it is published in full every 5 minutes by default (but updates to it are published live)

master_state should contain:
```javascript

{ netinfo:
   { dhcp: true,
     addr: 4294967040,
     mask: 4294967040,
     gw: 4294967040,
     dns1: 4294967040,
     dns2: 0,
     bssid: '12:12:12:12:12:12',
     sec: 4 },
  wifistat: { wifi: 1, uap: false, cloud: 4 },
  wlcfg: { sec: 7, ssid: '123123123123123123123123' },
  mac: '34:34:34:34:34:34',
  country: 'US',
  cloudEnv: 'prod',
  svcEndpoints: { svcDeplId: 'v005' },
  localtimeoffset: -180,
  utctime: 1487103319,
  pose: { theta: 61, point: { x: 171, y: -113 } },
  batPct: 100,
  dock: { known: true },
  bin: { present: true, full: false },
  audio: { active: false },
  cleanMissionStatus:
   { cycle: 'none',
     phase: 'charge',
     expireM: 0,
     rechrgM: 0,
     error: 0,
     notReady: 0,
     mssnM: 2,
     sqft: 29,
     initiator: 'manual',
     nMssn: 324 },
  language: 2,
  noAutoPasses: false,
  noPP: false,
  ecoCharge: false,
  vacHigh: false,
  binPause: false,
  carpetBoost: true,
  openOnly: false,
  twoPass: false,
  schedHold: false,
  lastCommand: { command: 'dock', time: 1487103424, initiator: 'manual' },
  langs:
   [ { 'en-US': 0 },
     { 'fr-FR': 1 },
     { 'es-ES': 2 },
     { 'de-DE': 3 },
     { 'it-IT': 4 } ],
  bbnav: { aMtrack: 45, nGoodLmrks: 15, aGain: 12, aExpo: 9 },
  bbpanic: { panics: [ 8, 8, 8, 14, 8 ] },
  bbpause: { pauses: [ 15, 0, 0, 0, 0, 0, 0, 0, 0, 17 ] },
  bbmssn:
   { nMssn: 323,
     nMssnOk: 218,
     nMssnC: 99,
     nMssnF: 1,
     aMssnM: 35,
     aCycleM: 31 },
  bbrstinfo: { nNavRst: 41, nMobRst: 0, causes: '0000' },
  cap: { pose: 1, ota: 2, multiPass: 2, carpetBoost: 1 },
  sku: 'R98----',
  batteryType: 'lith',
  soundVer: '31',
  uiSwVer: '4582',
  navSwVer: '01.09.09',
  wifiSwVer: '20902',
  mobilityVer: '5309',
  bootloaderVer: '3580',
  umiVer: '5',
  softwareVer: 'v2.0.0-34',
  tz:
   { events: [ { dt: 0, off: -180 }, { dt: 0, off: -180 }, { dt: 0, off: 0 } ],
     ver: 2 },
  timezone: 'America/Buenos_Aires',
  name: 'robotNAme',
  cleanSchedule:
   { cycle: [ 'none', 'none', 'none', 'none', 'none', 'none', 'none' ],
     h: [ 17, 10, 10, 12, 10, 13, 17 ],
     m: [ 0, 30, 30, 0, 30, 30, 0 ] },
  bbchg3:
   { avgMin: 158,
     hOnDock: 6110,
     nAvail: 1280,
     estCap: 12311,
     nLithChrg: 233,
     nNimhChrg: 0,
     nDocks: 98 },
  bbchg: { nChgOk: 226, nLithF: 0, aborts: [ 4, 4, 4 ] },
  bbswitch: { nBumper: 55889, nClean: 300, nSpot: 47, nDock: 98, nDrops: 300 },
  bbrun:
   { hr: 211,
     min: 48,
     sqft: 566,
     nStuck: 17,
     nScrubs: 85,
     nPicks: 592,
     nPanics: 178,
     nCliffsF: 1532,
     nCliffsR: 2224,
     nMBStll: 0,
     nWStll: 1,
     nCBump: 0 },
  bbsys: { hr: 6522, min: 54 },
  signal: { rssi: -43, snr: 40 } }

```

## Commands/Settings

* Commands are:
  * "start",
  * "stop",
  * "pause",
  * "resume",
  * "dock"

* Settings are:
  * carpetBoost true, 
  * vacHigh true,
  * openOnly true,   (this is edge clean - set to false to enable edge cleaning)
  * noAutoPasses true,
  * twoPass true,
  * binPause true,
                
You publish this as a string to your mqtt broker topic /roomba/command or /roomba/setting (or whatever you have defined if you change these from default)
Ubuntu example (assuming the broker is on your localhost) - should work for any linux system with mosquitto installed
```bash
mosquitto_pub -t "/roomba/command" -m "start"
mosquitto_pub -t "/roomba/setting" -m "carpetBoost true"
```

## ToDo's

I'm just using some roomba icons I found on the web, if you have better roomba icos, please let me know, I know these are not Roomba 980 icons...
Post my openhab2 items, sitemaps, transforms and rules for controlling the Roomba.
Update the example map shown here, it's an older version, the new ones are a little nicer.
