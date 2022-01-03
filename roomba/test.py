#!/usr/bin/env python3

# Copyright 2021 Matthew Garrett <mjg59@srcf.ucam.org>
#
# Portions Copyright 2010-2019 Amazon.com, Inc. or its affiliates. All
# Rights Reserved.
#
# This file is licensed under the Apache License, Version 2.0 (the
# "License").  You may not use this file except in compliance with the
# License. A copy of the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

import sys, os, base64, datetime, hashlib, hmac, logging, json
import random
import requests
import time
import urllib.parse
#import paho.mqtt.client as mqtt
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
import ssl
cert_reqs = ssl.CERT_REQUIRED
tls_version = ssl.PROTOCOL_TLS

class awsRequest:
    def __init__(self, region, access_key, secret_key, session_token, service):
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        self.session_token = session_token
        self.service = service
            
    def sign(self, key, msg):
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

    def getSignatureKey(self, key, dateStamp, regionName, serviceName):
        kDate = self.sign(('AWS4' + key).encode('utf-8'), dateStamp)
        kRegion = self.sign(kDate, regionName)
        kService = self.sign(kRegion, serviceName)
        kSigning = self.sign(kService, 'aws4_request')
        return kSigning

    def get(self, host, uri, query=""):
        method = "GET"

        # Create a date for headers and the credential string
        t = datetime.datetime.utcnow()
        amzdate = t.strftime('%Y%m%dT%H%M%SZ')
        datestamp = t.strftime('%Y%m%d') # Date w/o time, used in credential scope

        canonical_uri = uri
        canonical_querystring = query
        canonical_headers = 'host:' + host + '\n' + 'x-amz-date:' + amzdate + '\n' + 'x-amz-security-token:' + self.session_token + '\n'
        signed_headers = 'host;x-amz-date;x-amz-security-token'
        payload_hash = hashlib.sha256(('').encode('utf-8')).hexdigest()
        canonical_request = method + '\n' + canonical_uri + '\n' + canonical_querystring + '\n' + canonical_headers + '\n' + signed_headers + '\n' + payload_hash

        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = datestamp + '/' + self.region + '/' + self.service + '/' + 'aws4_request'
        string_to_sign = algorithm + '\n' +  amzdate + '\n' +  credential_scope + '\n' +  hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()

        signing_key = self.getSignatureKey(self.secret_key, datestamp, self.region, self.service)
        signature = hmac.new(signing_key, (string_to_sign).encode('utf-8'), hashlib.sha256).hexdigest()

        authorization_header = algorithm + ' ' + 'Credential=' + self.access_key + '/' + credential_scope + ', ' +  'SignedHeaders=' + signed_headers + ', ' + 'Signature=' + signature
        headers = {'x-amz-security-token': self.session_token, 'x-amz-date':amzdate, 'Authorization':authorization_header}

        req = "https://%s%s" % (host, uri)
        if query != "":
            req += "?%s" % query
        return requests.get(req, headers=headers)

class irobotAuth:
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def login(self):
        r = requests.get("https://disc-prod.iot.irobotapi.com/v1/discover/endpoints?country_code=US")
        response = r.json()
        deployment = response['deployments'][next(iter(response['deployments']))]
        self.httpBase = deployment['httpBase']
        iotBase = deployment['httpBaseAuth']
        iotUrl = urllib.parse.urlparse(iotBase)
        mqtt_host = deployment['mqtt']
        iotTopics = deployment["iotTopics"]
        self.iotHost = iotUrl.netloc
        region = deployment['awsRegion']

        self.apikey = response['gigya']['api_key']
        self.gigyaBase = response['gigya']['datacenter_domain']

        data = {"apiKey": self.apikey,
                "targetenv": "mobile",
                "loginID": self.username,
                "password": self.password,
                "format": "json",
                "targetEnv": "mobile",
        }

        r = requests.post("https://accounts.%s/accounts.login" % self.gigyaBase, data=data)

        response = r.json()

        data = {"timestamp": int(time.time()),
                "nonce": "%d_%d" % (int(time.time()), random.randint(0, 2147483647)),
                "oauth_token": response['sessionInfo']['sessionToken'],
                "targetEnv": "mobile"}

        uid = response['UID']
        uidSig = response['UIDSignature']
        sigTime = response['signatureTimestamp']

        data = {
            "app_id": "ANDROID-C7FB240E-DF34-42D7-AE4E-A8C17079A294",
            "assume_robot_ownership": "0",
            "gigya": {
                "signature": uidSig,
                "timestamp": sigTime,
                "uid": uid,
            }
        }

        r = requests.post("%s/v2/login" % self.httpBase, json=data)

        response = r.json()
        access_key = response['credentials']['AccessKeyId']
        secret_key = response['credentials']['SecretKey']
        session_token = response['credentials']['SessionToken']
        
        Expiration = response['credentials']['Expiration']
        CognitoId = response['credentials']['CognitoId']
        iot_token = response["iot_token"]

        self.data = response

        self.amz = awsRequest(region, access_key, secret_key, session_token, "execute-api")
        self.mqtt = awsMQTT(mqtt_host, region, access_key, secret_key, session_token, Expiration, iotTopics)

    def get_robots(self):
        return self.data['robots']

    def get_maps(self, robot):
        return self.amz.get(self.iotHost, '/dev/v1/%s/pmaps' % robot, query="activeDetails=2").json()

    def get_newest_map(self, robot):
        maps = self.get_maps(robot)
        latest = ""
        latest_time = 0
        for map in maps:
            if map['create_time'] > latest_time:
                latest_time = map['create_time']
                latest = map
        return latest

class awsMQTT:  
    def __init__(self, awsmqtthost, region, AWSAccessKeyID, AWSSecretAccessKey, AWSSessionToken, Expiration, iotTopics):
        #self.log = logging.getLogger("root")
        self.log = logging.getLogger("AWSIoTPythonSDK.core")
        self.log.setLevel(logging.DEBUG)
        streamHandler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        streamHandler.setFormatter(formatter)
        self.log.addHandler(streamHandler)
        self.log.info("MQTT set up")
        self.host = awsmqtthost
        self.region = region
        self.AWSAccessKeyID = AWSAccessKeyID
        self.AWSSecretAccessKey = AWSSecretAccessKey
        self.AWSSessionToken = AWSSessionToken
        self.Expiration = Expiration
        self.topic = iotTopics + "/things/E72D1E0D914E429CAB7527B43B758297/shadow/update"
        self.topic = iotTopics + "/#"
        self.thingName = "E72D1E0D914E429CAB7527B43B758297"
        # $aws/things/E72D1E0D914E429CAB7527B43B758297/shadow/update
        # mopster 4F28D7B9E0C94446B61D39518964563E
        self.rootCAPath = "/etc/ssl/certs/Amazon_Root_CA_1.pem"
        #self.setup_aws_mqtt()
        self.setup_mqtt_client2()
        
    def setup_mqtt_client2(self):
        from uuid import uuid4
        import threading
        from datetime import datetime, timedelta
        io.init_logging(getattr(io.LogLevel, 'Debug'), 'stderr')
        event_loop_group = io.EventLoopGroup(1)
        host_resolver = io.DefaultHostResolver(event_loop_group)
        client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
        #credentials_provider = auth.AwsCredentialsProvider.new_default_chain(client_bootstrap)
        credentials_provider = auth.AwsCredentials(self.AWSAccessKeyID, self.AWSSecretAccessKey, self.AWSSessionToken)
        clientId = "paho/" + "".join(random.choice("0123456789ADCDEF") for x in range(23-5))
        clientId = "app-ANDROID-C7FB240E-DF34-42D7-AE4E-A8C17079A294-M4MDAKLH"
        self.mqtt_connection = mqtt_connection_builder.websockets_with_default_aws_signing(
            endpoint=self.host,
            client_bootstrap=client_bootstrap,
            region=self.region,
            username = credentials_provider,
            credentials_provider=credentials_provider,
            cert_filepath = "",
            pri_key_filepath = "",
            http_proxy_options = None,
            ca_filepath=self.rootCAPath,
            on_connection_interrupted=self.on_connection_interrupted,
            on_connection_resumed=self.on_connection_resumed,
            client_id=clientId,
            clean_session=True,
            keep_alive_secs=30)
            
        print("Connecting to {} with client ID '{}'...".format(
        self.host, clientId))

        connect_future = self.mqtt_connection.connect()

        # Future.result() waits until a result is available
        connect_future.result()
        print("Connected!")

        # Subscribe
        print("Subscribing to topic '{}'...".format(self.topic))
        subscribe_future, packet_id = self.mqtt_connection.subscribe(
            topic=self.topic,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self.on_message_received)

        subscribe_result = subscribe_future.result()
        print("Subscribed with {}".format(str(subscribe_result['qos'])))
        
        while True:
            time.sleep(1)
        
    # Callback when connection is accidentally lost.
    def on_connection_interrupted(self, connection, error, **kwargs):
        print("Connection interrupted. error: {}".format(error))


    # Callback when an interrupted connection is re-established.
    def on_connection_resumed(self, connection, return_code, session_present, **kwargs):
        print("Connection resumed. return_code: {} session_present: {}".format(return_code, session_present))

        if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
            print("Session did not persist. Resubscribing to existing topics...")
            resubscribe_future, _ = connection.resubscribe_existing_topics()

            # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
            # evaluate result with a callback instead.
            resubscribe_future.add_done_callback(self.on_resubscribe_complete)


    def on_resubscribe_complete(self, resubscribe_future):
            resubscribe_results = resubscribe_future.result()
            print("Resubscribe results: {}".format(resubscribe_results))

            for topic, qos in resubscribe_results['topics']:
                if qos is None:
                    sys.exit("Server rejected resubscribe to topic: {}".format(topic))


    # Callback when the subscribed topic receives a message
    def on_message_received(self, topic, payload, dup, qos, retain, **kwargs):
        print("Received message from topic '{}': {}".format(topic, payload))
        
    def setup_aws_mqtt(self):
        clientId = "paho/" + "".join(random.choice("0123456789ADCDEF") for x in range(23-5))
        # Init AWSIoTMQTTClient
        #self.myAWSIoTMQTTClient = AWSIoTMQTTClient(clientId, useWebsocket=True)
        self.myAWSIoTMQTTClient = AWSIoTMQTTShadowClient(clientId, useWebsocket=True)

        # AWSIoTMQTTClient configuration
        self.myAWSIoTMQTTClient.configureEndpoint(self.host, 443)
        self.myAWSIoTMQTTClient.configureCredentials(self.rootCAPath)
        self.myAWSIoTMQTTClient.configureIAMCredentials(self.AWSAccessKeyID, self.AWSSecretAccessKey, self.AWSSessionToken)
        self.myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
        #self.myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
        #self.myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
        self.myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
        self.myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec
        #self.myAWSIoTMQTTClient.tls_insecure_set(True)

        # Connect and subscribe to AWS IoT
        self.myAWSIoTMQTTClient.connect()
        # Create a deviceShadow with persistent subscription
        deviceShadowHandler = self.myAWSIoTMQTTClient.createShadowHandlerWithName(self.thingName, True)

        # Listen on deltas
        deviceShadowHandler.shadowRegisterDeltaCallback(self.customShadowCallback_Delta)
        #self.myAWSIoTMQTTClient.subscribe(self.topic, 1, self.customCallback)
        while True:
            time.sleep(1)
        
    def customCallback(self, client, userdata, message):
        print("Received a new message: ")
        print(message.payload)
        print("from topic: ")
        print(message.topic)
        print("--------------\n\n")
        
    def customShadowCallback_Delta(self, payload, responseStatus, token):
        # payload is a JSON string ready to be parsed using json.loads(...)
        # in both Py2.x and Py3.x
        print(responseStatus)
        payloadDict = json.loads(payload)
        print("++++++++DELTA++++++++++")
        print("property: " + str(payloadDict["state"]["property"]))
        print("version: " + str(payloadDict["version"]))
        print("+++++++++++++++++++++++\n\n")
        
    def setup_mqtt():
        client_id = "paho/" + "".join(random.choice("0123456789ADCDEF") for x in range(23-5))
        self.client = mqtt.Client(
            client_id=client_id, clean_session=True,
            protocol=mqtt.MQTTv311)
        # Assign event callbacks
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
        self.client.on_subscribe = self.on_subscribe
        self.client.on_disconnect = self.on_disconnect
        #self.client._ssl_context = None
        context = ssl.SSLContext()
        # Either of the following context settings works - choose one
        # Needed for 980 and earlier robots as their security level is 1.
        # context.set_ciphers('HIGH:!DH:!aNULL')
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        self.client.tls_set_context(context)
        self.client.tls_insecure_set(True)
        #self.client.username_pw_set(self.blid, self.password)
        self.client.connect(self.host, port=8883, keepalive=60)
        self.client.loop_start()
        
    def on_connect(self, client, userdata, flags, rc):
        self.log.info("Connected")

    def on_message(self, mosq, obj, msg):
        print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
            
    def on_publish(self, mosq, obj, mid):
        pass

    def on_subscribe(self, mosq, obj, mid, granted_qos):
        self.log.debug("Subscribed: {} {}".format(str(mid), str(granted_qos)))

    def on_disconnect(self, mosq, obj, rc):
        if rc != 0:
            self.log.warning("Unexpected Disconnect! - reconnecting")
        else:
            self.log.info("Disconnected")

    def on_log(self, mosq, obj, level, string):
        self.log.info(string)

def main():
    import argparse, json
    loglevel = logging.DEBUG
    LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT, level=loglevel)
    
    #-------- Command Line -----------------
    parser = argparse.ArgumentParser(
        description='Get password and map data from iRobot aws cloud service')
    parser.add_argument(
        'login',
        nargs='*',
        action='store',
        type=str,
        default=[],
        help='iRobot Account Login and Password (default: None)')
    parser.add_argument(
        '-m', '--maps',
        action='store_true',
        default = False,
        help='List maps (default: %(default)s)')
    parser.add_argument(
        '-a', '--all',
        action='store_true',
        default = False,
        help='List all data (default: %(default)s)')

    arg = parser.parse_args()

    if len(arg.login) >= 2:
        irobot = irobotAuth(arg.login[0], arg.login[1])
        irobot.login()
        if arg.all:
            logging.info("Robot ALL data: {}".format(json.dumps(irobot.data, indent=2)))
        else:
            robots = irobot.get_robots()
            logging.info("Robot ID and data: {}".format(json.dumps(robots, indent=2)))
        if arg.maps:
            for robot in robots.keys():
                logging.info("Robot ID {}, MAPS: {}".format(robot, json.dumps(irobot.get_maps(robot), indent=2)))
    else:
        logging.error("Please enter iRobot account login and password")

if __name__ == '__main__':
    main()