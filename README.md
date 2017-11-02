roombapy
================

Unofficial iRobot Roomba 980 python library (SDK).

Thanks to https://github.com/koalazak/dorita980 where much of the inner workings were derived from.

This is version 1.0 so it may be buggy!
**NEW** Now version 1.1.2 - so it may be less buggy (or not)

## Advice
If you enjoy python980 and it works well for you, I recommend blocking the internet access to your robot to avoid the OTA firmware updates. New firmware changes can cause python980 to stop working. Blocking firmware updates can be performed using the parental control options on your router.

When a new firmware is published, you can come here to verify if python980 is still compatible. Once python980 is compatible you can temporarily enable internet access for your robot to get the firmware upgrade.

## Firmware 2.x.x notes
**This library is only for firmware 2.x.x.** [Check your robot version!](http://homesupport.irobot.com/app/answers/detail/a_id/529) *NEW* **Now supports Python 2.7 and Python 3.6** (thanks to pschmitt for adding Python 3 compatibility)

Only local connections are supported, cloud connections are a future project. The project was written to allow Openhab2 control, so if you integrate Roomba into Openhab2, you can control it from anywhere.

As only **one connection at at time is** allowed to the Roomba local mqtt server, the app will connect via the cloud if you run in continuous mode. In periodic mode, the app can connect locally, but the library will be off line until the app disconnects, when it will automatically reconnect.

Tested with firmware version V2.2.5-2/Ubuntu 14.04
* Now tested and working with F/W 2.2.9-1
* Now tested on Ubuntu 16.04
* Now tested with Python 3.5
* Now Tested with OpenCV 3.2
* Now Tested with paho-mqtt 1.3 (on python V2.7.12 and above - does **NOT** work on python versions lower than 2.7.9 - see "Dependencies")

## Features
* Get your username/password easily
* Auto discovery robot IP (optional)
* Local API control
* Remote API control (via your MQTT broker)
* Simplified Cleaning Preferences settings.
* **NOT Firmware 1.6.x compatible.**
* Firmware 2.x.x compatible.
* Multiple Roombas supported (but not tested)
* Continuous or periodic connection (to allow local app access)
* Live Maps
* Maps show locations of errors, bin full, cancelled runs
* auto map translation and rotation (at cleaning completion/error etc.)
* designed for openhab2 compatibility

## Live Maps
![iRobot Roomba 980 cleaning map using python980 lib](/roomba/res/map.png)
### OpenCV
If you have OpenCV installed, the library will use it to render the final map (on completion/error), it uses PIL for Live Maps, so the final map looks nicer. **This uses a lot of processing power/memory**, I don't know what happens if you try this on a RPi or other limited platform!
Also, if you enable debugging mode (-D), intermediate maps (edges.png, final_map.png and so on) are drawn every time a new co-ordinate is reported (every second or so when running). This consumes a lot of resources **You have been warned!**.
### PIL
Please use the latest version of pillow (V 4.1.1 at least), there are some nasty memory leaks in text processing in earlier versions that will quickly use up all your RAM and make the program unresponsive.
The library will issue a warning if it detects an earlier version of PIL.

If you do not have PIL installed, the system will not draw maps (even if enabled), even if you have OpenCV. PIL is used for basic image manipulations. If you do not specifically enable maps, no maps will be drawn. `roomba.py` uses maps, but the class default is to disable maps, so in your own scripts, if you want maps, you have to enable them (after creating the object).

## Dependencies
The following libraries/modules are used. Some are optional:
* six         **required**
* paho-mqtt   *optional*
* PIL/pillow  *optional*
* openCV      *optional*
* numpy       *optional (used by openCV)*

This script/library is intended to forward roomba data/commands to/from a local MQTT server (this is optional though). In this case, you need paho-mqtt installed
```bash
<sudo> pip install paho-mqtt
```

**NOTE:** Our friends at paho-mqtt have just released v1.3 (replaces v1.2.3) *which has breaking changes in it* You need to take note of the following:
If you are running python versions lower than 2.7.9 (eg Ubuntu 14.04), you **need to install/stay with the older version of paho-mqtt**. Check your python version using `python -V`.
To install the old version of paho-mqtt, use:
```bash
<sudo> pip install paho-mqtt==1.2.3
```

later versions of python should work with either version of paho-mqtt now, due to changes made in V1.1.1 and above of roomba.py.

For map drawing, you need at least PIL installed (preferably the latest version of pillow)
```bash
<sudo> pip install pillow
```

For fancy maps, you need openCV installed (V2, or V3). The installation of this can be complex, so I leave that up to you. Maps works without it, but it's nicer with it.

For Python 3.x compatibility, the six library is used
```bash
<sudo> pip install six
```

or
```bash
<sudo> pip3 install six
```
depending on your default python environment (in Unbuntu 14.04 and 16.04, python 2.7 is the default, but python 3.x is available).

## Install
First you need python 2.7 *or* python 3.5/3.6 installed (thanks to pschmitt for adding Python 3 compatibility) and then:

install via pip (this will take of dependencies as well):
```bash
pip install https://github.com/NickWaterton/Roomba980-Python.git
```

Alternatively you may get going by cloning this repository:
```bash
git clone https://github.com/NickWaterton/Roomba980-Python.git
cd Roomba980-Python
```

run `roomba -h` (or `python roomba/roomba.py` if you opted for the git checkout) to get the available options. This is what you will get:

```bash
usage: roomba [-h] [-f CONFIGFILE] [-n ROOMBANAME] [-t TOPIC]
              [-T BROKERFEEDBACK] [-C BROKERCOMMAND] [-S BROKERSETTING]
              [-b BROKER] [-p PORT] [-U USER] [-P PASSWORD] [-R ROOMBAIP]
              [-u BLID] [-w ROOMBAPASSWORD] [-i INDENT] [-l LOG] [-e] [-D]
              [-r] [-j] [-c] [-d DELAY] [-m] [-M MAPPATH] [-s MAPSIZE]
              [-I ICONPATH] [-o] [-x EXCLUDE] [--cert CERT] [--version]

Forward MQTT data from Roomba 980 to local MQTT broker

optional arguments:
  -h, --help            show this help message and exit
  -f CONFIGFILE, --configfile CONFIGFILE
                        config file name (default: ./config.ini)
  -n ROOMBANAME, --roombaName ROOMBANAME
                        optional Roomba name (default: "")
  -t TOPIC, --topic TOPIC
                        Roomba MQTT Topic to subscribe to (can use wildcards #
                        and + default: #)
  -T BROKERFEEDBACK, --brokerFeedback BROKERFEEDBACK
                        Topic on broker to publish feedback to (default:
                        /roomba/feedback</name>)
  -C BROKERCOMMAND, --brokerCommand BROKERCOMMAND
                        Topic on broker to publish commands to (default:
                        /roomba/command</name>)
  -S BROKERSETTING, --brokerSetting BROKERSETTING
                        Topic on broker to publish settings to (default:
                        /roomba/setting</name>)
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
                        Location to store maps to (default: .)
  -s MAPSIZE, --mapSize MAPSIZE
                        Map Size, Dock offset and skew for the map. (800,1500)
                        is the size, (0,0) is the dock location, in the center
                        of the map, 0 is the rotation of the map, 0 is the
                        rotation of the roomba. use single quotes around the
                        string. (default: '(800,1500,0,0,0,0)')
  -I ICONPATH, --iconPath ICONPATH
                        location of icons. (default: "./")
  -o, --roomOutline     Draw room outline (default: True)
  -x EXCLUDE, --exclude EXCLUDE
                        Exclude topics that have this in them (default: "")
  --cert CERT           Set the certificate to use for MQTT communication with
                        the Roomba
  --version             show program's version number and exit
```

## quick start
With the roomba 980 on the dock and charged (and connected to wifi), stand by the roomba and run
```bash
roomba
```
or
```bash
python roomba.py
```

Follow the instructions, the script will attempt to find the roomba, obtain the IP, blid, and password - then save these to a local configuration file. If this works, the program will then start displaying messages from your Roomba, and printing the master_state every few seconds. the results are logged to a log file (Roomba.log by default).

On future runs (Once successful), these values will be taken from the configuration file, so you only have to do this once. You can manually specify these on the command line, some example start up bash scripts are supplied.
I advice you to experiment with the map size (if you are using maps), as that is the one variable that isn't totally automatic. the size, position of the dock etc depend on your house layout.
the syntax of the map layout is (map x,map y, dock x, dock y, map rotation, roomba rotation). See the examples.

### Example output
Logging is supported with the python standard logging module
```bash
[I 2017-05-09 08:52:10,792] *******************
[I 2017-05-09 08:52:10,792] * Program Started *
[I 2017-05-09 08:52:10,792] *******************
[I 2017-05-09 08:52:10,792] Paho MQTT Version: 1002003
[I 2017-05-09 08:52:10,792] <CNTRL C> to Exit
[I 2017-05-09 08:52:10,792] Roomba 980 MQTT data Interface
[I 2017-05-09 08:52:10,792] connecting to broker
[I 2017-05-09 08:52:10,792] Creating Roomba object 192.168.100.181
[I 2017-05-09 08:52:10,793] CONTINUOUS connection
[I 2017-05-09 08:52:10,793] connecting Roomba 192.168.100.181
[I 2017-05-09 08:52:10,793] Posting DECODED data
[I 2017-05-09 08:52:10,793] MAP: Maps Enabled
[I 2017-05-09 08:52:10,793] MAP: openening existing line image
[I 2017-05-09 08:52:10,814] MAP: openening existing problems image
[I 2017-05-09 08:52:10,830] MAP: home_pos: (100,775)
[I 2017-05-09 08:52:10,834] MAP: Initialisation complete
[I 2017-05-09 08:52:10,835] Connecting
[I 2017-05-09 08:52:13,243] Roomba Connected
[I 2017-05-09 08:52:13,262] Received Roomba Data : wifistat, {"state":{"reported":{"netinfo":{"dhcp":true,"addr":3232261301,"mask":4294967040,"gw":3232261121,"dns1":3232261121,"dns2":0,"bssid":"6c:b0:ce:14:2f:cd","sec":4}}}}
[I 2017-05-09 08:52:13,307] Received Roomba Data : wifistat, {"state":{"reported":{"wifistat":{"wifi":1,"uap":false,"cloud":1}}}}
[I 2017-05-09 08:52:13,308] Received Roomba Data : wifistat, {"state":{"reported":{"netinfo":{"dhcp":true,"addr":3232261301,"mask":4294967040,"gw":3232261121,"dns1":3232261121,"dns2":0,"bssid":"6c:b0:ce:14:2f:cd","sec":4}}}}
[I 2017-05-09 08:52:13,309] Received Roomba Data : wifistat, {"state":{"reported":{"wlcfg":{"sec":7,"ssid":"7761746572746F6E73"}}}}
[I 2017-05-09 08:52:13,309] Received Roomba Data : wifistat, {"state":{"reported":{"mac":"f0:03:8c:13:24:5b"}}}
[I 2017-05-09 08:52:13,310] Received Roomba Data : $aws/things/3117850851637850/shadow/update, {"state":{"reported":{"country": "US"}}}
[I 2017-05-09 08:52:13,325] Received Roomba Data : $aws/things/3117850851637850/shadow/update, {"state":{"reported":{"cloudEnv": "prod"}}}
[I 2017-05-09 08:52:13,331] Received Roomba Data : $aws/things/3117850851637850/shadow/update, {"state":{"reported":{"svcEndpoints":{"svcDeplId": "v011"}}}}
[I 2017-05-09 08:52:13,429] Received Roomba Data : $aws/things/3117850851637850/shadow/update, {"state":{"reported":{"mapUploadAllowed":true}}}
[I 2017-05-09 08:52:13,483] Received Roomba Data : wifistat, {"state":{"reported":{"localtimeoffset":-240,"utctime":1494334341,"pose":{"theta":-179,"point":{"x":181,"y":-13}}}}}
[I 2017-05-09 08:52:13,533] Received Roomba Data : $aws/things/3117850851637850/shadow/update, {"state":{"reported":{"batPct":100,"dock":{"known":false},"bin":{"present":true,"full":false},"audio":{"active":false}}}}
[I 2017-05-09 08:52:13,689] Received Roomba Data : $aws/things/3117850851637850/shadow/update, {"state":{"reported":{"cleanMissionStatus":{"cycle":"none","phase":"charge","expireM":0,"rechrgM":0,"error":0,"notReady":0,"mssnM":0,"sqft":0,"initiator":"localApp","nMssn":109},"language":0,"noAutoPasses":false,"noPP":false,"ecoCharge":false}}}
[I 2017-05-09 08:52:13,693] updated state to: Charging
[I 2017-05-09 08:52:13,693] MAP: received: new_co_ords: {'y': 181, 'x': -13, 'theta': -179} old_co_ords: {'y': 181, 'x': -13, 'theta': -179} phase: charge, state: Charging
[I 2017-05-09 08:52:13,693] MAP: ignoring new co-ords in charge phase
[I 2017-05-09 08:52:13,756] Received Roomba Data : $aws/things/3117850851637850/shadow/update, {"state":{"reported":{"vacHigh":false,"binPause":true,"carpetBoost":true,"openOnly":false,"twoPass":false,"schedHold":false,"lastCommand":{"command":"dock","time":1494260716,"initiator":"localApp"}}}}
[I 2017-05-09 08:52:13,821] Received Roomba Data : $aws/things/3117850851637850/shadow/update, {"state":{"reported":{"langs":[{"en-US":0},{"fr-FR":1},{"es-ES":2},{"de-DE":3},{"it-IT":4}],"bbnav":{"aMtrack":98,"nGoodLmrks":5,"aGain":7,"aExpo":56},"bbpanic":{"panics":[11,8,6,8,6]},"bbpause":{"pauses":[0,14,0,0,0,0,17,0,4,0]}}}}
[I 2017-05-09 08:52:14,231] Received Roomba Data : $aws/things/3117850851637850/shadow/update, {"state":{"reported":{"bbmssn":{"nMssn":109,"nMssnOk":30,"nMssnC":78,"nMssnF":0,"aMssnM":14,"aCycleM":15},"bbrstinfo":{"nNavRst":3,"nMobRst":0,"causes":"0000"}}}}
[I 2017-05-09 08:52:14,242] Received Roomba Data : $aws/things/3117850851637850/shadow/update, {"state":{"reported":{"cap":{"pose":1,"ota":2,"multiPass":2,"carpetBoost":1,"pp":1,"binFullDetect":1,"langOta":1,"maps":1,"edge":1,"eco":1},"sku":"R980020","batteryType":"lith","soundVer":"31","uiSwVer":"4582","navSwVer":"01.11.02","wifiSwVer":"20923"}}}
[I 2017-05-09 08:52:14,245] Received Roomba Data : $aws/things/3117850851637850/shadow/update, {"state":{"reported":{"mobilityVer":"5420","bootloaderVer":"4042","umiVer":"6","softwareVer":"v2.2.5-2","tz":{"events":[{"dt":0,"off":-300},{"dt":0,"off":-240},{"dt":0,"off":-300}],"ver":3},"timezone":"America/Toronto","name":"Roomba"}}}
[I 2017-05-09 08:52:14,263] Received Roomba Data : $aws/things/3117850851637850/shadow/update, {"state":{"reported":{"cleanSchedule":{"cycle":["none","start","start","start","start","start","none"],"h":[0,9,9,9,9,9,0],"m":[0,0,0,0,0,0,0]},"bbchg3":{"avgMin":81,"hOnDock":448,"nAvail":163,"estCap":12311,"nLithChrg":38,"nNimhChrg":0,"nDocks":45}}}}
[I 2017-05-09 08:52:14,304] Received Roomba Data : $aws/things/3117850851637850/shadow/update, {"state":{"reported":{"bbchg":{"nChgOk":34,"nLithF":0,"aborts":[0,0,0]},"bbswitch":{"nBumper":41275,"nClean":37,"nSpot":12,"nDock":45,"nDrops":187}}}}
[I 2017-05-09 08:52:14,310] Received Roomba Data : $aws/things/3117850851637850/shadow/update, {"state":{"reported":{"bbrun":{"hr":48,"min":18,"sqft":190,"nStuck":7,"nScrubs":75,"nPicks":199,"nPanics":51,"nCliffsF":871,"nCliffsR":348,"nMBStll":1,"nWStll":3,"nCBump":0},"bbsys":{"hr":518,"min":55}}}}
[I 2017-05-09 08:52:15,406] Received Roomba Data : wifistat, {"state":{"reported":{"signal":{"rssi":-46,"snr":39}}}}
```

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

## API
The API calls are (see getpassword.py for an example of how to use the password class):
### Classes
```python
password(address='255.255.255.255', file=".\config.ini")
Roomba(address=None, blid=None, password=None, topic="#", continuous=True, clean=False, cert_name="", roombaName="", file="./config.ini")
```
### Roomba methods
```python
connect()
disconnect()
send_command(command)
set_preference(preference, setting)
set_mqtt_client(mqttc=None, brokerFeedback="")
set_options(raw=False, indent=0, pretty_print=False)
enable_map( enable=False, mapSize="(800,1500,0,0,0,0)", mapPath="./", iconPath="./",
            home_icon_file="home.png",
            roomba_icon_file="roomba.png",
            roomba_error_file="roombaerror.png",
            roomba_cancelled_file="roombacancelled.png",
            roomba_battery_file="roomba-charge.png",
            bin_full_file="binfull.png",
            roomba_size=(50,50), draw_edges = 15, auto_rotate=True)
make_icon(input="./roomba.png", output="./roomba_mod.png")
```
### Data Structures
```python
#boolean
roomba_connected
bin_full
#string
cleanMissionStatus_phase
current_state
error_message
#dictionarys
co_ords
master_state
```
### Notes
If you have multiple roomba's, these should be supported *not tested yet - I only have one roomba!*. Each roomba has it's own name, and this will be automatically used to differentiate them. feedback is published to `\roomba\feedback\<roomba name>\`, commands go to `\roomba\command\<roomba name>` and settings to `\roomba\setting\<roomba name>`. Maps and so on have <roomba name> prepended to them.
You can manually specify the roomba name in the object, in your own scripts, in which case the same applies.

## Using the library in your python script
Both these scripts are in the examples directory, as simple.py and complicated.py. To use them, copy them from examples to the main roomba.py directory (or copy roomba.py to examples). Edit them to include your own roomba ip address, blid and password, and run `python simple.py`. For "complicated.py" you also need to add your mqtt broker adddress, username, and password. Then run `python complicated.py`
### Simple Version
```python
from roomba import Roomba

#uncomment the option you want to run, and replace address, blid and roombaPassword with your own values

address = "192.168.100.181"
blid = "3835850251647850"
roombaPassword = ":1:1493319243:gOizXpQ4lcdSoD1xJ"

myroomba = Roomba(address, blid, roombaPassword)
#or myroomba = Roomba() #if you have a config file - will attempt discovery if you don't
myroomba.connect()

myroomba.set_preference("carpetBoost", "true")
#myroomba.set_preference("twoPass", "false")

#myroomba.send_command("start")
#myroomba.send_command("stop")
#myroomba.send_command("dock")

import json, time
for i in range(5):
    print json.dumps(myroomba.master_state, indent=2)
    time.sleep(1)
myroomba.disconnect()
```
### More Complicated Version
```python
from roomba import Roomba
import paho.mqtt.client as mqtt
import time
import json

#put your own values here
broker = 'localhost'    #ip of mqtt broker
user = 'user'           #mqtt username
password = 'password'   #mqtt password
#broker = None if not using local mqtt broker
address = '192.168.100.181'
blid = "3515850261627850"
roombaPassword = ":1:1492379243:gOiyXpQ4lbRoD1xJ"

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


mqttc = None
if broker is not None:
    brokerCommand = "/roomba/command"
    brokerSetting = "/roomba/setting"
    brokerFeedback = "/roomba/feedback"

    #connect to broker
    mqttc = mqtt.Client()
    #Assign event callbacks
    mqttc.on_message = broker_on_message
    mqttc.on_connect = broker_on_connect
    mqttc.on_disconnect = broker_on_disconnect
    mqttc.on_publish = broker_on_publish
    mqttc.on_subscribe = broker_on_subscribe

    try:
        mqttc.username_pw_set(user, password)  #put your own mqtt user and password here if you are using them, otherwise comment out
        mqttc.connect(broker, 1883, 60) #Ping MQTT broker every 60 seconds if no data is published from this script.

    except Exception as e:
        print("Unable to connect to MQTT Broker: %s" % e)
        mqttc = None

myroomba = Roomba()  #minnimum required to connect on Linux Debian system, will read connection from config file
#myroomba = Roomba(address, blid, roombaPassword, topic="#", continuous=True, clean=False, cert_name = "./ca-certificates.crt")  #setting things manually

#all these are optional, if you don't include them, the defaults will work just fine
#if you are using maps
myroomba.enable_map(enable=True, mapSize="(800,1650,-300,-50,2,0)", mapPath="./", iconPath="./")  #enable live maps, class default is no maps
if broker is not None:
    myroomba.set_mqtt_client(mqttc, brokerFeedback) #if you want to publish Roomba data to your own mqtt broker (default is not to) if you have more than one roomba, and assign a roombaName, it is addded to this topic (ie brokerFeedback/roombaName)
#finally connect to Roomba - (required!)
myroomba.connect()

print("<CMTRL C> to exit")
print("Subscribe to /roomba/feedback/# to see published data")

try:
    if mqttc is not None:
        mqttc.loop_forever()
    else:
        while True:
            print("Roomba Data: %s" % json.dumps(myroomba.master_state, indent=2))
            time.sleep(5)

except (KeyboardInterrupt, SystemExit):
    print("System exit Received - Exiting program")
    myroomba.disconnect()
    if mqttc is not None:
        mqttc.disconnect()

```
## Data/Feedback
master_state starts empty, and fills with time, it is published in full every 5 minutes by default (but updates to it are published live)

master_state should contain:
```javascript
{
  "state": {
    "reported": {
      "netinfo": {
        "dhcp": true,
        "addr": 3232261301,
        "mask": 4294967040,
        "gw": 3232261121,
        "dns1": 3232261121,
        "dns2": 0,
        "bssid": "6c:b0:ce:14:2f:cd",
        "sec": 4
      },
      "wifistat": {
        "wifi": 1,
        "uap": false,
        "cloud": 1
      },
      "wlcfg": {
        "sec": 7,
        "ssid": "7761746572746F6E73"
      },
      "mac": "f0:03:8c:13:24:5b",
      "country": "US",
      "cloudEnv": "prod",
      "svcEndpoints": {
        "svcDeplId": "v011"
      },
      "mapUploadAllowed": true,
      "localtimeoffset": -240,
      "utctime": 1494331734,
      "pose": {
        "theta": -179,
        "point": {
          "x": 181,
          "y": -13
        }
      },
      "batPct": 100,
      "dock": {
        "known": false
      },
      "bin": {
        "present": true,
        "full": false
      },
      "audio": {
        "active": true
      },
      "cleanMissionStatus": {
        "cycle": "none",
        "phase": "charge",
        "expireM": 0,
        "rechrgM": 0,
        "error": 0,
        "notReady": 0,
        "mssnM": 0,
        "sqft": 0,
        "initiator": "localApp",
        "nMssn": 109
      },
      "language": 0,
      "noAutoPasses": false,
      "noPP": false,
      "ecoCharge": false,
      "vacHigh": false,
      "binPause": true,
      "carpetBoost": true,
      "openOnly": false,
      "twoPass": false,
      "schedHold": false,
      "lastCommand": {
        "command": "dock",
        "time": 1494260716,
        "initiator": "localApp"
      },
      "langs": [
        {
          "en-US": 0
        },
        {
          "fr-FR": 1
        },
        {
          "es-ES": 2
        },
        {
          "de-DE": 3
        },
        {
          "it-IT": 4
        }
      ],
      "bbnav": {
        "aMtrack": 98,
        "nGoodLmrks": 5,
        "aGain": 7,
        "aExpo": 56
      },
      "bbpanic": {
        "panics": [
          11,
          8,
          6,
          8,
          6
        ]
      },
      "bbpause": {
        "pauses": [
          0,
          14,
          0,
          0,
          0,
          0,
          17,
          0,
          4,
          0
        ]
      },
      "bbmssn": {
        "nMssn": 109,
        "nMssnOk": 30,
        "nMssnC": 78,
        "nMssnF": 0,
        "aMssnM": 14,
        "aCycleM": 15
      },
      "bbrstinfo": {
        "nNavRst": 3,
        "nMobRst": 0,
        "causes": "0000"
      },
      "cap": {
        "pose": 1,
        "ota": 2,
        "multiPass": 2,
        "carpetBoost": 1,
        "pp": 1,
        "binFullDetect": 1,
        "langOta": 1,
        "maps": 1,
        "edge": 1,
        "eco": 1
      },
      "sku": "R980020",
      "batteryType": "lith",
      "soundVer": "31",
      "uiSwVer": "4582",
      "navSwVer": "01.11.02",
      "wifiSwVer": "20923",
      "mobilityVer": "5420",
      "bootloaderVer": "4042",
      "umiVer": "6",
      "softwareVer": "v2.2.5-2",
      "tz": {
        "events": [
          {
            "dt": 0,
            "off": -300
          },
          {
            "dt": 0,
            "off": -240
          },
          {
            "dt": 0,
            "off": -300
          }
        ],
        "ver": 3
      },
      "timezone": "America/Toronto",
      "name": "Roomba",
      "cleanSchedule": {
        "cycle": [
          "none",
          "start",
          "start",
          "start",
          "start",
          "start",
          "none"
        ],
        "h": [
          0,
          9,
          9,
          9,
          9,
          9,
          0
        ],
        "m": [
          0,
          0,
          0,
          0,
          0,
          0,
          0
        ]
      },
      "bbchg3": {
        "avgMin": 81,
        "hOnDock": 448,
        "nAvail": 163,
        "estCap": 12311,
        "nLithChrg": 38,
        "nNimhChrg": 0,
        "nDocks": 45
      },
      "bbchg": {
        "nChgOk": 34,
        "nLithF": 0,
        "aborts": [
          0,
          0,
          0
        ]
      },
      "bbswitch": {
        "nBumper": 41275,
        "nClean": 37,
        "nSpot": 12,
        "nDock": 45,
        "nDrops": 187
      },
      "bbrun": {
        "hr": 48,
        "min": 18,
        "sqft": 190,
        "nStuck": 7,
        "nScrubs": 75,
        "nPicks": 199,
        "nPanics": 51,
        "nCliffsF": 871,
        "nCliffsR": 348,
        "nMBStll": 1,
        "nWStll": 3,
        "nCBump": 0
      },
      "bbsys": {
        "hr": 518,
        "min": 11
      },
      "signal": {
        "rssi": -36,
        "snr": 53
      }
    }
  }
}
```

in raw mode, the json from the Roomba is passed directly to the mqtt topic (usually /roomba/feedback), in normal mode, each json item is decoded and published as a seperate topic. To see the topic published and their values run:
```bash
mosquitto_sub -v -t /roomba/feedback/#
```

Output should look like this:
```bash
/roomba/feedback/netinfo_dhcp True
/roomba/feedback/netinfo_addr 3232261301
/roomba/feedback/netinfo_mask 4294967040
/roomba/feedback/netinfo_gw 3232261121
/roomba/feedback/netinfo_dns1 3232261121
/roomba/feedback/netinfo_dns2 0
/roomba/feedback/netinfo_bssid 6c:b0:ce:14:2f:cd
/roomba/feedback/netinfo_sec 4
/roomba/feedback/wifistat_wifi 1
/roomba/feedback/wifistat_uap False
/roomba/feedback/wifistat_cloud 1
/roomba/feedback/netinfo_dhcp True
/roomba/feedback/netinfo_addr 3232261301
/roomba/feedback/netinfo_mask 4294967040
/roomba/feedback/netinfo_gw 3232261121
/roomba/feedback/netinfo_dns1 3232261121
/roomba/feedback/netinfo_dns2 0
/roomba/feedback/netinfo_bssid 6c:b0:ce:14:2f:cd
/roomba/feedback/netinfo_sec 4
/roomba/feedback/wlcfg_sec 7
/roomba/feedback/wlcfg_ssid 7761746572746F6E73
/roomba/feedback/mac f0:03:8c:13:24:5b
/roomba/feedback/country US
/roomba/feedback/cloudEnv prod
/roomba/feedback/svcEndpoints_svcDeplId v011
/roomba/feedback/mapUploadAllowed True
/roomba/feedback/localtimeoffset -240
/roomba/feedback/utctime 1494330872
/roomba/feedback/pose_theta -179
/roomba/feedback/pose_point_x 181
/roomba/feedback/pose_point_y -13
/roomba/feedback/batPct 100
/roomba/feedback/dock_known False
/roomba/feedback/bin_present True
/roomba/feedback/bin_full False
/roomba/feedback/audio_active False
/roomba/feedback/cleanMissionStatus_cycle none
/roomba/feedback/cleanMissionStatus_phase charge
/roomba/feedback/cleanMissionStatus_expireM 0
/roomba/feedback/cleanMissionStatus_rechrgM 0
/roomba/feedback/cleanMissionStatus_error 0
/roomba/feedback/cleanMissionStatus_notReady 0
/roomba/feedback/cleanMissionStatus_mssnM 0
/roomba/feedback/cleanMissionStatus_sqft 0
/roomba/feedback/cleanMissionStatus_initiator localApp
/roomba/feedback/cleanMissionStatus_nMssn 109
/roomba/feedback/language 0
/roomba/feedback/noAutoPasses False
/roomba/feedback/noPP False
/roomba/feedback/ecoCharge False
/roomba/feedback/state Charging
/roomba/feedback/vacHigh False
/roomba/feedback/binPause True
/roomba/feedback/carpetBoost True
/roomba/feedback/openOnly False
/roomba/feedback/twoPass False
/roomba/feedback/schedHold False
/roomba/feedback/lastCommand_command dock
/roomba/feedback/lastCommand_time 1494260716
/roomba/feedback/lastCommand_initiator localApp
/roomba/feedback/state Charging
/roomba/feedback/langs [('en-US', 0), ('fr-FR', 1), ('es-ES', 2), ('de-DE', 3), ('it-IT', 4)]
/roomba/feedback/bbnav_aMtrack 98
/roomba/feedback/bbnav_nGoodLmrks 5
/roomba/feedback/bbnav_aGain 7
/roomba/feedback/bbnav_aExpo 56
/roomba/feedback/bbpanic_panics [11, 8, 6, 8, 6]
/roomba/feedback/bbpause_pauses [0, 14, 0, 0, 0, 0, 17, 0, 4, 0]
/roomba/feedback/state Charging
/roomba/feedback/bbmssn_nMssn 109
/roomba/feedback/bbmssn_nMssnOk 30
/roomba/feedback/bbmssn_nMssnC 78
/roomba/feedback/bbmssn_nMssnF 0
/roomba/feedback/bbmssn_aMssnM 14
/roomba/feedback/bbmssn_aCycleM 15
/roomba/feedback/bbrstinfo_nNavRst 3
/roomba/feedback/bbrstinfo_nMobRst 0
/roomba/feedback/bbrstinfo_causes 0000
/roomba/feedback/state Charging
/roomba/feedback/cap_pose 1
/roomba/feedback/cap_ota 2
/roomba/feedback/cap_multiPass 2
/roomba/feedback/cap_carpetBoost 1
/roomba/feedback/cap_pp 1
/roomba/feedback/cap_binFullDetect 1
/roomba/feedback/cap_langOta 1
/roomba/feedback/cap_maps 1
/roomba/feedback/cap_edge 1
/roomba/feedback/cap_eco 1
/roomba/feedback/sku R980020
/roomba/feedback/batteryType lith
/roomba/feedback/soundVer 31
/roomba/feedback/uiSwVer 4582
/roomba/feedback/navSwVer 01.11.02
/roomba/feedback/wifiSwVer 20923
/roomba/feedback/state Charging
/roomba/feedback/mobilityVer 5420
/roomba/feedback/bootloaderVer 4042
/roomba/feedback/umiVer 6
/roomba/feedback/softwareVer v2.2.5-2
/roomba/feedback/tz_events [('dt', 0), ('off', -300), ('dt', 0), ('off', -240), ('dt', 0), ('off', -300)]
/roomba/feedback/tz_ver 3
/roomba/feedback/timezone America/Toronto
/roomba/feedback/name Roomba
/roomba/feedback/state Charging
/roomba/feedback/cleanSchedule_cycle ['none', 'start', 'start', 'start', 'start', 'start', 'none']
/roomba/feedback/cleanSchedule_h [0, 9, 9, 9, 9, 9, 0]
/roomba/feedback/cleanSchedule_m [0, 0, 0, 0, 0, 0, 0]
/roomba/feedback/bbchg3_avgMin 81
/roomba/feedback/bbchg3_hOnDock 448
/roomba/feedback/bbchg3_nAvail 163
/roomba/feedback/bbchg3_estCap 12311
/roomba/feedback/bbchg3_nLithChrg 38
/roomba/feedback/bbchg3_nNimhChrg 0
/roomba/feedback/bbchg3_nDocks 45
/roomba/feedback/state Charging
/roomba/feedback/bbchg_nChgOk 34
/roomba/feedback/bbchg_nLithF 0
/roomba/feedback/bbchg_aborts [0, 0, 0]
/roomba/feedback/bbswitch_nBumper 41275
/roomba/feedback/bbswitch_nClean 37
/roomba/feedback/bbswitch_nSpot 12
/roomba/feedback/bbswitch_nDock 45
/roomba/feedback/bbswitch_nDrops 187
/roomba/feedback/state Charging
/roomba/feedback/bbrun_hr 48
/roomba/feedback/bbrun_min 18
/roomba/feedback/bbrun_sqft 190
/roomba/feedback/bbrun_nStuck 7
/roomba/feedback/bbrun_nScrubs 75
/roomba/feedback/bbrun_nPicks 199
/roomba/feedback/bbrun_nPanics 51
/roomba/feedback/bbrun_nCliffsF 871
/roomba/feedback/bbrun_nCliffsR 348
/roomba/feedback/bbrun_nMBStll 1
/roomba/feedback/bbrun_nWStll 3
/roomba/feedback/bbrun_nCBump 0
/roomba/feedback/bbsys_hr 517
/roomba/feedback/bbsys_min 57
/roomba/feedback/state Charging
/roomba/feedback/signal_rssi -35
/roomba/feedback/signal_snr 54
/roomba/feedback/state Charging
/roomba/feedback/signal_rssi -36
/roomba/feedback/signal_snr 53
/roomba/feedback/state Charging
```

In addition `state` and `error_message` are published which are derived by the class.

## Commands/Settings
### Commands
* Commands are:
  * "start"
  * "stop"
  * "pause"
  * "resume"
  * "dock"
### Settings
* Settings are:
  * carpetBoost true
  * vacHigh true
  * openOnly true   *this is edge clean - set to false to enable edge cleaning*
  * noAutoPasses true
  * twoPass true
  * binPause true

You publish this as a string to your mqtt broker topic /roomba/command or /roomba/setting (or whatever you have defined if you change these from default)
Ubuntu example (assuming the broker is on your localhost) - should work for any linux system with mosquitto installed
```bash
mosquitto_pub -t "/roomba/command" -m "start"
mosquitto_pub -t "/roomba/setting" -m "carpetBoost true"
```

Or call directly from a python script (see simple example above).

## Openhab/Openhab2 Interface
Here are my Openhab2 files:
### Items
```
/* Roomba items */
Group roomba_items  "Roomba"        <roomba>        (gGF)

/* Roomba Commands */
String roomba_command "Roomba" <roomba> (roomba_items) {mqtt=">[proliant:/roomba/command:command:*:${command}]", autoupdate=false}
/* Settings */
Switch roomba_edgeClean    "Edge Clean [%s]" <switch> (roomba_items) {mqtt=">[proliant:/roomba/setting:command:ON:openOnly false],>[proliant:/roomba/setting:command:OFF:openOnly true],<[proliant:/roomba/feedback/openOnly:state:MAP(inverse_switch.map)]", autoupdate=false}
Switch roomba_carpetBoost  "Auto carpet Boost [%s]" <switch> (roomba_items) {mqtt=">[proliant:/roomba/setting:command:ON:carpetBoost true],>[proliant:/roomba/setting:command:OFF:carpetBoost false],<[proliant:/roomba/feedback/carpetBoost:state:MAP(switch.map)]", autoupdate=false}
Switch roomba_vacHigh      "Vacuum Boost [%s]" <switch> (roomba_items) {mqtt=">[proliant:/roomba/setting:command:ON:vacHigh true],>[proliant:/roomba/setting:command:OFF:vacHigh false],<[proliant:/roomba/feedback/vacHigh:state:MAP(switch.map)]", autoupdate=false}
Switch roomba_noAutoPasses "Auto Passes [%s]" <switch> (roomba_items) {mqtt=">[proliant:/roomba/setting:command:ON:noAutoPasses false],>[proliant:/roomba/setting:command:OFF:noAutoPasses true],<[proliant:/roomba/feedback/noAutoPasses:state:MAP(inverse_switch.map)]", autoupdate=false}
Switch roomba_twoPass      "Two Passes [%s]" <switch> (roomba_items) {mqtt=">[proliant:/roomba/setting:command:ON:twoPass true],>[proliant:/roomba/setting:command:OFF:twoPass false],<[proliant:/roomba/feedback/twoPass:state:MAP(switch.map)]", autoupdate=false}
Switch roomba_binPause     "Always Complete (even if bin is full) [%s]" <switch> (roomba_items) {mqtt=">[proliant:/roomba/setting:command:ON:binPause false],>[proliant:/roomba/setting:command:OFF:binPause true],<[proliant:/roomba/feedback/binPause:state:MAP(inverse_switch.map)]", autoupdate=false}
/* Roomba Feedback */
String roomba_softwareVer  "Software Version [%s]" <text> (roomba_items) {mqtt="<[proliant:/roomba/feedback/softwareVer:state:default]"}
Number roomba_batPct "Battery [%d%%]" <battery> (roomba_items, Battery)  {mqtt="<[proliant:/roomba/feedback/batPct:state:default]"}
String roomba_lastcommand  "Last Command [%s]" <roomba> (roomba_items) {mqtt="<[proliant:/roomba/feedback/lastCommand_command:state:default]"}
Switch roomba_bin_present  "Bin Present [%s]" <trashpresent> (roomba_items) {mqtt="<[proliant:/roomba/feedback/bin_present:state:MAP(switch.map)]"}
Switch roomba_full   "Bin Full [%s]" <trash> (roomba_items) {mqtt="<[proliant:/roomba/feedback/bin_full:state:MAP(switch.map)]"}
/* Mission values */
String roomba_mission  "Mission [%s]" <msg> (roomba_items) {mqtt="<[proliant:/roomba/feedback/cleanMissionStatus_cycle:state:default]"}
Number roomba_nMssn    "Cleaning Mission Number [%d]" <number> (roomba_items)  {mqtt="<[proliant:/roomba/feedback/cleanMissionStatus_nMssn:state:default]"}
String roomba_phase    "Phase [%s]" <msg> (roomba_items) {mqtt="<[proliant:/roomba/feedback/cleanMissionStatus_phase:state:default]"}
String roomba_initiator  "Initiator [%s]" <msg> (roomba_items) {mqtt="<[proliant:/roomba/feedback/cleanMissionStatus_initiator:state:default]"}
Switch roomba_error "Error [%]" <roombaerror> (roomba_items) {mqtt="<[proliant:/roomba/feedback/cleanMissionStatus_error:state:MAP(switchFromMqtt.map)]"}
String roomba_errortext  "Error Message [%s]" <msg> (roomba_items) {mqtt="<[proliant:/roomba/feedback/error_message:state:default]"}
Number roomba_mssnM "Cleaning Elapsed Time [%d m]" <clock> (roomba_items)  {mqtt="<[proliant:/roomba/feedback/cleanMissionStatus_mssnM:state:default]"}
Number roomba_sqft "Square Ft Cleaned [%d]" <groundfloor> (roomba_items)  {mqtt="<[proliant:/roomba/feedback/cleanMissionStatus_sqft:state:default]"}
Number roomba_expireM "Mission Recharge Time [%d m]" <clock> (roomba_items)  {mqtt="<[proliant:/roomba/feedback/cleanMissionStatus_expireM:state:default]"}
Number roomba_rechrgM "Remaining Time To Recharge [%d m]" <clock> (roomba_items)  {mqtt="<[proliant:/roomba/feedback/cleanMissionStatus_rechrgM:state:default]"}
String roomba_status    "Status [%s]" <msg> (roomba_items) {mqtt="<[proliant:/roomba/feedback/state:state:default]"}
Dimmer roomba_percent_complete    "Mission % Completed [%d%%]" <humidity> (roomba_items)
DateTime roomba_lastmissioncompleted "Last Mission Completed [%1$ta %1$tR]" <calendar>
/* Schedule */
String roomba_cycle   "Day of Week [%s]" <calendar> (roomba_items) {mqtt="<[proliant:/roomba/feedback/cleanSchedule_cycle:state:default]"}
String roomba_cleanSchedule_h   "Hour of Day [%s]" <clock> (roomba_items) {mqtt="<[proliant:/roomba/feedback/cleanSchedule_h:state:default]"}
String roomba_cleanSchedule_m   "Minute of Hour [%s]" <clock> (roomba_items) {mqtt="<[proliant:/roomba/feedback/cleanSchedule_m:state:default]"}
String roomba_cleanSchedule "Schedule [%s]" <calendar> (roomba_items)
/* General */
Switch roomba_control "Roomba ON/OFF [%s]" <switch> (roomba_items)
Number roomba_theta "Theta [%d]" <angle> (roomba_items)  {mqtt="<[proliant:/roomba/feedback/pose_theta:state:default]"}
Number roomba_x "X [%d]" <map> (roomba_items)  {mqtt="<[proliant:/roomba/feedback/pose_point_x:state:default]"}
Number roomba_y "Y [%d]" <map> (roomba_items)  {mqtt="<[proliant:/roomba/feedback/pose_point_y:state:default]"}
Number roomba_rssi "RSSI [%d]" <network> (roomba_items)  {mqtt="<[proliant:/roomba/feedback/signal_rssi:state:default]"}
DateTime roomba_lastheardfrom "Last Update [%1$ta %1$tR]" <clock>
```
### Sitemap
```
Group item=roomba_items {
            Switch item=roomba_command mappings=[start="Start",stop="Stop",pause="Pause",dock="Dock",resume="Resume"]
            Switch item=roomba_control
            Group label="Map" icon="map" {
                Frame label="Map" {
                    //Image icon="map" url="http://your_OH_ip_address:port/static/map.png" label="Map" refresh=1000
                    Webview icon="map" url="http://your_OH_ip_address:port/static/roomba_map.html" height=21 label="Map"
                }
            }
            Group label="Settings" icon="select"{
                Text item=roomba_cleanSchedule
                Switch item=roomba_edgeClean
                Switch item=roomba_carpetBoost
                Switch item=roomba_vacHigh visibility=[roomba_carpetBoost==OFF]
                Switch item=roomba_noAutoPasses
                Switch item=roomba_twoPass visibility=[roomba_noAutoPasses==OFF]
                Switch item=roomba_binPause
            }
            Frame label="Status" {
                Text item=roomba_softwareVer
                Text item=roomba_batPct
                Text item=roomba_phase
                Text item=roomba_lastcommand
                Switch item=roomba_full mappings=[ON="FULL", OFF="Not Full"]
                Switch item=roomba_bin_present mappings=[OFF="Removed", ON="Installed"]
                Text item=roomba_rssi
                Text item=roomba_lastheardfrom
            }
            Frame label="Mission" {
                Text item=roomba_status
                Text item=roomba_rechrgM visibility=[roomba_status=="Recharging"]
                Text item=roomba_mission
                Text item=roomba_percent_complete
                Switch item=roomba_error mappings=[ON="ERROR!", OFF="Normal"]
                Text item=roomba_errortext
                Text item=roomba_mssnM
                Text item=roomba_sqft
                Text item=roomba_nMssn
                Text item=roomba_lastmissioncompleted
                Text item=roomba_initiator
            }
            Frame label="Location" {
                Text item=roomba_theta
                Text item=roomba_x
                Text item=roomba_y
            }
        }
```
### Transforms
```
/etc/openhab2/transform/switch.map
ON=ON
OFF=OFF
0=OFF
1=ON
True=ON
False=OFF
true=ON
false=OFF
-=Unknown
NULL=Unknown

/etc/openhab2/transform/inverse_switch.map
ON=OFF
OFF=ON
0=ON
1=OFF
True=OFF
False=ON
true=OFF
false=ON
-=Unknown
NULL=Unknown

/etc/openhab2/transform/switchFromMqtt.map
-=Unknonwn
NULL=Unknown
OFF=OFF
0=OFF
1=ON
2=ON
3=ON
4=ON
5=ON
6=ON
7=ON
8=ON
9=ON
10=ON
11=ON
12=ON
13=ON
14=ON
15=ON
16=ON
17=ON
18=ON
19=ON
20=ON
21=ON
22=ON
23=ON
24=ON
25=ON
26=ON
27=ON
28=ON
29=ON
30=ON
31=ON
32=ON
33=ON
34=ON
35=ON
36=ON
37=ON
38=ON
39=ON
40=ON
41=ON
42=ON
43=ON
44=ON
45=ON
46=ON
47=ON
48=ON
49=ON
50=ON
51=ON
52=ON
53=ON
54=ON
55=ON
56=ON
57=ON
58=ON
59=ON
60=ON
61=ON
62=ON
63=ON
64=ON
65=ON
66=ON
67=ON
68=ON
69=ON
70=ON
71=ON
72=ON
73=ON
74=ON
75=ON
76=ON
77=ON
78=ON
79=ON
80=ON
81=ON
82=ON
83=ON
84=ON
85=ON
86=ON
87=ON
88=ON
89=ON
90=ON
91=ON
92=ON
93=ON
94=ON
95=ON
96=ON
97=ON
98=ON
99=ON
100=ON
101=ON
102=ON
103=ON
104=ON
105=ON
106=ON
107=ON
108=ON
109=ON
110=ON
111=ON
112=ON
113=ON
114=ON
115=ON
116=ON
117=ON
118=ON
119=ON
120=ON
121=ON
122=ON
123=ON
124=ON
125=ON
126=ON
127=ON
128=ON
129=ON
130=ON
131=ON
132=ON
133=ON
134=ON
135=ON
136=ON
137=ON
138=ON
139=ON
140=ON
141=ON
142=ON
143=ON
144=ON
145=ON
146=ON
147=ON
148=ON
149=ON
150=ON
151=ON
152=ON
153=ON
154=ON
155=ON
156=ON
157=ON
158=ON
159=ON
160=ON
161=ON
162=ON
163=ON
164=ON
165=ON
166=ON
167=ON
168=ON
169=ON
170=ON
171=ON
172=ON
173=ON
174=ON
175=ON
176=ON
177=ON
178=ON
179=ON
180=ON
181=ON
182=ON
183=ON
184=ON
185=ON
186=ON
187=ON
188=ON
189=ON
190=ON
191=ON
192=ON
193=ON
194=ON
195=ON
196=ON
197=ON
198=ON
199=ON
200=ON
201=ON
202=ON
203=ON
204=ON
205=ON
206=ON
207=ON
208=ON
209=ON
210=ON
211=ON
212=ON
213=ON
214=ON
215=ON
216=ON
217=ON
218=ON
219=ON
220=ON
221=ON
222=ON
223=ON
224=ON
225=ON
226=ON
227=ON
228=ON
229=ON
230=ON
231=ON
232=ON
233=ON
234=ON
235=ON
236=ON
237=ON
238=ON
239=ON
240=ON
241=ON
242=ON
243=ON
244=ON
245=ON
246=ON
247=ON
248=ON
249=ON
250=ON
251=ON
252=ON
253=ON
254=ON
255=ON
256=ON
ON=ON
```
### Rules
These use one of my functions getTimestamp, here it is:
```
val Functions$Function2<GenericItem, String, String> getTimestamp = [  //function (lambda) to get a timestamp. Returns formatted string and optionally updates an item
    item,
    date_format |

    var date_time_format = date_format
    if(date_format == "" || date_format == null) date_time_format = "%1$ta %1$tT" //default format Day Hour:Minute:Seconds
    var String Timestamp = String::format( date_time_format, new Date() )
    if(item != NULL && item != null) {
        var Integer time = now().getMillis()    //current time (/1000?)
        var cal = new java.util.GregorianCalendar()
        cal.setTimeInMillis(time)  //timestamp in unix format
        var t = new DateTimeType(cal)

        if(item instanceof DateTimeItem) {
            postUpdate(item, t)
            logInfo("Last Update", item.name + " DateTimeItem updated at: " + Timestamp )
            }
        else if(item instanceof StringItem) {
            postUpdate(item, Timestamp)
            logInfo("Last Update", item.name + " StringItem updated at: " + Timestamp )
            }
        else
            logWarn("Last Update", item.name + " is not DateTime or String - not updating")
    }
    Timestamp
    ]
```
Here are my roomba rules, some of them assume you have e-mail and pushNotification set up:
```
/* Roomba Rules */
rule "Roomba start and stop"
when
    Item roomba_control received command
then
    logInfo("Roomba", "Roomba ON/OFF received command: " + receivedCommand)
    if (receivedCommand == ON)
        sendCommand(roomba_command, "start")
    if (receivedCommand == OFF) {
        sendCommand(roomba_command, "stop")
        Thread::sleep(1000)
        sendCommand(roomba_command, "dock")
    }
end

rule "Roomba Auto Boost Control"
when
    Item roomba_carpetBoost changed
then
    logInfo("Roomba", "Roomba Boost changed to: Auto " + roomba_carpetBoost.state + " Manual: " + roomba_vacHigh.state)
    if (roomba_carpetBoost.state == ON && roomba_vacHigh.state == ON)
        sendCommand(roomba_vacHigh, OFF)
end

rule "Roomba Manual Boost Control"
when
    Item roomba_vacHigh changed
then
    logInfo("Roomba", "Roomba Boost changed to: Auto " + roomba_carpetBoost.state + " Manual: " + roomba_vacHigh.state)
    if (roomba_carpetBoost.state == ON && roomba_vacHigh.state == ON)
        sendCommand(roomba_carpetBoost, OFF)
end

rule "Roomba Auto Passes Control"
when
    Item roomba_noAutoPasses changed or
    Item roomba_twoPass changed
then
    logInfo("Roomba", "Roomba Passes changed to: Auto " + roomba_noAutoPasses.state + " Manual: " + roomba_twoPass.state)
    if (roomba_noAutoPasses.state == ON && roomba_twoPass.state == ON)
        sendCommand(roomba_twoPass, OFF)
end

rule "Roomba Last Update Timestamp"
when
    Item roomba_rssi received update
then
    getTimestamp.apply(roomba_lastheardfrom, "%1$ta %1$tR")
end

rule "Roomba Bin Full"
when
    Item roomba_full changed from OFF to ON
then
    val Timestamp = getTimestamp.apply(roomba_lastheardfrom, "%1$ta %1$tR")
    pushNotification("Roomba", "BIN FULL reported by Roomba at: " + Timestamp)
end

rule "Roomba Error"
when
    Item roomba_error changed from OFF to ON
then
    val Timestamp = getTimestamp.apply(roomba_lastheardfrom, "%1$ta %1$tR")
    pushNotification("Roomba", "ERROR reported by Roomba at: " + Timestamp)
    sendMail(mailTo, "Roomba", "ERROR reported by Roomba at: " + Timestamp + "See attachment for details", "http://your_OH_ip:port/static/map.png")
end

rule "Roomba percent completed"
when
    Item roomba_sqft received update
then
    var sqft_completed = roomba_sqft.state as Number

    var max_sqft = 470  //insert max square footage here
    var min_sqft = 0

    var Number completed_percent = 0

    if (sqft_completed < min_sqft) {completed_percent = 0)
    else if (sqft_completed > max_sqft) {completed_percent = 100}
    else {
        completed_percent = (((sqft_completed - min_sqft) * 100) / (max_sqft-min_sqft)).intValue
        }
    logInfo("Roomba", "Roomba percent complete "+roomba_sqft.state+" of "+max_sqft.toString+" calculated as " + completed_percent.toString + "%")
    postUpdate(roomba_percent_complete,completed_percent)
end

rule "Roomba update command"
when
    Item roomba_phase received update
then
    logInfo("Roomba", "Roomba phase received update: " + roomba_phase.state}
    switch(roomba_phase.state) {
        case "run"          : postUpdate(roomba_command,"start")
        case "hmUsrDock"    : postUpdate(roomba_command,"pause")
        case "hmMidMsn"     : postUpdate(roomba_command,"pause")
        case "hmPostMsn"    : {
                              postUpdate(roomba_command,"dock")
                              getTimestamp.apply(roomba_lastmissioncompleted, "%1$ta %1$tR")
                              }
        case "charge"       : postUpdate(roomba_command,"dock")
        case "stop"         : postUpdate(roomba_command,"stop")
        case "pause"        : postUpdate(roomba_command,"pause")
        case "stuck"        : postUpdate(roomba_command,"stop")
    }
end

rule "Roomba Notifications"
when
    Item roomba_status changed
then
    logInfo("Roomba", "Roomba status is: " + roomba_status.state}
    val Timestamp = getTimestamp.apply(roomba_lastheardfrom, "%1$ta %1$tR")
    switch(roomba_status.state) {
        case "Running"                  : pushNotification("Roomba", "Roomba is RUNNING at: " + Timestamp)
        case "Docking - End Mission"    : {
                                          createTimer(now.plusSeconds(2)) [|
                                              pushNotification("Roomba", "Roomba has FINISHED cleaning at: " + Timestamp)
                                              sendMail(mailTo, "Roomba", "Roomba has FINISHED cleaning at: " + Timestamp + "See attachment for details", "http://your_OH_ip:port/static/map.png")
                                              ]
                                          }
        case "Stuck"                    : {
                                          pushNotification("Roomba", "HELP! Roomba is STUCK at: " + Timestamp)
                                          sendMail(mailTo, "Roomba", "HELP! Roomba is STUCK at: " + Timestamp + "See attachment for location", "http://your_OH_ip:port/static/map.png")
                                          }
    }
end

rule "Roomba Schedule Display"
when
    Item roomba_cycle changed or
    Item roomba_cleanSchedule_h changed or
    Item roomba_cleanSchedule_m changed
then
    logInfo("Roomba", "Roomba Schedule: Day " + roomba_cycle.state + " Hour: " + roomba_cleanSchedule_h.state + " Minute: " + roomba_cleanSchedule_m.state)
    var String schedule = ""
    var String days = (roomba_cycle.state as StringType).toString
    var String hours = (roomba_cleanSchedule_h.state as StringType).toString
    var String minutes = (roomba_cleanSchedule_m.state as StringType).toString
    val ArrayList daysOfWeek = newArrayList("Sun","Mon","Tues","Wed","Thur","Fri","Sat")
    val ArrayList<String> daysList = new ArrayList(days.replace("[","").replace("]","").replace("'","").split(","))
    val ArrayList<String> hoursList = new ArrayList(hours.replace("[","").replace("]","").split(","))
    val ArrayList<String> minutesList = new ArrayList(minutes.replace("[","").replace("]","").split(","))
    daysList.forEach[ item, i |
        if(item.trim() == "start") {
            schedule += daysOfWeek.get(i) + ": " + hoursList.get(i) + ":" + minutesList.get(i) + ", "
        }
    ]
    postUpdate(roomba_cleanSchedule, schedule.trim())
end
```
### Icons
I also have various roomba icons in /etc/openhab2/icons/classic

These are here in openhab/icons, copy them to /etc/openhab2/icons/classic.
items and transforms are there also.
### General
start_openhab_roomba is a bash script that starts roomba with the maps in the right location (on Ubuntu) for openhab2, you may have to change this location for other systems (windows, RPi, etc), depending on how you installed Openhab2. You need the mqtt binding installed as well.
In the above rules/sitemap replace `your_OH_ip:port` with your own Openhab2 ip and port - to use this from anywhere, these should be externally available (from outside your own network) addresses, otherwise you can only access then from within your own network (e-mail attachments should work though).

## ToDo's
I'm just using some roomba icons I found on the web, if you have better roomba icons, please let me know, I know these are not Roomba 980 icons...
Update the example map shown here, it's an older version, the new ones are a little nicer.
Write a nice web interface script. Done! (well a web map display anyway). See `roomba_map.html` - for openhab2 copy this to /etc/openhab2/html (same location as map.png will go in), now you can see the live maps via `http://your_OH_ip:port/static/roomba_map.html` in your browser. I use a subdirectory to avoid cluttering the root html directory, just be consistent in the pathnames, and make sure the directory exists (with write permission) before running roomba.py!
