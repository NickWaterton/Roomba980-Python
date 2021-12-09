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

import sys, os, base64, datetime, hashlib, hmac
import random
import requests
import time
import urllib.parse

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

        self.data = response

        self.amz = awsRequest(region, access_key, secret_key, session_token, "execute-api")

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

def main():
    import argparse, logging, json
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

    arg = parser.parse_args()

    if len(arg.login) >= 2:
        irobot = irobotAuth(arg.login[0], arg.login[1])
        irobot.login()
        robots = irobot.get_robots()
        logging.info("Robot ID and data: {}".format(json.dumps(robots, indent=2)))
        if arg.maps:
            for robot in robots.keys():
                logging.info("Robot ID {}, MAPS: {}".format(robot, json.dumps(irobot.get_maps(robot), indent=2)))
    else:
        logging.error("Please enter iRobot account login and password")

if __name__ == '__main__':
    main()