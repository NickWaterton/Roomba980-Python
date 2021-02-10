#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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