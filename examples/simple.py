from __future__ import print_function
from roomba import Roomba

#uncomment the option you want to run, and replace address, blid and roombaPassword with your own values

address = "192.168.100.181"
blid = "3115850251687850"
roombaPassword = ":1:1493319243:gOiaXpQ4lbSoD1xJ"

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
    print(json.dumps(myroomba.master_state, indent=2))
    time.sleep(1)
myroomba.disconnect()
