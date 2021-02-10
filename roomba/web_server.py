#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Roomba api web server
'''
import asyncio
from aiohttp import web
import base64
import logging


class webserver():

    VERSION = __version__ = "2.0a"
    
    api_get =   {'time'                     : 'utctime',
                 'bbrun'                    : 'bbrun',
                 'langs'                    : 'langs',
                 'sys'                      : ['bbrstinfo',
                                               'cap',
                                               'sku',
                                               'batteryType',
                                               'soundVer',
                                               'uiSwVer',
                                               'navSwVer',
                                               'wifiSwVer',
                                               'mobilityVer',
                                               'bootloaderVer',
                                               'umiVer',
                                               'softwareVer',
                                               'audio',
                                               'bin'],
                 'lastwireless'             : ['wifistat', 'wlcfg'],
                 'week'                     : ['cleanSchedule'],
                 'preferences'              : ['cleanMissionStatus', 'cleanSchedule', 'name', 'vacHigh', 'signal'],
                 'state'                    : 'state',
                 'mission'                  : ['cleanMissionStatus', 'pose', 'bin', 'batPct'],
                 'missionbasic'             : ['cleanMissionStatus', 'bin', 'batPct'],
                 'wirelessconfig'           : ['wlcfg', 'netinfo'],
                 'wireless'                 : ['wifistat', 'netinfo'],
                 'cloud'                    : ['cloudEnv'],
                 'sku'                      : 'sku',
                 'cleanRoom'                : 'start',
                 'start'                    : 'start',
                 'clean'                    : 'clean',
                 'spot'                     : 'spot',
                 'pause'                    : 'pause',
                 'stop'                     : 'stop',
                 'resume'                   : 'resume',
                 'dock'                     : 'dock',
                 'evac'                     : 'evac',
                 'train'                    : 'train',
                 'find'                     : 'find',
                 'reset'                    : 'reset'
                }
            
    api_post =  {'week'                     : 'cleanSchedule',
                 'preferences'              : None,
                 'cleanRoom'                : 'start',
                 'carpetboost/auto'         : {'carpetBoost': True, 'vacHigh': False},
                 'carpetboost/performance'  : {'carpetBoost': False, 'vacHigh': True},
                 'carpetboost/eco'          : {'carpetBoost': False, 'vacHigh': False},
                 'edgeclean/on'             : {'openOnly': False},
                 'edgeclean/off'            : {'openOnly': True},
                 'cleaningpasses/auto'      : {'noAutoPasses': False, 'twoPass': False},
                 'cleaningpasses/one'       : {'noAutoPasses': True, 'twoPass': False},
                 'cleaningpasses/two'       : {'noAutoPasses': True, 'twoPass': True},
                 'alwaysfinish/on'          : {'binPause': False},
                 'alwaysfinish/off'         : {'binPause': True}
                }

    def __init__(self, roomba=None, webport=None, log=None):
        self.roomba = roomba if roomba else self.dummy_roomba()
        if log:
            self.log = log
        else:
            self.log = logging.getLogger("Roomba.{}.api".format(self.roomba.roombaName))
        self.loop = asyncio.get_event_loop()
        self.webport = webport
        self.app = None
        self.web_task = None
        self.start_web()
        #except aiohttp.web_runner.GracefulExit:
    
    def start_web(self):
        routes = web.RouteTableDef()
        routes.static('/map', './views')
        routes.static('/js', './views/js')
        routes.static('/css', './views/css')
        routes.static('/res', './res')
        
                    
        @routes.get('/api/local/map/{info}')
        async def map_info(request):
            item = request.match_info['info']
            value = None
            if item == 'enabled':
                value = self.roomba.drawmap
            elif item == 'mapsize':
                if self.roomba.mapSize:
                    value = {'x': self.roomba.mapSize[0],
                             'y': self.roomba.mapSize[1],
                             'off_x': self.roomba.mapSize[2],
                             'off_y': self.roomba.mapSize[3],
                             'angle': self.roomba.mapSize[4],
                             'roomba_angle': self.roomba.mapSize[5],
                             'update': 5000}
                else:
                    value = {'x': 2000,
                             'y': 2000,
                             'off_x': 0,
                             'off_y': 0,
                             'angle': 0,
                             'roomba_angle': 0,
                             'update': 5000}
            elif item == 'outline':
                img = self.roomba.img_to_png('room.png')
                if img:
                    b64img = base64.b64encode(img)
                    self.log.info('got: bytes len {}'.format(len(b64img)))
                    return web.Response(body=b64img)
            if value:
                return web.json_response(value)
            if not self.roomba.drawmap:
                raise web.HTTPBadRequest(reason='Roomba mapping not Enabled')
            raise web.HTTPBadRequest(reason='bad api call {}'.format(str(request.rel_url)))
        
        @routes.get('/api/local/info/{info}')
        async def info(request):
            item = request.match_info['info']
            items = self.get_items(item)
            value = await self.roomba.get_settings(items)
            if value:
                return web.json_response(value)
            raise web.HTTPBadRequest(reason='bad api call {}'.format(str(request.rel_url)))

        @routes.get('/api/local/action/{command}')
        async def action(request):
            command = request.match_info['command']
            command = self.get_items(command)
            value = request.query
            if command and value:
                newcommand = {'command' : command}
                newcommand.update(value)
                self.log.info('received: {}'.format(newcommand))
                self.roomba.send_region_command(newcommand)
                return web.Response(text="ok")
            await self.roomba.async_send_command(command)
            return web.Response(text="ok")
            
        @routes.get('/api/local/config/{config}')
        async def config(request):
            config = request.match_info['config']
            config = self.get_items(config)
            value = await self.loop.run_in_executor(None, self.roomba.get_property, config)
            return web.json_response(value)
            
        @routes.get('/api/local/config/{config}/{setting}')
        async def set_config(request):
            config = request.match_info['config']
            setting = request.match_info['setting']
            settings = self.post_items(config, setting)
            for k, v in settings.items():
                await self.roomba.async_set_preference(k, v)
            return web.Response(text="ok")
            
        @routes.post('/api/local/action/{command}')
        async def send_command(request):
            command = request.match_info['command']
            value = {}
            if request.can_read_body:
                value = await request.json()
                self.log.info('received: {}'.format(value))
            command = self.post_items(command)
            if command and value:
                value['command'] = command
                self.roomba.send_region_command(value)
                return web.Response(text="sent: {}".format(value))
            raise web.HTTPBadRequest(reason='bad api call {}'.format(str(request.rel_url)))
            
        @routes.post('/map/values')
        async def map_values(request):
            value = {}
            if request.can_read_body:
                value = await request.text()
                self.log.info('received: {}'.format(value))
            return web.Response(text="copy this to config.ini: {}".format(value))

        self.app = web.Application()
        self.app.add_routes(routes)
        self.log.info('starting api WEB Server V{} on port {}'.format(self.__version__, self.webport))
        self.web_task = self.loop.create_task(web._run_app(self.app, host='0.0.0.0', port=self.webport, print=None, access_log=self.log))
        
    async def cancel(self):
        '''
        shutdown web server
        '''
        if self.app:
            await self.app.shutdown()
            await self.app.cleanup()
        if self.web_task and not self.web_task.done():
            self.web_task.cancel()
        
    def get_items(self, request):
        return self.api_get.get(request, request)
        
    def post_items(self, setting, value=''):
        key = '/'.join([setting, value])
        return self.api_post.get(key, {})
        
    class dummy_roomba():
        '''
        dummy roomba class for testing
        
        '''
        def __init__(self):
            self.roombaName = 'Simulated'
            self.log = logging.getLogger("Roomba.{}.api".format(self.roombaName))
            self.log.info('Simulating Roomba')
            self.response = 'Simulated Roomba'
            self.drawmap = False
            self.room_outline = None
            self.mapSize = None
            
        def img_to_png(self, name):
            return b''
        
        async def get_settings(self, *args):
            return self.response
            
        async def async_send_command(self, *arga):
            return None
            
        def get_property(self, *atgs):
            return self.response
            
        async def async_set_preference(self, *args):
            return None
    
def main():
    logging.basicConfig(level=logging.INFO, 
                        format= '[%(asctime)s][%(levelname)5.5s](%(name)-20s) %(message)s')
    try:
        log = logging.getLogger('Roomba.{}'.format(__name__))
        loop = asyncio.get_event_loop()
        webs = webserver(webport=8200)
        loop.run_forever()
        
    except (KeyboardInterrupt, SystemExit):
        log.info("System exit Received - Exiting program")
        
    finally:
        pass
        
if __name__ == '__main__':
    main()
        