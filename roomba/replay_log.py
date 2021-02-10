#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Python 3.6 Program to test roomba mapping by replaying a log file
This is for debugging only! use at your own risk...
'''
import re
from datetime import datetime
import os
import paho.mqtt.client as mqtt
import time
import argparse
import logging as log

end_mission = '{"state":{"reported":{"cleanMissionStatus":{"cycle":"none","phase":"charge","expireM":0,"rechrgM":0,"error":0,"notReady":0,"mssnM":0,"sqft":0,"initiator":"schedule","nMssn":0}}}}'

def valid_datetime_type(arg_datetime_str):
    '''
    custom argparse type for user datetime values given from the command line
    '''
    if arg_datetime_str is None:
        return None
    try:
        return datetime.strptime(arg_datetime_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        msg = "Given Datetime ({0}) not valid! Expected format, 'YYYY-MM-DD HH:mm:ss'! (use ' around the date/time)".format(arg_datetime_str)
        raise argparse.ArgumentTypeError(msg) 

def parse_args():
    default_icon_path = os.path.join(os.path.dirname(__file__), 'res')
    #-------- Command Line -----------------
    parser = argparse.ArgumentParser(
        description='Replay Roomba log to test mapping')
    parser.add_argument(
        '-n', '--roombaName',
        action='store',
        type=str,
        default="", help='optional Roomba name (default: "")')
    parser.add_argument(
        '-pn', '--pubroombaName',
        action='store',
        type=str,
        default="", help='optional Roomba name to publish to (default: "")')
    parser.add_argument(
        '-m', '--missionStart',
        action='store',
        type=valid_datetime_type,
        default=None, help='optional date/time to start parsing from, format is "2021-01-13 14:57:06" (default: None)')
    parser.add_argument(
        '-s', '--start_mission',
        action='store_true',
        default = False,
        help='Start Mission immediately (default: %(default)s)')
    parser.add_argument(
        '-C', '--brokerCommand',
        action='store',
        type=str,
        default="/roomba/simulate",
        help='Topic on broker to publish commands to (default: '
             '/roomba/simulate</name>)')
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
        'log',
        action='store',
        type=str,
        default=None,
        help='path/name of log file (default: None)')
    return parser.parse_args()
    
def setup_client(user=None, password=None):
    client = mqtt.Client(protocol=mqtt.MQTTv311)
    # Assign event callbacks
    #client.on_message = on_message
    #client.on_connect = on_connect
    #client.on_publish = on_publish
    #client.on_subscribe = on_subscribe
    #client.on_disconnect = on_disconnect

    # Uncomment to enable debug messages
    #self.client.on_log = self.on_log
    
    if all([user, password]):
        self.client.username_pw_set(user, password)
    return client
    
def publish(mqttc, topic, msg):
    if mqttc:
        log.info('publishing: {}: {}'.format(topic, msg))
        mqttc.publish(topic, msg)
    
def lines_from_file(filename, roomba_name='', startdate=None):
    '''
    date format 2021-01-13 14:57:06
    '''
    log.info('reading file: {}'.format(filename))
    date = None
    with open(filename) as f:
        for line in f:
            if startdate:
                match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line)
                if match:
                    date = datetime.strptime(match.group(), '%Y-%m-%d %H:%M:%S')
            if startdate and date and date < startdate:
                continue
            #log.info('line: {}'.format(line))
            if roomba_name:
                if 'Roomba.{}'.format(roomba_name) in line:
                    yield line
            else:
                yield line
  
def replay_data(gen, mission=False):
    for line in gen:
        if 'New Mission' in line:
            mission = True
        if mission:
            if 'reported' in line:
                data = line.find('{')
                if data:
                    message = line[data:].replace("'","").rstrip()
                    #log.info(message)
                    yield message                    
    

def main():
    arg = parse_args()
    log.basicConfig(level=log.INFO)
    log.info("*******************")
    log.info("* Program Started *")
    log.info("*******************")
    
    if not os.path.isfile(arg.log):
        log.warning('File {} does not exist'.format(arg.log))
        return
    
    if not arg.pubroombaName:
        arg.pubroombaName = arg.roombaName
    brokerCommand = '{}{}'.format(arg.brokerCommand, '/{}'.format(arg.pubroombaName) if arg.pubroombaName else '')
    
    log.info('reading file: {}, Roomba: {}, publish to {}  Mission Date: {}'.format(arg.log, arg.roombaName, brokerCommand, arg.missionStart))
    
    file_reader = lines_from_file(arg.log, arg.roombaName, arg.missionStart)
    data_gen = replay_data(file_reader, arg.start_mission)
    
    if arg.broker:
        mqttc = setup_client(arg.user, arg.password)
        mqttc.connect(arg.broker, arg.port, 60)
        mqttc.loop_start()
    else:
        mqttc = None
        
    try:
        for data in data_gen:
            publish(mqttc, brokerCommand, data)
            time.sleep(0.5) #do not make longer than 9 seconds!, and 0.5 is as low as you can go

    except KeyboardInterrupt:
        log.info('program exit')
        publish(mqttc, brokerCommand, end_mission)
    except Exception as e:
        log.error('program error: {}'.format(e))
    finally:
        if mqttc:
            mqttc.loop_stop()

if __name__ == '__main__':
    main()