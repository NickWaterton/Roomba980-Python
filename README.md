Roomba980-Python
================

Unofficial iRobot Roomba python library (SDK).

Thanks to https://github.com/koalazak/dorita980 where much of the inner workings were derived from.
Thanks to Matthew Garrett <mjg59@srcf.ucam.org> for figuring out how to get passwords from iRobots aws cloud.

**NEW V2.0c 16/3/2021** All new re-write.  
**NEW 9/12/2021** Updated password.py can now get passwords for robots from the cloud  
**NEW 19/6/2024: Support for Python 3.6 and earlier is now dropped**

**NOTE: With the latest release of firmware (3.20.7) Robots are no longer reporting tracking information, therefore realtime maps will not work**

## New Features
* Now re-written as asyncio application
* Only Python 3.7 and above are supported
* supports 600, 900, i, and s series Roombas (all WiFi connected roombas)
* Supports M6 Mop
* new support for all configurations in config file (*config.ini* default)
* better blid and password discovery, supports multiple robots discovery/config
* Supports Multiple Roombas or Mops, any combination
* supports self emptying base
* New web interface for experimenting with real-time mapping
* support V2.XX and 3.XX firmware
* Supports Floor Plans for overlay on map
* Can now get passwords from the cloud

## Important!
Only local connections are supported. The project was written to allow Openhab2 control, so if you integrate Roomba into Openhab2, you can control it from anywhere.

As only **one connection at at time is** allowed to the Roomba local mqtt server, when the library is connected to your Roomba, the app will connect via the cloud.

Tested with Python 3.10/Ubuntu 22.04
* Python 3.7 or above is required
* Python 2.x is not supported, please use the old version of Roomba980 for Python 2.7 compatibility
* I have not tested on Windows, or anything othe than Ubuntu 18.04. use at your own risk on any other platform/OS
* PyPi install is not supported (yet) The version on PyPi is the 1.x version!

## Features
* Get your username/password easily (for multiple robots)
* Auto discovery robot IP (optional)
* Local API control
* Remote API control (via your MQTT broker)
* remote API control via REST interface (with web interface enabled)
* Ability to send command to clean specific rooms (zones)
* Json supported as command (so you can make your own commands)
* **NOT Firmware 1.6.x compatible.**
* Firmware 2.x.x/3.x.x compatible.
* Multiple Roombas/Mops supported
* Live Maps
* Maps show locations of errors, bin full, cancelled runs
* Supports Floor Plans for overlay on map
* designed for openhab2 compatibility
* HA compatibility
* Built in Web Server for interactive control/Mapping
* Simulation mode topic for easier debugging

## Live Maps
Live tracking of Roomba location and track, updated in real time:
![iRobot Roomba cleaning map using roomba lib](/roomba/res/map.png)

This is a comparison of the actual Roomba track (left) vs the Rooba app generated map (right):
![iRobot Roomba cleaning map comparison](/roomba/res/side_by_side_map.png)

**NOTE:** Later Roombas only update their position every 5 seconds - they can move a long way in this time, so apparent "gaps" in the floor coverage may not be real.
### OpenCV
If you have OpenCV installed, the library will use it to render the final map (on completion/error), it uses PIL for Live Maps, so the final map looks nicer. **This uses a lot of processing power/memory**, I don't know what happens if you try this on a RPi or other limited platform!
Also, if you enable debugging mode (-D), intermediate maps (edges.png, final_map.png and so on) are drawn every time a new co-ordinate is reported (every second or so when running). This consumes a lot of resources **You have been warned!**.
### PIL
Please use the latest version of pillow (V 4.1.1 at least), there are some nasty memory leaks in text processing in earlier versions that will quickly use up all your RAM and make the program unresponsive.
The library will issue a warning if it detects an earlier version of PIL.

If you do not have PIL installed, the system will not draw maps (even if enabled), even if you have OpenCV. PIL is used for basic image manipulations. If you do not specifically enable maps, no maps will be drawn. `roomba.py` uses maps, but the class default is to disable maps, so in your own scripts, if you want maps, you have to enable them (after creating the object).

## Dependencies
The following libraries/modules are used. Some are optional:
* paho-mqtt   *optional*
* PIL/pillow  *optional*
* openCV      *optional*
* numpy       *optional (used by openCV)*
* aiohttp     *optional (used for optional web server)*
* requests    *optinal (used for cloud passwords)*

This script/library is intended to forward roomba data/commands to/from a local MQTT server (this is optional though). In this case, you need paho-mqtt installed
```bash
pip install paho-mqtt
```
If you want the REST interface, or the built in web server, you need aiohttp installed:
```bash
pip install aiohttp
```
For map drawing, you need at least PIL installed (preferably the latest version of pillow)
```bash
pip install pillow
```
For fancy maps, you need openCV installed (V2,3,4). The installation of this can be complex, so I leave that up to you. Maps works without it, but it's nicer with it.

In all cases `pip` may be `pip3` depending on your default python configuration

## Install
First you need python 3.6 or later installed and then:  
Clone this repository:
```bash
git clone https://github.com/NickWaterton/Roomba980-Python.git
cd Roomba980-Python/roomba
```
Make sure you have the dependancies listed in `Roomba980-Python/requirements.txt` installed. You can do this by running:
```bash
pip3 install -r ../requirements.txt
```
**Note:** This may be `pip3` depending on your configuration.

run `./roomba -h` (or `python3 ./roomba.py`) to get the available options. This is what you will get:

```bash
usage: roomba.py [-h] [-f CONFIGFILE] [-n ROOMBA_NAME] [-t TOPIC]
                 [-T BROKER_FEEDBACK] [-C BROKER_COMMAND] [-S BROKER_SETTING]
                 [-b BROKER] [-p PORT] [-U USER] [-P BROKER_PASSWORD]
                 [-R ROOMBA_IP] [-u BLID] [-w PASSWORD] [-wp WEBPORT]
                 [-i INDENT] [-l LOG] [-e] [-D] [-r] [-j] [-m] [-M MAPPATH]
                 [-sq MAX_SQFT] [-s MAPSIZE] [-fp FLOORPLAN] [-I ICONPATH]
                 [-o] [-x EXCLUDE] [--version]

Forward MQTT data from Roomba to local MQTT broker

optional arguments:
  -h, --help            show this help message and exit
  -f CONFIGFILE, --configfile CONFIGFILE
                        config file name (default: ./config.ini)
  -n ROOMBA_NAME, --roomba_name ROOMBA_NAME
                        optional Roomba name (default: "")
  -t TOPIC, --topic TOPIC
                        Roomba MQTT Topic to subscribe to (can use wildcards #
                        and + default: #)
  -T BROKER_FEEDBACK, --broker_feedback BROKER_FEEDBACK
                        Topic on broker to publish feedback to (default:
                        /roomba/feedback</name>)
  -C BROKER_COMMAND, --broker_command BROKER_COMMAND
                        Topic on broker to publish commands to (default:
                        /roomba/command</name>)
  -S BROKER_SETTING, --broker_setting BROKER_SETTING
                        Topic on broker to publish settings to (default:
                        /roomba/setting</name>)
  -b BROKER, --broker BROKER
                        ipaddress of MQTT broker (default: None)
  -p PORT, --port PORT  MQTT broker port number (default: 1883)
  -U USER, --user USER  MQTT broker user name (default: None)
  -P BROKER_PASSWORD, --broker_password BROKER_PASSWORD
                        MQTT broker password (default: None)
  -R ROOMBA_IP, --roomba_ip ROOMBA_IP
                        ipaddress of Roomba (default: 255.255.255.255)
  -u BLID, --blid BLID  Roomba blid (default: None)
  -w PASSWORD, --password PASSWORD
                        Roomba password (default: None)
  -wp WEBPORT, --webport WEBPORT
                        Optional web server port number (default: None)
  -i INDENT, --indent INDENT
                        Default indentation=auto
  -l LOG, --log LOG     path/name of log file (default: ./roomba.log)
  -e, --echo            Echo to Console (default: True)
  -D, --debug           debug mode
  -r, --raw             Output raw data to mqtt, no decoding of json data
                        (default: False)
  -j, --pretty_print    pretty print json in logs (default: False)
  -m, --drawmap         Draw Roomba cleaning map (default: True)
  -M MAPPATH, --mappath MAPPATH
                        Location to store maps to (default: .)
  -sq MAX_SQFT, --max_sqft MAX_SQFT
                        Max Square Feet of map (default: 0)
  -s MAPSIZE, --mapsize MAPSIZE
                        Map Size, Dock offset and skew for the map.(800,1500)
                        is the size, (0,0) is the dock location, in the center
                        of the map, 0 is the rotation of the map, 0 is the
                        rotation of the roomba. Use single quotes around the
                        string. (default: "(800,1500,0,0,0,0)")
  -fp FLOORPLAN, --floorplan FLOORPLAN
                        Floorplan for Map. eg
                        ("res/first_floor.jpg",0,0,(1.0,1.0),0,
                        0.2)"res/first_floor.jpg" is the file name, 0,0 is the
                        x,y offset, (1.0, 1.0) is the (x,y) scale (or a single
                        number eg 1.0 for both), 0 is the rotation of the
                        floorplan, 0.2 is the transparencyUse single quotes
                        around the string. (default: None)
  -I ICONPATH, --iconpath ICONPATH
                        location of icons. (default:
                        "/home/nick/Scripts/Roomba980-Python/roomba/res")
  -o, --room_outline    Draw room outline (default: True)
  -x EXCLUDE, --exclude EXCLUDE
                        Exclude topics that have this in them (default: "")
  --version             Display version of this program

```
## quick start
With the roomba on the dock and charged (and connected to wifi), stand by the roomba and run
```bash
./roomba.py
```
or
```bash
python ./roomba.py
```
or
```bash
python3 ./roomba.py
```
Follow the instructions, the script will attempt to find the roomba, obtain the IP, blid, and password - then save these to a local configuration file (*config.ini* by default). If this works, the program will then start displaying messages from your Roomba, and printing the master_state every few seconds. the results are logged to a log file (`roomba.log` by default).  
**NOTE:** You will have to press and hold the HOME button on your robot until it plays a series of tones (about 2 seconds). Release the button and your robot will flash WIFI light to discover your Roomba.

On future runs (Once successful), these values will be taken from the configuration file, so you only have to do this once. You can manually specify these on the command line, some example start up bash scripts are supplied.
You can also edit the *config.ini* file, to add options for each defined robot.
I advise you to experiment with the map size (if you are using maps), as that is the one variable that isn't totally automatic. the size, position of the dock etc depend on your house layout.
the syntax of the map layout is (map x,map y, dock x, dock y, map rotation, roomba rotation). you can use the interactive [Web Server](#web-interface) to experiment with different settings to se what fits best.

### Example output
Logging is supported with the python standard logging module (the logger is `Roomba`)
```bash
[2021-02-05 12:42:06,718][ INFO](Roomba              ) *******************
[2021-02-05 12:42:06,719][ INFO](Roomba              ) * Program Started *
[2021-02-05 12:42:06,719][ INFO](Roomba              ) *******************
[2021-02-05 12:42:06,719][ INFO](Roomba              ) Roomba.py Version: 2.0a
[2021-02-05 12:42:06,720][ INFO](Roomba              ) Python Version: 3.6.9 (default, Oct  8 2020, 12:12:24) [GCC 8.4.0]
[2021-02-05 12:42:06,720][ INFO](Roomba              ) Paho MQTT Version: 1.5.1
[2021-02-05 12:42:06,720][ INFO](Roomba              ) CV Version: 3.2.0
[2021-02-05 12:42:06,720][ INFO](Roomba              ) PIL Version: 8.0.1
[2021-02-05 12:42:06,720][ INFO](Roomba              ) <CNTRL C> to Exit
[2021-02-05 12:42:06,721][ INFO](Roomba              ) Roomba MQTT data Interface
[2021-02-05 12:42:06,721][ INFO](Roomba.Password     ) Using Password version 2.0a
[2021-02-05 12:42:06,722][ INFO](Roomba.Password     ) reading/writing info from config file ./config.ini
[2021-02-05 12:42:06,723][ INFO](Roomba.Password     ) 3 Roombas Found
[2021-02-05 12:42:06,724][ INFO](Roomba              ) Creating Roomba object 192.168.100.181, Upstairs
[2021-02-05 12:42:06,725][ INFO](Roomba.Password     ) Using Password version 2.0a
[2021-02-05 12:42:06,949][ INFO](Roomba.Upstairs.api ) starting api WEB Server V2.0a on port 8200
[2021-02-05 12:42:06,950][ INFO](Roomba.Upstairs     ) Posting DECODED data
[2021-02-05 12:42:06,951][ INFO](Roomba.Upstairs     ) MAP: Maps Enabled
[2021-02-05 12:42:06,953][ INFO](Roomba              ) Creating Roomba object 192.168.100.206, Downstairs
[2021-02-05 12:42:06,955][ INFO](Roomba.Password     ) Using Password version 2.0a
[2021-02-05 12:42:06,958][ INFO](Roomba.Downstairs.api) starting api WEB Server V2.0a on port 8201
[2021-02-05 12:42:06,960][ INFO](Roomba.Downstairs   ) Posting DECODED data
[2021-02-05 12:42:06,968][ INFO](Roomba.Downstairs   ) MAP: Maps Enabled
[2021-02-05 12:42:06,973][ INFO](Roomba              ) Creating Roomba object 192.168.100.79, Mopster
[2021-02-05 12:42:06,982][ INFO](Roomba.Password     ) Using Password version 2.0a
[2021-02-05 12:42:06,994][ INFO](Roomba.Mopster.api  ) starting api WEB Server V2.0a on port 8202
[2021-02-05 12:42:06,997][ INFO](Roomba.Mopster      ) Posting DECODED data
[2021-02-05 12:42:07,002][ INFO](Roomba.Downstairs   ) subscribed to /roomba/command/Downstairs/#, /roomba/setting/Downstairs/#
[2021-02-05 12:42:07,003][ INFO](Roomba.Mopster      ) MAP: Maps Enabled
[2021-02-05 12:42:07,005][ INFO](Roomba.Upstairs     ) subscribed to /roomba/command/Upstairs/#, /roomba/setting/Upstairs/#
[2021-02-05 12:42:07,016][ INFO](Roomba.Downstairs   ) Connecting...
[2021-02-05 12:42:07,038][ INFO](Roomba.Downstairs   ) Setting TLS
[2021-02-05 12:42:07,041][ INFO](Roomba.Mopster      ) subscribed to /roomba/command/Mopster/#, /roomba/setting/Mopster/#
[2021-02-05 12:42:07,044][ INFO](Roomba.Downstairs   ) Setting TLS - OK
[2021-02-05 12:42:07,053][ INFO](Roomba.Upstairs     ) Connecting...
[2021-02-05 12:42:07,061][ INFO](Roomba.Upstairs     ) Setting TLS
[2021-02-05 12:42:07,063][ INFO](Roomba.Upstairs     ) Setting TLS - OK
[2021-02-05 12:42:07,072][ INFO](Roomba.Mopster      ) Connecting...
[2021-02-05 12:42:07,080][ INFO](Roomba.Mopster      ) Setting TLS
[2021-02-05 12:42:07,083][ INFO](Roomba.Mopster      ) Setting TLS - OK
[2021-02-05 12:42:07,206][ INFO](Roomba.Upstairs     ) MAP: opening existing map_notext.png
[2021-02-05 12:42:07,210][ INFO](Roomba.Mopster      ) MAP: opening existing map_notext.png
[2021-02-05 12:42:07,211][ INFO](Roomba.Downstairs   ) MAP: opening existing map_notext.png
[2021-02-05 12:42:07,302][ INFO](Roomba.Mopster      ) MAP: home_pos: (675,80)
[2021-02-05 12:42:07,302][ INFO](Roomba.Mopster      ) MAP: Initialisation complete
[2021-02-05 12:42:07,308][ INFO](Roomba.Downstairs   ) MAP: home_pos: (675,800)
[2021-02-05 12:42:07,309][ INFO](Roomba.Downstairs   ) MAP: Initialisation complete
[2021-02-05 12:42:07,312][ INFO](Roomba.Upstairs     ) MAP: home_pos: (300,300)
[2021-02-05 12:42:07,312][ INFO](Roomba.Upstairs     ) MAP: Initialisation complete
[2021-02-05 12:42:07,573][ INFO](Roomba.Mopster      ) Roomba Connected
[2021-02-05 12:42:07,679][ INFO](Roomba.Downstairs   ) Roomba Connected
[2021-02-05 12:42:07,788][ INFO](Roomba.Mopster      ) Received Roomba Data: $aws/things/ABCDEFGHGIXXXXXXXXXXXXXXXXXXXX/shadow/update, b'{"state":{"reported":{"batPct": 100, "batteryType": "F12432784", "batInfo": {"mDate": "2020-7-27", "mName": "F12432784", "mDaySerial": 2482, "mData": "303030393034303200000000000000000000000000", "mLife": "0BD10B64100C0D7F352A000703C3F6660071FEE81D130000000003A700000000", "cCount": 6, "afCount": 0}, "batAuthEnable": true, "bbchg": {"nChatters": 0, "nKnockoffs": 3, "nLithF": 2, "nChgOk": 24, "aborts": [0, 13, 0], "smberr": 0}, "bbchg3": {"estCap": 1913, "nAvail": 49, "hOnDock": 968, "avgMin": 55}, "bbmssn": {"aCycleM": 40, "nMssnF": 4, "nMssnC": 1, "nMssnOk": 31, "aMssnM": 46, "nMssn": 36}, "bbnav": {"aMtrack": 0, "nGoodLmrks": 0, "aGain": 0, "aExpo": 0}, "bbpause": {"pauses": [24, 18, 24, 18, 104, 104, 19, 18, 35, 46]}, "bbrun": {"nOvertemps": 0, "nCBump": 0, "nWStll": 0, "nPanics": 0, "nStuck": 22, "nPicks": 50, "sqft": 41, "min": 55, "hr": 20, "nCliffsF": 1042, "nCliffsR": 0}, "bbswitch": {"nBumper": 22526, "nDrops": 146, "nDock": 0, "nSpot": 0, "nClean": 17}, "bbsys": {"min": 43, "hr": 1009}, "behaviorFwk": true, "cap": {"edge": 0, "maps": 3, "pmaps": 5, "tHold": 1, "tLine": 2, "area": 1, "eco": 1, "multiPass": 2, "pose": 1, "team": 1, "pp": 0, "lang": 2, "5ghz": 1, "prov": 3, "sched": 1, "svcConf": 1, "ota": 2, "log": 2, "langOta": 0, "tileScan": 1}, "carpetBoost": false, "cleanMissionStatus": {"cycle": "none", "phase": "charge", "expireM": 0, "rechrgM": 0, "error": 0, "notReady": 0, "mssnM": 0, "expireTm": 0, "rechrgTm": 0, "mssnStrtTm": 0, "initiator": "none", "nMssn": 36}, "cleanSchedule2": [], "cloudEnv": "prod", "connected": true, "country": "CA", "deploymentState": 0, "detectedPad": "reusableWet", "dock": {"known": true}, "ecoCharge": false, "hwPartsRev": {"mobBrd": 11, "mobBlid": "XXXXXXXXXXXXXXXXXXXX", "navSerialNo": "CD00GHGV", "wlan0HwAddr": "50:14:41:69:c2:5d", "NavBrd": 1}, "hwDbgr": {"swVer": "", "hw": "", "status": 0}, "langs": null, "langs2": {"sVer": "1.0", "dLangs": {"ver": "0.20", "langs": ["cs-CZ", "da-DK", "de-DE", "en-GB", "en-US", "es-ES", "es-XL", "fi-FI", "fr-CA", "fr-FR", "he-IL", "it-IT", "ja-JP", "ko-KR", "nb-NO", "nl-NL", "pl-PL", "pt-BR", "pt-PT", "ru-RU", "sv-SE", "zh-CN", "zh-HK", "zh-TW"]}, "sLang": "en-US", "aSlots": 0}, "language": null, "lastCommand": {"command": null, "time": null, "initiator": null}, "lastDisconnect": 1, "mapUploadAllowed": true, "missionTelemetry": {"aux_comms": 1, "bat_stats": 1, "camera_settings": 1, "map_hypotheses": 1, "map_load": 1, "vital_stats": 1, "vslam_report": 1}, "mopReady": {"tankPresent": true, "lidClosed": true}, "name": "Mopster", "noAutoPasses": false, "noPP": false, "openOnly": false, "padWetness": {"disposable": 2, "reusable": 2}, "pmapLearningAllowed": true, "pmaps": [{"v3R-QnaqSQi3p1LIhEwWRA": "210205T030726"}, {"nL9mAMMXRmiEc1Q5ZWDNZQ": "210131T174925"}], "pmapCL": true, "pmapFmt": "3", "rankOverlap": 67, "sceneRecog": 1, "schedHold": false, "secureBoot": {"log": 2, "flip": 0, "sbl1Ver": "B3.2.02_PPUB", "stublVer": "B3.2.02_PPUB", "efuse": 1, "blType": 1, "enforce": 2, "lastRst": "200000001", "recov": "linux+2.4.2+sanmarino-release-rt320+11", "idSwitch": 0}, "sku": "m611220", "softwareVer": "sanmarino+3.12.8+sanmarino-release-420+12", "subModSwVer": {"nav": "sanmarino-nav+3.12.8+ubuntu-HEAD-09318572a78+12", "mob": "3.12.8+ubuntu-HEAD-09318572a78+12", "pwr": "0.3.0+ubuntu-HEAD-09318572a78+12", "sft": "1.2.0+SanMarino-Builds/SanMarino-Certified-Safety/sanmarino-safety-ca6f27d09c6+26", "mobBtl": "4.3", "linux": "linux+3.8.0.2+sanmarino-release-420+12", "con": "3.8.61-@8419265a/ubuntu"}, "svcEndpoints": {"svcDeplId": "v011"}, "tankLvl": 100, "timezone": "America/Toronto", "tls": {"tzbChk": 1, "privKType": 2, "lcCiphers": [0, 0, 0, 0, 0, 0, 0, 0, 0, 50380848]}, "twoPass": false, "tz": {"events": [{"dt": 1604232000, "off": -300}, {"dt": 1615705201, "off": -240}, {"dt": 1636264801, "off": -300}], "ver": 9}, "vacHigh": false}}}'
[2021-02-05 12:42:07,821][ INFO](Roomba.Mopster      ) current_state: None, current phase: charge, mission: none, mission_min: 0, recharge_min: 0, co-ords changed: False
[2021-02-05 12:42:07,823][ INFO](Roomba.Mopster      ) updated state to: Charging
[2021-02-05 12:42:07,824][ INFO](Roomba.Mopster      ) MAP: ignoring new co-ords in charge phase: {'x': 0, 'y': 0, 'theta': 180}
[2021-02-05 12:42:07,893][ INFO](Roomba.Downstairs   ) Received Roomba Data: $aws/things/ABCDEFGXXXXXXXXXXXXXXXXXXXXXXX/shadow/update, b'{"state":{"reported":{"batPct": 100, "batteryType": "F12432712", "batInfo": {"mDate": "2020-8-19", "mName": "F12432712", "mDaySerial": 560, "mData": "303031303035303300000000000000000000000000", "mLife": "0BE90B5410120C8D4A97000A0719EDBA0121FD531F110000000003B300000000", "cCount": 13, "afCount": 0}, "batAuthEnable": true, "bbchg": {"nChatters": 0, "nKnockoffs": 0, "nLithF": 0, "nChgOk": 40, "aborts": [0, 0, 0], "smberr": 0}, "bbchg3": {"estCap": 3474, "nAvail": 150, "hOnDock": 792, "avgMin": 65}, "bbmssn": {"aCycleM": 30, "nMssnF": 33, "nMssnC": 19, "nMssnOk": 26, "aMssnM": 62, "nMssn": 79}, "bbnav": {"aMtrack": 8, "nGoodLmrks": 18, "aGain": 11, "aExpo": 33}, "bbpause": {"pauses": [31, 31, 2, 31, 2, 31, 31, 31, 31, 31]}, "bbrun": {"nOvertemps": 0, "nCBump": 0, "nWStll": 0, "nMBStll": 1748, "nEvacs": 48, "nPanics": 116, "nPicks": 225, "nOpticalDD": 3, "nPiezoDD": 0, "nScrubs": 3, "nStuck": 103, "sqft": 51, "min": 39, "hr": 21, "nCliffsF": 7111, "nCliffsR": 0}, "bbswitch": {"nBumper": 36637, "nDrops": 706, "nDock": 52, "nSpot": 71, "nClean": 238}, "bbsys": {"min": 7, "hr": 905}, "behaviorFwk": true, "bin": {"present": true, "full": false}, "binPause": true, "cap": {"carpetBoost": 1, "binFullDetect": 2, "dockComm": 1, "edge": 0, "maps": 3, "pmaps": 5, "tLine": 2, "area": 1, "eco": 1, "multiPass": 2, "pose": 1, "team": 1, "pp": 0, "lang": 2, "5ghz": 1, "prov": 3, "sched": 1, "svcConf": 1, "ota": 2, "log": 2, "langOta": 0, "tileScan": 1}, "carpetBoost": true, "cleanMissionStatus": {"cycle": "none", "phase": "charge", "expireM": 0, "rechrgM": 0, "error": 0, "notReady": 0, "mssnM": 0, "expireTm": 0, "rechrgTm": 0, "mssnStrtTm": 1612533591, "initiator": "schedule", "nMssn": 79}, "cleanSchedule2": [{"enabled": true, "type": 0, "start": {"day": [5], "hour": 9, "min": 0}, "cmd": {"command": "start", "params": {"team": {"team_id": "watA6YF2"}}}}, {"enabled": true, "type": 0, "start": {"day": [1], "hour": 9, "min": 0}, "cmd": {"command": "start", "params": {"team": {"team_id": "lmoTXfAD"}}}}, {"enabled": true, "type": 0, "start": {"day": [2, 4], "hour": 9, "min": 0}, "cmd": {"command": "start", "ordered": 1, "pmap_id": "3w7_8thVQomB2wTwI7PSVQ", "regions": [{"region_id": "5", "type": "rid"}], "user_pmapv_id": "210110T000133"}}, {"enabled": true, "type": 0, "start": {"day": [3], "hour": 9, "min": 0}, "cmd": {"command": "start"}}], "cloudEnv": "prod", "connected": true, "country": "CA", "deploymentState": 0, "dock": {"known": true, "pn": "unknown", "state": 301, "id": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX", "fwVer": "3.3.6"}, "evacAllowed": true, "ecoCharge": false, "hwPartsRev": {"csscID": 1, "mobBrd": 7, "mobBlid": "XXXXXXXXXXXXXXXXXXXXXXXXXXXX", "navSerialNo": "CE00A1X2V", "wlan0HwAddr": "50:14:79:72:2e:7a", "NavBrd": 0}, "hwDbgr": {"swVer": "", "hw": "", "status": 0}, "langs": null, "langs2": {"sVer": "1.0", "dLangs": {"ver": "0.20", "langs": ["cs-CZ", "da-DK", "de-DE", "en-GB", "en-US", "es-ES", "es-XL", "fi-FI", "fr-CA", "fr-FR", "he-IL", "it-IT", "ja-JP", "ko-KR", "nb-NO", "nl-NL", "pl-PL", "pt-BR", "pt-PT", "ru-RU", "sv-SE", "zh-CN", "zh-HK", "zh-TW"]}, "sLang": "en-US", "aSlots": 0}, "language": null, "lastCommand": {"command": "start", "initiator": "schedule", "time": 1612533600, "params": {"team": {"team_id": "ypRG6GK1"}}, "robot_id": null, "select_all": null}, "lastDisconnect": 2, "mapUploadAllowed": true, "missionTelemetry": {"aux_comms": 1, "bat_stats": 1, "camera_settings": 1, "map_hypotheses": 1, "map_load": 1, "vital_stats": 1, "vslam_report": 1}, "mssnNavStats": {"nMssn": 79, "gLmk": 18, "lmk": 3, "reLc": 0, "plnErr": "none", "mTrk": 8, "kdp": 1, "sfkdp": 0, "nmc": 2, "nmmc": 1, "nrmc": 0, "mpSt": "idle", "l_drift": 0, "h_drift": 0, "l_squal": 90, "h_squal": 0}, "name": "Downstairs", "noAutoPasses": false, "noPP": false, "openOnly": false, "pmapLearningAllowed": true, "pmaps": [{"QpjbGUqlZv-Cmf-Geq9HAw": "210205T153623"}], "pmapCL": true, "pmapFmt": "3", "rankOverlap": 15, "sceneRecog": 1, "schedHold": false, "secureBoot": {"log": 2, "flip": 0, "sbl1Ver": "B3.2.02_PPUB", "stublVer": "B3.2.02_PPUB", "efuse": 1, "blType": 1, "enforce": 2, "lastRst": "200000000040", "recov": "linux+2.4.2+soho-release-rt320+11", "idSwitch": 0}, "sku": "s955020", "softwareVer": "soho+3.12.8+soho-release-420+12", "subModSwVer": {"nav": "soho-nav+3.12.8+ubuntu-HEAD-09318572a78+12", "mob": "3.12.8+ubuntu-HEAD-09318572a78+12", "bmp": "2.0.1+ubuntu-HEAD-09318572a78+12", "pwr": "1.14.27+ubuntu-HEAD-09318572a78+12", "sft": "1.2.0+Soho-Builds/Soho-Certified-Safety/soho-safety-ca6f27d09c6+27", "mobBtl": "4.2", "linux": "linux+3.8.0.2+soho-release-420+12", "con": "3.8.61-@8419265a/ubuntu"}, "svcEndpoints": {"svcDeplId": "v011"}, "timezone": "America/Toronto", "tls": {"tzbChk": 1, "privKType": 2, "lcCiphers": [0, 0, 0, 0, 0, 0, 0, 0, 0, 50380848]}, "twoPass": false, "tz": {"events": [{"dt": 1604232000, "off": -300}, {"dt": 1615705201, "off": -240}, {"dt": 1636264801, "off": -300}], "ver": 9}, "vacHigh": false}}}'
[2021-02-05 12:42:07,932][ INFO](Roomba.Downstairs   ) current_state: None, current phase: charge, mission: none, mission_min: 222, recharge_min: 0, co-ords changed: False
[2021-02-05 12:42:07,933][ INFO](Roomba.Downstairs   ) updated state to: Charging
[2021-02-05 12:42:07,934][ INFO](Roomba.Downstairs   ) MAP: ignoring new co-ords in charge phase: {'x': 0, 'y': 0, 'theta': 180}
```

**NOTE:** If you get an error like:
```bash
[ERROR](Roomba.Upstairs     ) Connection Error: _ssl.c:835: The handshake operation timed out
or
[ERROR](Roomba.Upstairs     ) Connection Error: timed out
```
It usually means something else is already connected to the Roomba, force close the app, and **reboot the roomba** (press and hold the *Clean* button for 20 seconds). You should then be able to connect.

## How to get your username/blid and password
You can get it automatically as described in quick start, or you can run:
```bash
./password.py
```
either with or without the IP address of your roomba.
```bash
./password.py -R <roomba IP>
```
You can also specify a config file other than the default (-h for options). Results are displayed and saved to the config file.
**NEW:** iRobot has changed the way passwords are retrieved in the latest firmware (3.20.7) see below for a workaround.

### Getting your username/blid and password from the iRobot cloud
You need the requests library installed for this to work:
```bash
pip3 install requests
```

To get the blid and password from the cloud run:
```bash
./password.py <login> <password>
```
Where `<login>` and `<password>` are your iRobot account login and password. Results are displayed and saved to the config file.

## config.ini
By default, all settings are stored in the *config.ini* file. You can change this file if you like (but there is really no need).  
An exaple file *config_example.ini* is given to show the structure of the file. It is a standard `ini` file with each section being the ip address of each robot.  
Any setting that can be added on the command line can be entered in the *config.ini* file. The key is the same as the long format of the cli setting. This allows you to make different settings for different robots.  
**NOTE:** Anything entered in the *config.ini* file overrides the command line setting.

## API
The API calls are properties or methods of two classes (see `roomba_direct.py` for an example of how to use the password class)
* password
* Roomba

In practice you should only need to use the Roomba class, which contains a reference to the password class (the *get_passwd* property).
### Classes
```python
password(address='255.255.255.255', file="./config.ini")
Roomba(address=None, blid=None, password=None, topic="#", roombaName="", file="./config.ini", log=None, webport=None)
```
If you have a *config.ini* file, you just need to supply *address* (ip address of the robot), the *blid* and *password* and *roombaName* will be filled in from info in the *config.ini* file.
### Roomba methods/properties
There are now async methods as well  
**NOTE:** *set_cleanSchedule* needs more work for i, M and s series  
**NOTE:** *auto_rotate* has been removed, as it was proving difficult to support
#### Sync methods
```python
connect()
disconnect()
send_command(command)
set_preference(preference, setting)
set_mqtt_client(mqttc=None, brokerFeedback="")
set_options(raw=False, indent=0, pretty_print=False, max_sqft=0)
set_cleanSchedule(schedule)
get_property(property, cap=False)
enable_map(enable=False, mapSize="(800,1500,0,0,0,0)",
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
           roomba_size=(50,50), draw_edges = 30, auto_rotate=False)
```
#### Async methods
```python
async_connect()
async_send_command(command)
async_set_preference(preference, setting)
async_set_cleanSchedule(setting)
get_settings(items)
```
#### Properties/Structures
```python
#boolean
roomba_connected
bin_full
#string
cleanMissionStatus_phase    #same as phase
current_state
error_message
sku
phase
mission
#dictionarys/lists
cleanMissionStatus
co_ords
pose
cap
pmaps
regions
master_state
#numbers:
batPct
rechrgM
mssnM
expireM
pcent_complete
```
### Notes
If you have multiple roomba's, each roomba has it's own name, and this will be automatically used to differentiate them. feedback is published to `\roomba\feedback\<roomba name>\`, commands go to `\roomba\command\<roomba name>` and settings to `\roomba\setting\<roomba name>`. Maps and so on have <roomba name> prepended to them.
You can manually specify the roomba name when you create the object, *as long as you specify blid and password as well*.
If you only supply the *address*, all other values will be retrieved from the *config.ini* file if you have one, and will override your other settings, including *roombaName* and *webport* (if *webport* is defined in *config.ini*).

## Using the library in your python script
Both these scripts are in the examples directory, as simple.py and complicated.py. To use them, copy them from examples to the main roomba.py directory. Edit them to include your own roomba ip address, blid and password, and run `python simple.py`. For "complicated.py" you also need to add your mqtt broker adddress, username, and password. Then run `python complicated.py`  
You will need an event loop running, to use the interface.
### Simple Version
```python
import asyncio
import json
import logging
from roomba import Roomba

#Uncomment the following two lines to see logging output
#logging.basicConfig(level=logging.INFO, 
#      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

#uncomment the option you want to run, and replace address, blid and roombaPassword with your own values

address = "192.168.1.181"
blid = "38XXXXXXXX850"
roombaPassword = ":1:1492XXX243:gOXXXXXXXD1xJ"

myroomba = Roomba(address, blid, roombaPassword)
#or myroomba = Roomba(address) #if you have a config file - will attempt discovery if you don't

async def test():
    myroomba.connect()
    #myroomba.set_preference("carpetBoost", "true")
    #myroomba.set_preference("twoPass", "false")

    #myroomba.send_command("start")
    #myroomba.send_command("stop")
    #myroomba.send_command("dock")

    import json, time
    for i in range(10):
        print(json.dumps(myroomba.master_state, indent=2))
        await asyncio.sleep(1)
    myroomba.disconnect()
    
loop = asyncio.get_event_loop()
loop.run_until_complete(test())
```
### More Complicated Version
```python
import asyncio
from roomba import Roomba
import paho.mqtt.client as mqtt
import time
import json
import logging

#Uncomment the following two lines to see logging output
logging.basicConfig(level=logging.INFO, 
      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

#put your own values here
broker = 'localhost'    #ip of mqtt broker
user = 'user'           #mqtt username
password = 'password'   #mqtt password
#broker = None if not using local mqtt broker
address = '192.168.1.181'
blid = "38XXXXXXXX850"
roombaPassword = ":1:1492XXX243:gOXXXXXXXD1xJ"

loop = asyncio.get_event_loop()

myroomba = Roomba(address)  #minnimum required to connect on Linux Debian system, will read connection from config file
#myroomba = Roomba(address, blid, roombaPassword)  #setting things manually

#all these are optional, if you don't include them, the defaults will work just fine
#if you are using maps
myroomba.enable_map(enable=True, mapSize="(800,1650,-300,-50,2,0)", mapPath="./", iconPath="./res")  #enable live maps, class default is no maps
if broker is not None:
    myroomba.setup_mqtt_client(broker, 1883, user, password, '/roomba/feedback') #if you want to publish Roomba data to your own mqtt broker (default is not to) if you have more than one roomba, and assign a roombaName, it is addded to this topic (ie /roomba/feedback/roombaName)
#finally connect to Roomba - (required!)
myroomba.connect()

print("<CMTRL C> to exit")
print("Subscribe to /roomba/feedback/# to see published data")

try:
    loop.run_forever()

except (KeyboardInterrupt, SystemExit):
    print("System exit Received - Exiting program")
    myroomba.disconnect()
```
See `roomba_direct.py` for a more detailed example, and how to handle multiple roombas

## Data/Feedback
master_state starts empty, and fills with time, it is published in full every 5 minutes by default (but updates to it are published live)  
master_state should contain (for Romba 600/900 series):
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
There are diferent entries/values for i and s series.  
in raw mode, the json from the Roomba is passed directly to the mqtt topic (usually /roomba/feedback/<roombaname>), in normal mode, each json item is decoded and published as a seperate topic. To see the topic published and their values run:
```bash
mosquitto_sub -v -t /roomba/feedback/#
```
Output should look like this (if your roomba does not have a name):
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
Your Roomba should have a name, in which case you get:
```bash
/roomba/feedback/Mopster/roomba_percent_complete 17
/roomba/feedback/Mopster/state Charging
/roomba/feedback/Mopster/signal_rssi -56
/roomba/feedback/Mopster/signal_snr 34
/roomba/feedback/Mopster/signal_noise -90
/roomba/feedback/Mopster/roomba_percent_complete 17
/roomba/feedback/Mopster/state Charging
/roomba/feedback/Mopster/signal_rssi -57
/roomba/feedback/Mopster/signal_snr 33
/roomba/feedback/Mopster/signal_noise -90
/roomba/feedback/Mopster/roomba_percent_complete 17
/roomba/feedback/Mopster/state Charging
/roomba/feedback/Upstairs/signal_rssi -55
/roomba/feedback/Upstairs/signal_snr 32
/roomba/feedback/Upstairs/roomba_percent_complete 0
/roomba/feedback/Upstairs/state Charging
/roomba/feedback/Upstairs/signal_rssi -55
/roomba/feedback/Upstairs/signal_snr 33
/roomba/feedback/Upstairs/roomba_percent_complete 0
/roomba/feedback/Upstairs/state Charging
```
In addition `state` and `error_message` are published which are derived by the class.

## Commands/Settings

* Commands are:
  * "start"
  * "stop"
  * "pause"
  * "resume"
  * "dock"
  * "evac" (only with clean base)
  * "reset"
  * "locate"
  
* Settings are:
  * carpetBoost true
  * vacHigh true
  * openOnly true   *this is edge clean - set to false to enable edge cleaning*
  * noAutoPasses true
  * twoPass true
  * binPause true

You publish this as a string to your mqtt broker topic /roomba/command/<roombaname> or /roomba/setting/<roombaname> (or whatever you have defined if you change these from default)
Ubuntu example (assuming the broker is on your localhost) - should work for any linux system with mosquitto installed (user and password may be required).
```bash
mosquitto_pub -t "/roomba/command/Upstairs" -m "start"
mosquitto_pub -t "/roomba/setting/Upstairs" -m "carpetBoost true"
```
Or call directly from a python script (see simple example above).  
Or use with the REST interface

# REST interface
To enable the REST interface, enter a value for `webport` in the Roomba contstructor. eg:
```bash
myroomba = Roomba(address, blid, roombaPassword, webport=8200)
```
The web interface is now available in a web browser at `http://localhost:8200/map/map.html`
## REST api
The end points for the REST api are:
* GET
    * /api/local/map/
    * /api/local/info/
    * /api/local/action/
    * /api/local/config/
* POST
    * /api/local/action/
    * /map/values

### GET usage
You can call the GET endpoints from a web browser, or via curl etc.
eg `http://localhost:8200/api/local/info/state` which will return the current state as json. Any sub setting can be used (such as `lastCommand`)
Where `localhost` is the ip/hostname of the host that the server is running on, and `8200` is the webport you set (individual to each roomba)

The `/api/local/map/` enpoint has two options `mapsize` and `outline`:
mapsize gives the current map size settings as json
outline gives the current roomba path as base 64 encoded png data (for use in web pages, I don't advise calling it directly).
The `/api/local/info/` endpoint accepts any configured value on the Roomba (eg `batInfo`, `cleanMissionStatus` etc, and returns json. It will return `null` for the value if the configuration does not exist.
eg for `cleanMissionStatus`:
```bash
{
"cleanMissionStatus": {
    "cycle": "none",
    "phase": "charge",
    "expireM": 0,
    "rechrgM": 0,
    "error": 0,
    "notReady": 0,
    "mssnM": 0,
    "expireTm": 0,
    "rechrgTm": 0,
    "mssnStrtTm": 1612533591,
    "initiator": "schedule",
    "nMssn": 79
    }
}
```
Notice the queried value is always returned as part of the json.
`/api/local/info` also accepts some special values. These are:
* 'sys'
* 'lastwireless'
* 'week'
* 'preferences'
* 'mission'
* 'missionbasic'
* 'wirelessconfig'
* 'wireless'
* 'cloud'

These give composite reports of multiple values (or are aliases for other settings).

`/api/local/action` allows you to send a command to the robot, such as `start` or `dock`
eg `http://localhost:8200/api/local/action/start` would start the roomba cleaning.  
You can also start the cleaning of a specific room by adding arguments for pmap_id and region:  
`http://localhost:8200/api/local/action/cleanRoom?pmap_id=HGAHGGSHGS&regions=1,2,3`
Would start cleaning region 1, 2 and 3 of pmap HGAHGGSHGS. if you leave `pmap_id` out, the first pmap found is used. You can use `pmaps` in `\api\local\info` to find out your pmaps. Which region is which you have to work out for your self. 
`cleanRoom` is an alias for `start`, it just makes the intention clearer.

`/api/local/config/` is the same as `/api/local/info` but the name queried is not returned as part of the json. eg `batInfo` returns:
```bash
{
    "mDate": "2020-8-19",
    "mName": "F12432712",
    "mDaySerial": 560,
    "mData": "303031303035303300000000000000000000000000",
    "mLife": "0BE90B5410120C8D4A97000A0719EDBA0121FD531F110000000003B300000000",
    "cCount": 13,
    "afCount": 0
}
```
and special values are not accepted. You can query any value in the roomba configuration, `null` is returned if it does not exist (or is null). 

## POST Usage
There are only two endpoints you can post to, and currently `/map/values` does nothing (future use).  
The only end point that it mnakes sense to post to is `/api/local/action/` which is used to send a command to the roomba. You can use GET to send simple commands (like `start`, `dock` etc), but if you want to send a more complex command, then you need to use json.
A complex command would look like this:
```json
{
"lastCommand": {
  "command": "clean",
  "time": 1612918962,
  "initiator": "alexa",
  "ordered": 1,
  "pmap_id": "v3R-QnXXXXXXXXXURA",
  "regions": [
    {
    "region_id": "5"
    }
  ],
  "user_pmapv_id": null,
  "robot_id": null,
  "select_all": null
  }
}
``` 
you can use `/api/local/info/lastCommand` to figure out what the format of the last command you sent was (and get the pmap_id and regions), and post your own json to `/api/local/action/` to replicate a command.  
You would POST:
```json
{
  "command": "clean",
  "time": 1612918962,
  "initiator": "alexa",
  "ordered": 1,
  "pmap_id": "v3R-QnXXXXXXXXXURA",
  "regions": [
    {
    "region_id": "5"
    }
  ],
  "user_pmapv_id": null,
  "robot_id": null,
  "select_all": null
}
``` 
To copy the last command example.  
Note that with this example, you could get the same result by using GET to `/api/local/action/cleanRoom?pmap_id=v3R-QnXXXXXXXXXURA&regions=5`, and if you only had one pmap, you could even leave that out - `/api/local/action/cleanRoom?regions=5` would do the same thing.

### Web Interface
The web interface can be used for debugging. You can watch value update as roomba runs, or is simulated. You can interactively change the size/rotation of the map, to get the values correct for your floor plan.  
It is available on `http://Your_Server_IP:webport/map/map.html` Each roomba would have it's own webport, which you specify at startup. See [REST Interface](#rest-interface) for details.  
The Web interface looks like this:  
**NOTE:** *Save values* currently just displays the entry you need to **manually** make in the *config.ini* file. it does not actually "save" anything. It may do in the future...

![iRobot Roomba Web Interface](/roomba/res/web_interface.png)
If you restart the server, you need to refresh/reload the web page.

## Openhab/Openhab2 Interface
Here are my Openhab2 files:
### things
```
Bridge mqtt:broker:proliant "Proliant" [ 
  host="Your_MQTT_broker_IP",
  port="1883",
  secure=false,
  //retainMessages=false,
  clientID="Openhab2_mqtt2"
]

//Roomba things
Thing mqtt:topic:upstairs_roomba "Upstairs Roomba"  (mqtt:broker:proliant) {
    Channels:
    /* Roomba Commands */
    Type string : roomba_command "Roomba" [ commandTopic="/roomba/command/Upstairs" ]
    /* Settings */
    Type switch : roomba_edgeClean    "Edge Clean"              [ commandTopic="/roomba/setting/Upstairs", stateTopic="/roomba/feedback/Upstairs/openOnly", transformationPattern="MAP:inverse_switch.map", formatBeforePublish="openOnly %s", on="false", off="true" ]
    Type switch : roomba_carpetBoost  "Auto carpet Boost"       [ commandTopic="/roomba/setting/Upstairs", stateTopic="/roomba/feedback/Upstairs/carpetBoost", transformationPattern="MAP:inverse_switch.map", formatBeforePublish="carpetBoost %s", on="false", off="true"  ]
    Type switch : roomba_vacHigh      "Vacuum Boost"            [ commandTopic="/roomba/setting/Upstairs", stateTopic="/roomba/feedback/Upstairs/vacHigh", transformationPattern="MAP:switch.map", formatBeforePublish="vacHigh %s", on="false", off="true"  ]
    Type switch : roomba_noAutoPasses "Auto Passes"             [ commandTopic="/roomba/setting/Upstairs", stateTopic="/roomba/feedback/Upstairs/noAutoPasses", transformationPattern="MAP:inverse_switch.map", formatBeforePublish="noAutoPasses %s", on="false", off="true"  ]
    Type switch : roomba_twoPass      "Two Passes"              [ commandTopic="/roomba/setting/Upstairs", stateTopic="/roomba/feedback/Upstairs/twoPass", transformationPattern="MAP:switch.map", formatBeforePublish="twoPass %s", on="false", off="true"  ]
    Type switch : roomba_binPause     "Always Complete (even if bin is full)" [ commandTopic="/roomba/setting/Upstairs", stateTopic="/roomba/feedback/Upstairs/binPause", transformationPattern="MAP:inverse_switch.map", formatBeforePublish="binPause %s", on="false", off="true"  ]
    /* Roomba Feedback */
    Type string : roomba_softwareVer "Software Version"         [ stateTopic="/roomba/feedback/Upstairs/softwareVer" ]
    Type number : roomba_batPct "Battery"                       [ stateTopic="/roomba/feedback/Upstairs/batPct" ]
    Type string : roomba_lastcommand  "Last Command"            [ stateTopic="/roomba/feedback/Upstairs/lastCommand_command" ]
    Type switch : roomba_bin_present "Bin Present"              [ stateTopic="/roomba/feedback/Upstairs/bin_present", transformationPattern="MAP:switch.map" ]
    Type switch : roomba_full "Bin Full"                        [ stateTopic="/roomba/feedback/Upstairs/bin_full", transformationPattern="MAP:switch.map" ]
    /* Mission values */
    Type string : roomba_mission  "Mission"                     [ stateTopic="/roomba/feedback/Upstairs/cleanMissionStatus_cycle" ]
    Type number : roomba_nMssn    "Cleaning Mission number"     [ stateTopic="/roomba/feedback/Upstairs/cleanMissionStatus_nMssn" ]
    Type string : roomba_phase    "Phase"                       [ stateTopic="/roomba/feedback/Upstairs/cleanMissionStatus_phase" ]
    Type string : roomba_initiator  "Initiator"                 [ stateTopic="/roomba/feedback/Upstairs/cleanMissionStatus_initiator" ]
    Type switch : roomba_error "Error"                          [ stateTopic="/roomba/feedback/Upstairs/cleanMissionStatus_error" ]
    Type string : roomba_errortext  "Error Message"             [ stateTopic="/roomba/feedback/Upstairs/error_message" ]
    Type number : roomba_mssnM "Cleaning Elapsed Time"          [ stateTopic="/roomba/feedback/Upstairs/cleanMissionStatus_mssnM" ]
    Type number : roomba_sqft "Square Ft Cleaned"               [ stateTopic="/roomba/feedback/Upstairs/cleanMissionStatus_sqft" ]
    Type number : roomba_percent_complete "Mission % complete"  [ stateTopic="/roomba/feedback/Upstairs/roomba_percent_complete" ]
    Type number : roomba_expireM "Mission Recharge Time"        [ stateTopic="/roomba/feedback/Upstairs/cleanMissionStatus_expireM" ]
    Type number : roomba_rechrgM "Remaining Time To Recharge"   [ stateTopic="/roomba/feedback/Upstairs/cleanMissionStatus_rechrgM" ]
    Type string : roomba_status    "Status"                     [ stateTopic="/roomba/feedback/Upstairs/state" ]
    /* Schedule */
    Type string : roomba_cycle   "Day of Week"                  [ stateTopic="/roomba/feedback/Upstairs/cleanSchedule_cycle" ]
    Type string : roomba_cleanSchedule_h   "Hour of Day"        [ stateTopic="/roomba/feedback/Upstairs/cleanSchedule_h" ]
    Type string : roomba_cleanSchedule_m   "Minute of Hour"     [ stateTopic="/roomba/feedback/Upstairs/cleanSchedule_m" ]
    Type string : roomba_cleanSchedule2    "New Schedule"       [ stateTopic="/roomba/feedback/Upstairs/cleanSchedule2" ]
    /* General */
    Type number : roomba_theta "Theta"                          [ stateTopic="/roomba/feedback/Upstairs/pose_theta" ]
    Type number : roomba_x "X"                                  [ stateTopic="/roomba/feedback/Upstairs/pose_point_x" ]
    Type number : roomba_y "Y"                                  [ stateTopic="/roomba/feedback/Upstairs/pose_point_y" ]
    Type number : roomba_rssi "RSSI"                            [ stateTopic="/roomba/feedback/Upstairs/signal_rssi" ]
}

Thing mqtt:topic:downstairs_roomba "Downstairs Roomba"  (mqtt:broker:proliant) {
    Channels:
    /* Roomba Commands */
    Type string : roomba_command "Roomba" [ commandTopic="/roomba/command/Downstairs" ]
    /* Settings */
    Type switch : roomba_edgeClean    "Edge Clean"              [ commandTopic="/roomba/setting/Downstairs", stateTopic="/roomba/feedback/Downstairs/openOnly", transformationPattern="MAP:inverse_switch.map", formatBeforePublish="openOnly %s", on="false", off="true" ]
    Type switch : roomba_carpetBoost  "Auto carpet Boost"       [ commandTopic="/roomba/setting/Downstairs", stateTopic="/roomba/feedback/Downstairs/carpetBoost", transformationPattern="MAP:inverse_switch.map", formatBeforePublish="carpetBoost %s", on="false", off="true"  ]
    Type switch : roomba_vacHigh      "Vacuum Boost"            [ commandTopic="/roomba/setting/Downstairs", stateTopic="/roomba/feedback/Downstairs/vacHigh", transformationPattern="MAP:switch.map", formatBeforePublish="vacHigh %s", on="false", off="true"  ]
    Type switch : roomba_noAutoPasses "Auto Passes"             [ commandTopic="/roomba/setting/Downstairs", stateTopic="/roomba/feedback/Downstairs/noAutoPasses", transformationPattern="MAP:inverse_switch.map", formatBeforePublish="noAutoPasses %s", on="false", off="true"  ]
    Type switch : roomba_twoPass      "Two Passes"              [ commandTopic="/roomba/setting/Downstairs", stateTopic="/roomba/feedback/Downstairs/twoPass", transformationPattern="MAP:switch.map", formatBeforePublish="twoPass %s", on="false", off="true"  ]
    Type switch : roomba_binPause     "Always Complete (even if bin is full)" [ commandTopic="/roomba/setting/Downstairs", stateTopic="/roomba/feedback/Downstairs/binPause", transformationPattern="MAP:inverse_switch.map", formatBeforePublish="binPause %s", on="false", off="true"  ]
    /* Roomba Feedback */
    Type string : roomba_softwareVer "Software Version"         [ stateTopic="/roomba/feedback/Downstairs/softwareVer" ]
    Type number : roomba_batPct "Battery"                       [ stateTopic="/roomba/feedback/Downstairs/batPct" ]
    Type string : roomba_lastcommand  "Last Command"            [ stateTopic="/roomba/feedback/Downstairs/lastCommand_command" ]
    Type switch : roomba_bin_present "Bin Present"              [ stateTopic="/roomba/feedback/Downstairs/bin_present", transformationPattern="MAP:switch.map" ]
    Type switch : roomba_full "Bin Full"                        [ stateTopic="/roomba/feedback/Downstairs/bin_full", transformationPattern="MAP:switch.map" ]
    /* Mission values */
    Type string : roomba_mission  "Mission"                     [ stateTopic="/roomba/feedback/Downstairs/cleanMissionStatus_cycle" ]
    Type number : roomba_nMssn    "Cleaning Mission number"     [ stateTopic="/roomba/feedback/Downstairs/cleanMissionStatus_nMssn" ]
    Type string : roomba_phase    "Phase"                       [ stateTopic="/roomba/feedback/Downstairs/cleanMissionStatus_phase" ]
    Type string : roomba_initiator  "Initiator"                 [ stateTopic="/roomba/feedback/Downstairs/cleanMissionStatus_initiator" ]
    Type switch : roomba_error "Error"                          [ stateTopic="/roomba/feedback/Downstairs/cleanMissionStatus_error" ]
    Type string : roomba_errortext  "Error Message"             [ stateTopic="/roomba/feedback/Downstairs/error_message" ]
    Type number : roomba_mssnM "Cleaning Elapsed Time"          [ stateTopic="/roomba/feedback/Downstairs/cleanMissionStatus_mssnM" ]
    Type number : roomba_sqft "Square Ft Cleaned"               [ stateTopic="/roomba/feedback/Downstairs/cleanMissionStatus_sqft" ]
    Type number : roomba_percent_complete "Mission % complete"  [ stateTopic="/roomba/feedback/Downstairs/roomba_percent_complete" ]
    Type number : roomba_expireM "Mission Recharge Time"        [ stateTopic="/roomba/feedback/Downstairs/cleanMissionStatus_expireM" ]
    Type number : roomba_rechrgM "Remaining Time To Recharge"   [ stateTopic="/roomba/feedback/Downstairs/cleanMissionStatus_rechrgM" ]
    Type string : roomba_status    "Status"                     [ stateTopic="/roomba/feedback/Downstairs/state" ]
    /* Schedule */
    Type string : roomba_cycle   "Day of Week"                  [ stateTopic="/roomba/feedback/Downstairs/cleanSchedule_cycle" ]
    Type string : roomba_cleanSchedule_h   "Hour of Day"        [ stateTopic="/roomba/feedback/Downstairs/cleanSchedule_h" ]
    Type string : roomba_cleanSchedule_m   "Minute of Hour"     [ stateTopic="/roomba/feedback/Downstairs/cleanSchedule_m" ]
    Type string : roomba_cleanSchedule2    "New Schedule"       [ stateTopic="/roomba/feedback/Downstairs/cleanSchedule2" ]
    /* General */
    Type number : roomba_theta "Theta"                          [ stateTopic="/roomba/feedback/Downstairs/pose_theta" ]
    Type number : roomba_x "X"                                  [ stateTopic="/roomba/feedback/Downstairs/pose_point_x" ]
    Type number : roomba_y "Y"                                  [ stateTopic="/roomba/feedback/Downstairs/pose_point_y" ]
    Type number : roomba_rssi "RSSI"                            [ stateTopic="/roomba/feedback/Downstairs/signal_rssi" ]
}

Thing mqtt:topic:downstairs_mop "Downstairs Braava Jet M6"  (mqtt:broker:proliant) {
    Channels:
    /* Braava Commands */
    Type string : roomba_command "Braava" [ commandTopic="/roomba/command/Mopster" ]
    /* Braava Feedback */
    Type string : roomba_softwareVer "Software Version"         [ stateTopic="/roomba/feedback/Mopster/softwareVer" ]
    Type number : roomba_batPct "Battery"                       [ stateTopic="/roomba/feedback/Mopster/batPct" ]
    Type string : roomba_lastcommand  "Last Command"            [ stateTopic="/roomba/feedback/Mopster/lastCommand_command" ]
    Type string : roomba_detectedPad  "Detected Pad"            [ stateTopic="/roomba/feedback/Mopster/detectedPad" ]
    Type switch : roomba_lid_closed "Lid Closed"                [ stateTopic="/roomba/feedback/Mopster/mopReady_lidClosed", transformationPattern="MAP:switch.map" ]
    Type switch : roomba_bin_present "Bin Present"              [ stateTopic="/roomba/feedback/Mopster/mopReady_tankPresent", transformationPattern="MAP:switch.map" ]
    Type number : roomba_tankLvl "Tank Level"                   [ stateTopic="/roomba/feedback/Mopster/tankLvl" ]
    Type number : roomba_padWetness_disposable "Disposable Pad Wetness" [ stateTopic="/roomba/feedback/Mopster/padWetness_disposable" ]
    Type number : roomba_padWetness_reusable   "Reusable Pad Wetness"   [ stateTopic="/roomba/feedback/Mopster/padWetness_reusable" ]
    /* Mission values */
    Type string : roomba_mission  "Mission"                     [ stateTopic="/roomba/feedback/Mopster/cleanMissionStatus_cycle" ]
    Type number : roomba_nMssn    "Cleaning Mission number"     [ stateTopic="/roomba/feedback/Mopster/cleanMissionStatus_nMssn" ]
    Type string : roomba_phase    "Phase"                       [ stateTopic="/roomba/feedback/Mopster/cleanMissionStatus_phase" ]
    Type string : roomba_initiator  "Initiator"                 [ stateTopic="/roomba/feedback/Mopster/cleanMissionStatus_initiator" ]
    Type switch : roomba_error "Error"                          [ stateTopic="/roomba/feedback/Mopster/cleanMissionStatus_error" ]
    Type string : roomba_errortext  "Error Message"             [ stateTopic="/roomba/feedback/Mopster/error_message" ]
    Type number : roomba_mssnM "Cleaning Elapsed Time"          [ stateTopic="/roomba/feedback/Mopster/cleanMissionStatus_mssnM" ]
    Type number : roomba_sqft "Square Ft Cleaned"               [ stateTopic="/roomba/feedback/Mopster/cleanMissionStatus_sqft" ]
    Type number : roomba_percent_complete "Mission % complete"  [ stateTopic="/roomba/feedback/Mopster/roomba_percent_complete" ]
    Type number : roomba_expireM "Mission Recharge Time"        [ stateTopic="/roomba/feedback/Mopster/cleanMissionStatus_expireM" ]
    Type number : roomba_rechrgM "Remaining Time To Recharge"   [ stateTopic="/roomba/feedback/Mopster/cleanMissionStatus_rechrgM" ]
    Type string : roomba_status    "Status"                     [ stateTopic="/roomba/feedback/Mopster/state" ]
    /* Schedule */
    Type string : roomba_cycle   "Day of Week"                  [ stateTopic="/roomba/feedback/Mopster/cleanSchedule_cycle" ]
    Type string : roomba_cleanSchedule_h   "Hour of Day"        [ stateTopic="/roomba/feedback/Mopster/cleanSchedule_h" ]
    Type string : roomba_cleanSchedule_m   "Minute of Hour"     [ stateTopic="/roomba/feedback/Mopster/cleanSchedule_m" ]
    Type string : roomba_cleanSchedule2    "New Schedule"       [ stateTopic="/roomba/feedback/Mopster/cleanSchedule2" ]
    /* General */
    Type number : roomba_theta "Theta"                          [ stateTopic="/roomba/feedback/Mopster/pose_theta" ]
    Type number : roomba_x "X"                                  [ stateTopic="/roomba/feedback/Mopster/pose_point_x" ]
    Type number : roomba_y "Y"                                  [ stateTopic="/roomba/feedback/Mopster/pose_point_y" ]
    Type number : roomba_rssi "RSSI"                            [ stateTopic="/roomba/feedback/Mopster/signal_rssi" ]
}
```

### Items
```
/* Roomba items */
Group roomba_items             "Roombas"                  <roomba>
Group downstairs_roomba_items  "Downstairs Roomba"        <roomba>        (roomba_items)
Group upstairs_roomba_items    "Upstairs Roomba"          <roomba>        (roomba_items)
Group mopster_roomba_items     "Downstairs Mop"           <roomba>        (roomba_items)

/* Upstairs Roomba Commands */
String upstairs_roomba_command "Roomba" <roomba> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_command" }
/* Settings */
Switch upstairs_roomba_edgeClean     "Edge Clean [%s]" <switch> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_edgeClean", autoupdate="false" }
Switch upstairs_roomba_carpetBoost   "Auto carpet Boost [%s]" <switch> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_carpetBoost", autoupdate="false" }
Switch upstairs_roomba_vacHigh       "Vacuum Boost [%s]" <switch> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_vacHigh", autoupdate="false" }
Switch upstairs_roomba_noAutoPasses  "Auto Passes [%s]" <switch> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_noAutoPasses", autoupdate="false" }
Switch upstairs_roomba_twoPass       "Two Passes [%s]" <switch> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_twoPass", autoupdate="false" }
Switch upstairs_roomba_binPause      "Always Complete (even if bin is full) [%s]" <switch> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_binPause", autoupdate="false" }
/* Roomba Feedback */
String upstairs_roomba_softwareVer   "Software Version [%s]" <text> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_softwareVer" }
Number upstairs_roomba_batPct  "Battery [%d%%]" <battery> (upstairs_roomba_items, Battery)  { channel="mqtt:topic:upstairs_roomba:roomba_batPct" }
String upstairs_roomba_lastcommand   "Last Command [%s]" <roomba> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_lastcommand" }
Switch upstairs_roomba_bin_present   "Bin Present [%s]" <trashpresent> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_bin_present" }
Switch upstairs_roomba_full    "Bin Full [%s]" <trash> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_full" }
/* Mission values */
String upstairs_roomba_mission   "Mission [%s]" <msg> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_mission" }
Number upstairs_roomba_nMssn     "Cleaning Mission Number [%d]" <number> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_nMssn" }
String upstairs_roomba_phase     "Phase [%s]" <msg> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_phase" }
String upstairs_roomba_initiator   "Initiator [%s]" <msg> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_initiator" }
Switch upstairs_roomba_error  "Error [%d]" <roombaerror> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_error" }
String upstairs_roomba_errortext   "Error Message [%s]" <msg> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_errortext" }
Number upstairs_roomba_mssnM  "Cleaning Elapsed Time [%d m]" <clock> (upstairs_roomba_items)  { channel="mqtt:topic:upstairs_roomba:roomba_mssnM" }
Number upstairs_roomba_sqft  "Square Ft Cleaned [%d]" <groundfloor> (upstairs_roomba_items)  { channel="mqtt:topic:upstairs_roomba:roomba_sqft" }
Number upstairs_roomba_expireM  "Mission Recharge Time [%d m]" <clock> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_expireM" }
Number upstairs_roomba_rechrgM  "Remaining Time To Recharge [%d m]" <clock> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_rechrgM" }
String upstairs_roomba_status     "Status [%s]" <msg> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_status" }
Number upstairs_roomba_percent_complete     "Mission % Completed [%d%%]" <humidity> (upstairs_roomba_items)  { channel="mqtt:topic:upstairs_roomba:roomba_percent_complete" }
DateTime upstairs_roomba_lastmissioncompleted  "Last Mission Completed [%1$ta %1$tR]" <calendar>
/* Schedule */
String upstairs_roomba_cycle    "Day of Week [%s]" <calendar> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_cycle" }
String upstairs_roomba_cleanSchedule_h    "Hour of Day [%s]" <clock> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_cleanSchedule_h" }
String upstairs_roomba_cleanSchedule_m    "Minute of Hour [%s]" <clock> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_cleanSchedule_m" }
String upstairs_roomba_cleanSchedule2     "Schedule [%s]" <clock> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_cleanSchedule2" }
String upstairs_roomba_cleanSchedule  "Schedule [%s]" <calendar> (upstairs_roomba_items)
/* General */
Switch upstairs_roomba_control  "Upstairs Roomba ON/OFF [%s]" <switch> (upstairs_roomba_items)
Number upstairs_roomba_theta  "Theta [%d]" <angle> (upstairs_roomba_items)  { channel="mqtt:topic:upstairs_roomba:roomba_theta" }
Number upstairs_roomba_x  "X [%d]" <map> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_x" }
Number upstairs_roomba_y  "Y [%d]" <map> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_y" }
Number upstairs_roomba_rssi  "RSSI [%d]" <network> (upstairs_roomba_items) { channel="mqtt:topic:upstairs_roomba:roomba_rssi" }
DateTime upstairs_roomba_lastheardfrom  "Last Update [%1$ta %1$tR]" <clock> { channel="mqtt:topic:upstairs_roomba:roomba_rssi" [profile="timestamp-update"] }

/* Downstairs Roomba Commands */
String downstairs_roomba_command "Roomba" <roomba> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_command" }
/* Settings */
Switch downstairs_roomba_edgeClean     "Edge Clean [%s]" <switch> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_edgeClean", autoupdate="false" }
Switch downstairs_roomba_carpetBoost   "Auto carpet Boost [%s]" <switch> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_carpetBoost", autoupdate="false" }
Switch downstairs_roomba_vacHigh       "Vacuum Boost [%s]" <switch> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_vacHigh", autoupdate="false" }
Switch downstairs_roomba_noAutoPasses  "Auto Passes [%s]" <switch> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_noAutoPasses", autoupdate="false" }
Switch downstairs_roomba_twoPass       "Two Passes [%s]" <switch> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_twoPass", autoupdate="false" }
Switch downstairs_roomba_binPause      "Always Complete (even if bin is full) [%s]" <switch> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_binPause", autoupdate="false" }
/* Roomba Feedback */
String downstairs_roomba_softwareVer   "Software Version [%s]" <text> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_softwareVer" }
Number downstairs_roomba_batPct  "Battery [%d%%]" <battery> (downstairs_roomba_items, Battery)  { channel="mqtt:topic:downstairs_roomba:roomba_batPct" }
String downstairs_roomba_lastcommand   "Last Command [%s]" <roomba> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_lastcommand" }
Switch downstairs_roomba_bin_present   "Bin Present [%s]" <trashpresent> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_bin_present" }
Switch downstairs_roomba_full    "Bin Full [%s]" <trash> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_full" }
/* Mission values */
String downstairs_roomba_mission   "Mission [%s]" <msg> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_mission" }
Number downstairs_roomba_nMssn     "Cleaning Mission Number [%d]" <number> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_nMssn" }
String downstairs_roomba_phase     "Phase [%s]" <msg> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_phase" }
String downstairs_roomba_initiator   "Initiator [%s]" <msg> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_initiator" }
Switch downstairs_roomba_error  "Error [%d]" <roombaerror> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_error" }
String downstairs_roomba_errortext   "Error Message [%s]" <msg> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_errortext" }
Number downstairs_roomba_mssnM  "Cleaning Elapsed Time [%d m]" <clock> (downstairs_roomba_items)  { channel="mqtt:topic:downstairs_roomba:roomba_mssnM" }
Number downstairs_roomba_sqft  "Square Ft Cleaned [%d]" <groundfloor> (downstairs_roomba_items)  { channel="mqtt:topic:downstairs_roomba:roomba_sqft" }
Number downstairs_roomba_expireM  "Mission Recharge Time [%d m]" <clock> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_expireM" }
Number downstairs_roomba_rechrgM  "Remaining Time To Recharge [%d m]" <clock> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_rechrgM" }
String downstairs_roomba_status     "Status [%s]" <msg> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_status" }
Number downstairs_roomba_percent_complete     "Mission % Completed [%d%%]" <humidity> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_percent_complete" }
DateTime downstairs_roomba_lastmissioncompleted  "Last Mission Completed [%1$ta %1$tR]" <calendar>
/* Schedule */
String downstairs_roomba_cycle    "Day of Week [%s]" <calendar> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_cycle" }
String downstairs_roomba_cleanSchedule_h    "Hour of Day [%s]" <clock> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_cleanSchedule_h" }
String downstairs_roomba_cleanSchedule_m    "Minute of Hour [%s]" <clock> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_cleanSchedule_m" }
String downstairs_roomba_cleanSchedule2     "Schedule [%s]" <clock> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_cleanSchedule2" }
String downstairs_roomba_cleanSchedule  "Schedule [%s]" <calendar> (downstairs_roomba_items)
/* General */
Switch downstairs_roomba_control  "Downstairs Roomba ON/OFF [%s]" <switch> (downstairs_roomba_items)
Number downstairs_roomba_theta  "Theta [%d]" <angle> (downstairs_roomba_items)  { channel="mqtt:topic:downstairs_roomba:roomba_theta" }
Number downstairs_roomba_x  "X [%d]" <map> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_x" }
Number downstairs_roomba_y  "Y [%d]" <map> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_y" }
Number downstairs_roomba_rssi  "RSSI [%d]" <network> (downstairs_roomba_items) { channel="mqtt:topic:downstairs_roomba:roomba_rssi" }
DateTime downstairs_roomba_lastheardfrom  "Last Update [%1$ta %1$tR]" <clock> { channel="mqtt:topic:downstairs_roomba:roomba_rssi" [profile="timestamp-update"] }

/* Downstairs Braava Jet M6 Commands */
String mopster_roomba_command "Mopster" <roomba> (roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_command" }
/* Settings */
/* Mop Feedback */
String mopster_roomba_softwareVer   "Software Version [%s]" <text> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_softwareVer" }
Number mopster_roomba_batPct  "Battery [%d%%]" <battery> (mopster_roomba_items, Battery)  { channel="mqtt:topic:downstairs_mop:roomba_batPct" }
String mopster_roomba_lastcommand   "Last Command [%s]" <roomba> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_lastcommand" }
String mopster_roomba_detectedPad   "Detected Pad [%s]" <msg>    (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_detectedPad" }
Switch mopster_roomba_lid_closed    "Lid Closed [%s]"   <msg>    (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_lid_closed" }
Number mopster_roomba_padWetness_disposable "Disposable Pad Wetness [%d]" (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_padWetness_disposable" }
Number mopster_roomba_padWetness_reusable   "Reusable Pad Wetness [%d]"   (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_padWetness_reusable" }
Switch mopster_roomba_bin_present   "Tank Present [%s]" <cistern> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_bin_present" }
Number mopster_roomba_tankLvl "Tank Level [%d%%]"       <cistern> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_tankLvl" }
/* Mission values */
String mopster_roomba_mission   "Mission [%s]" <msg> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_mission" }
Number mopster_roomba_nMssn     "Cleaning Mission Number [%d]" <number> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_nMssn" }
String mopster_roomba_phase     "Phase [%s]" <msg> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_phase" }
String mopster_roomba_initiator   "Initiator [%s]" <msg> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_initiator" }
Switch mopster_roomba_error  "Error [%d]" <roombaerror> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_error" }
String mopster_roomba_errortext   "Error Message [%s]" <msg> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_errortext" }
Number mopster_roomba_mssnM  "Cleaning Elapsed Time [%d m]" <clock> (mopster_roomba_items)  { channel="mqtt:topic:downstairs_mop:roomba_mssnM" }
Number mopster_roomba_sqft  "Square Ft Cleaned [%d]" <groundfloor> (mopster_roomba_items)  { channel="mqtt:topic:downstairs_mop:roomba_sqft" }
Number mopster_roomba_expireM  "Mission Recharge Time [%d m]" <clock> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_expireM" }
Number mopster_roomba_rechrgM  "Remaining Time To Recharge [%d m]" <clock> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_rechrgM" }
String mopster_roomba_status     "Status [%s]" <msg> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_status" }
Number mopster_roomba_percent_complete     "Mission % Completed [%d%%]" <humidity> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_percent_complete" }
DateTime mopster_roomba_lastmissioncompleted  "Last Mission Completed [%1$ta %1$tR]" <calendar>
/* Schedule */
String mopster_roomba_cycle    "Day of Week [%s]" <calendar> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_cycle" }
String mopster_roomba_cleanSchedule_h    "Hour of Day [%s]" <clock> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_cleanSchedule_h" }
String mopster_roomba_cleanSchedule_m    "Minute of Hour [%s]" <clock> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_cleanSchedule_m" }
String mopster_roomba_cleanSchedule2     "Schedule [%s]" <clock> (mopster_roomba_items) { channel="mqtt:topic:mopster_roomba:roomba_cleanSchedule2" }
String mopster_roomba_cleanSchedule  "Schedule [%s]" <calendar> (mopster_roomba_items)
/* General */
Switch mopster_roomba_control  "Mop ON/OFF [%s]" <switch> (mopster_roomba_items)
Number mopster_roomba_theta  "Theta [%d]" <angle> (mopster_roomba_items)  { channel="mqtt:topic:downstairs_mop:roomba_theta" }
Number mopster_roomba_x  "X [%d]" <map> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_x" }
Number mopster_roomba_y  "Y [%d]" <map> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_y" }
Number mopster_roomba_rssi  "RSSI [%d]" <network> (mopster_roomba_items) { channel="mqtt:topic:downstairs_mop:roomba_rssi" }
DateTime mopster_roomba_lastheardfrom  "Last Update [%1$ta %1$tR]" <clock> { channel="mqtt:topic:downstairs_mop:roomba_rssi" [profile="timestamp-update"] }
```
### Sitemap
```
Group item=roomba_items {
    Group item=downstairs_roomba_items label="Downstairs Roomba" {
        Switch item=downstairs_roomba_command mappings=[start="Start",stop="Stop",pause="Pause",dock="Dock",resume="Resume",train="Train", reset="Reset"]
        Group item=downstairs_roomba_items label="Map" icon="map" {
            Frame label="Map" {
                Webview icon="map" url="http://your_OH_ip:port/static/roomba/Downstairsroomba_map.html" height=21 label="Map"
            }
        }
        Group item=downstairs_roomba_items label="Settings" icon="select"{
            Text item=downstairs_roomba_cleanSchedule
            Switch item=downstairs_roomba_edgeClean
            Switch item=downstairs_roomba_carpetBoost
            Switch item=downstairs_roomba_vacHigh visibility=[downstairs_roomba_carpetBoost==OFF]
            Switch item=downstairs_roomba_noAutoPasses
            Switch item=downstairs_roomba_twoPass visibility=[downstairs_roomba_noAutoPasses==OFF]
            Switch item=downstairs_roomba_binPause
        }
        Frame item=downstairs_roomba_lastcommand label="Status [%s]" {
            Text item=downstairs_roomba_softwareVer
            Text item=downstairs_roomba_batPct
            Text item=downstairs_roomba_phase
            Text item=downstairs_roomba_lastcommand
            Switch item=downstairs_roomba_full mappings=[ON="FULL", OFF="Not Full"]
            Switch item=downstairs_roomba_bin_present mappings=[OFF="Removed", ON="Installed"]
            Text item=downstairs_roomba_rssi
            Text item=downstairs_roomba_lastheardfrom
        }
        Frame item=downstairs_roomba_status label="Mission [%s]" {
            Text item=downstairs_roomba_status
            Text item=downstairs_roomba_rechrgM visibility=[downstairs_roomba_status=="Recharging"]
            Text item=downstairs_roomba_mission
            Text item=downstairs_roomba_percent_complete
            Switch item=downstairs_roomba_error mappings=[ON="ERROR!", OFF="Normal"]
            Text item=downstairs_roomba_errortext
            Text item=downstairs_roomba_mssnM
            Text item=downstairs_roomba_sqft
            Text item=downstairs_roomba_nMssn
            Text item=downstairs_roomba_lastmissioncompleted
            Text item=downstairs_roomba_initiator
        }
        Frame label="Location" {
            Text item=downstairs_roomba_theta
            Text item=downstairs_roomba_x
            Text item=downstairs_roomba_y
        }
    }
    Group item=mopster_roomba_items label="Downstairs Mop" {
        Switch item=mopster_roomba_command mappings=[start="Start",stop="Stop",pause="Pause",dock="Dock",resume="Resume",train="Train"]
        Group item=mopster_roomba_items label="Map" icon="map" {
            Frame label="Map" {
                Webview icon="map" url="http://your_OH_ip:port/static/roomba/Mopsterroomba_map.html" height=21 label="Map"
            }
        }
        Group item=mopster_roomba_items label="Settings" icon="select"{
            Text item=mopster_roomba_cleanSchedule
        }
        Frame item=mopster_roomba_lastcommand label="Status [%s]" {
            Text item=mopster_roomba_softwareVer
            Text item=mopster_roomba_batPct
            Text item=mopster_roomba_phase
            Text item=mopster_roomba_lastcommand
            Switch item=mopster_roomba_lid_closed  mappings=[OFF="Open", ON="Closed"]
            Switch item=mopster_roomba_bin_present mappings=[OFF="Removed", ON="Installed"]
            Text item=mopster_roomba_tankLvl
            Text item=mopster_roomba_detectedPad
            Text item=mopster_roomba_padWetness_disposable
            Text item=mopster_roomba_padWetness_reusable
            Text item=mopster_roomba_rssi
            Text item=mopster_roomba_lastheardfrom
        }
        Frame item=mopster_roomba_status label="Mission [%s]" {
            Text item=mopster_roomba_status
            Text item=mopster_roomba_rechrgM visibility=[mopster_roomba_status=="Recharging"]
            Text item=mopster_roomba_mission
            Text item=mopster_roomba_percent_complete
            Switch item=mopster_roomba_error mappings=[ON="ERROR!", OFF="Normal"]
            Text item=mopster_roomba_errortext
            Text item=mopster_roomba_mssnM
            Text item=mopster_roomba_sqft
            Text item=mopster_roomba_nMssn
            Text item=mopster_roomba_lastmissioncompleted
            Text item=mopster_roomba_initiator
        }
        Frame label="Location" {
            Text item=mopster_roomba_theta
            Text item=mopster_roomba_x
            Text item=mopster_roomba_y
        }
    }
    Group item=upstairs_roomba_items label="Upstairs Roomba" {
        Switch item=upstairs_roomba_command mappings=[start="Start",stop="Stop",pause="Pause",dock="Dock",resume="Resume"]
        Group item=upstairs_roomba_items label="Map" icon="map" {
            Frame label="Map" {
                Webview icon="map" url="http://your_OH_ip:port/static/roomba/Upstairsroomba_map.html" height=21 label="Map"
            }
        }
        Group item=upstairs_roomba_items label="Settings" icon="select"{
            Text item=upstairs_roomba_cleanSchedule
            Switch item=upstairs_roomba_edgeClean
            Switch item=upstairs_roomba_carpetBoost
            Switch item=upstairs_roomba_vacHigh visibility=[upstairs_roomba_carpetBoost==OFF]
            Switch item=upstairs_roomba_noAutoPasses
            Switch item=upstairs_roomba_twoPass visibility=[upstairs_roomba_noAutoPasses==OFF]
            Switch item=upstairs_roomba_binPause
        }
        Frame item=upstairs_roomba_lastcommand label="Status [%s]" {
            Text item=upstairs_roomba_softwareVer
            Text item=upstairs_roomba_batPct
            Text item=upstairs_roomba_phase
            Text item=upstairs_roomba_lastcommand
            Switch item=upstairs_roomba_full mappings=[ON="FULL", OFF="Not Full"]
            Switch item=upstairs_roomba_bin_present mappings=[OFF="Removed", ON="Installed"]
            Text item=upstairs_roomba_rssi
            Text item=upstairs_roomba_lastheardfrom
        }
        Frame item=upstairs_roomba_status label="Mission [%s]" {
            Text item=upstairs_roomba_status
            Text item=upstairs_roomba_rechrgM visibility=[upstairs_roomba_status=="Recharging"]
            Text item=upstairs_roomba_mission
            Text item=upstairs_roomba_percent_complete
            Switch item=upstairs_roomba_error mappings=[ON="ERROR!", OFF="Normal"]
            Text item=upstairs_roomba_errortext
            Text item=upstairs_roomba_mssnM
            Text item=upstairs_roomba_sqft
            Text item=upstairs_roomba_nMssn
            Text item=upstairs_roomba_lastmissioncompleted
            Text item=upstairs_roomba_initiator
        }
        Frame label="Location" {
            Text item=upstairs_roomba_theta
            Text item=upstairs_roomba_x
            Text item=upstairs_roomba_y
        }
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
```
### Rules
**NOTE:** I do not use these rules anymore, as I have moved over to the HabApp rules engine (see https://github.com/spacemanspiff2007/HABApp), so they probably won't work properly anymore  
**NOTE:** You will have to change the roomba item names to match your roomba item names eg `upstairs_roomba_command` etc.  

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
Items and transforms are there also.

### Mapping
See `roomba_map.html` - for openhab2 copy this to /etc/openhab2/html (same location as map.png will go in), now you can see the live maps via `http://your_OH_ip:port/static/roomba_map.html` in your browser. I use a subdirectory to avoid cluttering the root html directory, just be consistent in the pathnames, and make sure the directory exists (with write permission) before running roomba.py!  
If you specify a map location when starting `roomba.py` the file will be generated automatically.

### General
start_openhab_roomba is a bash script that starts roomba with the maps in the right location (on Ubuntu) for openhab2, you may have to change this location for other systems (windows, RPi, etc), depending on how you installed Openhab2. You need the mqtt binding installed as well.  
In the above rules/sitemap replace `your_OH_ip:port` with your own Openhab2 ip and port - to use this from anywhere, these should be externally available (from outside your own network) addresses, otherwise you can only access then from within your own network (e-mail attachments should work though).

### Debugging
You can start `roomba.py` in debugging mode using `-D` switch, this produces a lot more information in the logs, and saves more files. It also uses more CPU cycles.

There is a utility included `replay_log.py`, this takes the log output, and replays it throught the server, so you can simulate Rooba runs, without actually having to run the Roomba.  
This is the help output:
```bash
usage: replay_log.py [-h] [-n ROOMBANAME] [-pn PUBROOMBANAME]
                     [-m MISSIONSTART] [-s] [-C BROKERCOMMAND] [-b BROKER]
                     [-p PORT] [-U USER] [-P PASSWORD]
                     log

Replay Roomba log to test mapping

positional arguments:
  log                   path/name of log file (default: None)

optional arguments:
  -h, --help            show this help message and exit
  -n ROOMBANAME, --roombaName ROOMBANAME
                        optional Roomba name (default: "")
  -pn PUBROOMBANAME, --pubroombaName PUBROOMBANAME
                        optional Roomba name to publish to (default: "")
  -m MISSIONSTART, --missionStart MISSIONSTART
                        optional date/time to start parsing from, format is
                        "2021-01-13 14:57:06" (default: None)
  -s, --start_mission   Start Mission immediately (default: False)
  -C BROKERCOMMAND, --brokerCommand BROKERCOMMAND
                        Topic on broker to publish commands to (default:
                        /roomba/simulate</name>)
  -b BROKER, --broker BROKER
                        ipaddress of MQTT broker (default: None)
  -p PORT, --port PORT  MQTT broker port number (default: 1883)
  -U USER, --user USER  MQTT broker user name (default: None)
  -P PASSWORD, --password PASSWORD
                        MQTT broker password (default: None)
```
To use this, enter the same broker information as used to start `roomba.py`, enter the path to a log file, with a Roomba mission captured in it, and use -n to enter the name of the Roomba you want to replay the run for. The mission start will be found automatically, or you can specify `-s` to start immediately. You can also optionally use `-m` ro set a start date/time - just use `"` around the date/time string.

For example:
```bash
./replay_log.py ./roomba.log -b my_MQTT_broker_IP -m "2021-02-10 09:25:43" -n Upstairs
```
Would start searching `roomba.log` for a "New Mission" for roomba called "Upstairs" after 2021-02-10 09:25:43, and then start publishing the Roomba data in the log to the MQTT simulation topic for that roomba.  
If you used the `-s` switch, publishing would start immediately, without looking for the "new Mission" event. If you leave the date/time out, publishing starts with the first event in the log.

## ToDo's
I'm just using some roomba icons I found on the web, if you have better roomba icons, please let me know.  
Update the example map shown here, it's an older version, the new ones are a little nicer. 
