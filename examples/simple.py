#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
import logging
from roomba import Roomba

#Uncomment the following two lines to see logging output
logging.basicConfig(level=logging.INFO, 
      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

#uncomment the option you want to run, and replace address, blid and roombaPassword with your own values

address = "192.168.1.181"
blid = "3835850251647850"
roombaPassword = ":1:1493319243:gOizXpQ4lcdSoD1xJ"

#myroomba = Roomba(address, blid, roombaPassword)
#or myroomba = Roomba(address) #if you have a config file - will attempt discovery if you don't
myroomba = Roomba()
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