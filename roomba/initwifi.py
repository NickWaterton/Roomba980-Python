#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import binascii
import json
import logging
import time

from roomba import Password, Roomba


class InitWifi(object):
    def __init__(self,
                 address='192.168.10.1',
                 wifi_ssid=None,
                 wifi_password=None,
                 country=None,
                 timezone=None,
                 robot_name=None,
                 sdisc_url=None,
                 ntphosts=None,
                 cloud_env=None):
        self.address = address
        self.wifi_ssid = wifi_ssid
        self.wifi_password = wifi_password
        self.country = country
        self.timezone = timezone
        self.robot_name = robot_name
        self.sdisc_url = sdisc_url
        self.ntphosts = ntphosts
        self.cloud_env = cloud_env

        self.log = logging.getLogger('Roomba.{}'.format(__class__.__name__))

        if self.timezone is None:
            try:
                import tzlocal
                self.timezone = str(tzlocal.get_localzone())
            except ImportError:
                self.log.warning('tzlocal module not present, cannot determine system timezone')
                pass

        if self.country is None:
            try:
                import pytz
                for country_code in pytz.country_names:
                    try:
                        if self.timezone in pytz.country_timezones(country_code):
                            self.country = country_code
                            break
                    except KeyError:
                        continue
            except ImportError:
                self.log.warning('pytz module not present, cannot determine country code')
                pass

    def init_wifi(self):
        get_passwd = Password(self.address, file=None)

        self.log.info("Trying to discover robot at address {}".format(self.address))
        roombas = get_passwd.receive_udp()
        if len(roombas) == 0:
            self.log.warning("No Roombas found on network, try again...")
            return False

        if len(roombas) > 1:
            self.log.warning("More than one Roomba found. Please provide a specific IP address")
            return False

        addr, parsedMsg = next(iter(roombas.items()))
        blid = parsedMsg.get('robotid', parsedMsg.get("hostname", "").split('-')[1])
        fw_ver = int(parsedMsg.get("ver", "3"))
        if fw_ver < 2:
            self.log.info(
                "Roombas at address: {} does not have the correct firmware version. Your version info is: {}".format(
                    addr, json.dumps(parsedMsg, indent=2)))
            return False

        if self.wifi_ssid is None:
            self.log.info("WiFi SSID not specified")
            self.wifi_ssid = input("Type the SSID that the robot shall use: ")
            if not self.wifi_ssid:
                self.log.error("WiFi SSID not provided, aborting")
                return False

        if self.wifi_password is None:
            self.log.info("WiFi password not specified")
            self.wifi_password = input("Type the password that the robot shall use: ")
            if self.wifi_password is None:
                self.log.error("WiFi password not provided, aborting")
                return False

        if self.wifi_ssid is None or self.wifi_password is None:
            self.log.critical("Invalid wifi_ssid or wifi_password! All these must be specified!")
            return False

        password = parsedMsg.get('password')
        if password is None:
            password = get_passwd.get_password_from_roomba(addr)
        if not password:
            self.log.info("No password set, attempting to generate and set a new one...")
            time.sleep(1)
            password = get_passwd.set_new_password_on_roomba(addr)
            time.sleep(1)

            if password is None or get_passwd.get_password_from_roomba(addr) != password:
                self.log.error("Setting MQTT password failed")
                return False

        self.log.info("blid is: {}".format(blid))
        self.log.info('Password=> {} <= Yes, all this string.'.format(password))
        self.log.info('Use these credentials in roomba.py')

        result = self.provision_wifi_config(addr, blid, password, fw_ver)
        if result:
            self.log.info(
                'Provisioning information sent. Your robot should connect the desired network in a minute.')
        else:
            self.log.error('Provisioning failed.')
        return result

    def provision_wifi_config(self, addr, blid, password, fw_ver):
        async def async_provision(myroomba: Roomba):
            connected = await myroomba.async_connect()
            if not connected:
                return False

            try:
                messages = []
                messages.append(("wifictl", {"wactivate": False}))
                messages.append(("wifictl", {"utctime": int(time.time())}))
                messages.append(("wifictl", {"localtimeoffset": -time.timezone // 60}))
                if self.timezone is not None:
                    self.log.info("Using timezone: " + self.timezone)
                    messages.append(("delta", {"timezone": self.timezone}))
                if self.sdisc_url is not None:
                    self.log.info("Using sdiscUrl: " + self.sdisc_url)
                    messages.append(("wifictl", {"sdiscUrl": self.sdisc_url}))
                if self.ntphosts is not None:
                    self.log.info("Using ntphosts: " + self.ntphosts)
                    messages.append(("wifictl", {"ntphosts": self.ntphosts}))
                if self.country is not None:
                    self.log.info("Using country: " + self.country)
                    messages.append(("delta", {"country": self.country}))
                if self.cloud_env is not None:
                    self.log.info("Using cloudEnv: " + self.cloud_env)
                    messages.append(("delta", {"cloudEnv": self.cloud_env}))
                if self.robot_name is not None:
                    self.log.info("Using robot name: " + self.robot_name)
                    messages.append(("delta", {"name": self.robot_name}))

                wlcfg = {"sec": 7,
                         "ssid": binascii.hexlify(self.wifi_ssid.encode("UTF-8")).decode()}
                if fw_ver == 2:
                    wlcfg["pass"] = self.wifi_password
                else:
                    wlcfg["pass"] = binascii.hexlify(self.wifi_password.encode("UTF-8")).decode()
                messages.append(("wifictl", {"wlcfg": wlcfg}))
                messages.append(("wifictl", {"chkssid": True}))
                messages.append(("wifictl", {"wactivate": True}))
                messages.append(("wifictl", {"get": "netinfo"}))
                messages.append(("wifictl", {"uap": False}))

                for topic, state in messages:
                    myroomba.client.publish(topic, json.dumps({"state": state}))
                    await asyncio.sleep(1)

                return True
            finally:
                await myroomba._disconnect()

        myroomba = Roomba(addr, blid=blid, password=password, file=None)
        return myroomba.loop.run_until_complete(async_provision(myroomba))


def main():
    import argparse
    loglevel = logging.DEBUG
    LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT, level=loglevel)

    # -------- Command Line -----------------
    parser = argparse.ArgumentParser(
        description='Provision WiFi connection to a robot while connected to its SoftAP network')
    parser.add_argument(
        '-R', '--roomba_ip',
        action='store',
        type=str,
        default='192.168.10.1',
        help='ipaddress of Roomba (default: %(default)s)')
    parser.add_argument(
        '-n', '--roomba_name',
        action='store',
        type=str,
        default="", help='Name that the robot shall assume')
    parser.add_argument(
        '-s', '--wifi_ssid',
        action='store',
        type=str,
        help='SSID of the WiFi network the robot should connect to')
    parser.add_argument(
        '-p', '--wifi_password',
        action='store',
        type=str,
        help='Password of the WiFi network the robot should connect to')
    parser.add_argument(
        '-T', '--timezone',
        action='store',
        type=str,
        help='IANA name of the timezone that should be configured on the robot '
             '(default: read from the host system if possible)')
    parser.add_argument(
        '-c', '--country',
        action='store',
        type=str,
        help='Two-letter code of the country the robot is located in '
             '(for radio regulatory purposed; default: inferred from timezone if possible)')
    parser.add_argument(
        '-S', '--sdisc_url',
        type=str,
        help='MQTT service discovery URL that the robot shall use after provisioning')
    parser.add_argument(
        '-N', '--ntphosts',
        type=str,
        help='Space-separated list of NTP servers that the robot shall use')
    parser.add_argument(
        '-C', '--cloud_env',
        type=str,
        help='Name of the cloud environment that the robot shall use (e.g. "prod")')

    arg = parser.parse_args()

    init_wifi = InitWifi(address=arg.roomba_ip,
                         wifi_ssid=arg.wifi_ssid,
                         wifi_password=arg.wifi_password,
                         country=arg.country,
                         timezone=arg.timezone,
                         robot_name=arg.roomba_name,
                         sdisc_url=arg.sdisc_url,
                         ntphosts=arg.ntphosts,
                         cloud_env=arg.cloud_env)
    init_wifi.init_wifi()


if __name__ == '__main__':
    main()
