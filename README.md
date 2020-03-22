roombapy
================

Unofficial iRobot Roomba python library (SDK).

Fork of [NickWaterton/Roomba980-Python](https://github.com/NickWaterton/Roomba980-Python)

This library designed to work as [integration](https://www.home-assistant.io/integrations/roomba/) with Home-Assistant.

## Firmware 2.x.x notes
This library is only for firmware 2.x.x [Check your robot version!](http://homesupport.irobot.com/app/answers/detail/a_id/529) 

Supports Python 3.6, 3.7 (thanks to pschmitt for adding Python 3 compatibility). Only local connections are supported.

## How to get your username/blid and password

Please refer to [here](https://github.com/NickWaterton/Roomba980-Python#how-to-get-your-usernameblid-and-password) or 
[here](https://github.com/koalazak/dorita980#how-to-get-your-usernameblid-and-password) to retrieve both the BLID (username) and the password.

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
