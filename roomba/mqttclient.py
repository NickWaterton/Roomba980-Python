import logging
import ssl
import os.path
import paho.mqtt.client as mqtt


class RoombaMQTTClient:
    address = None
    port = None
    blid = None
    password = None
    cert_path = None
    log = None
    was_connected = False

    def __init__(self, address, blid, password, cert_path=None, port=8883):
        self.address = address
        self.blid = blid
        self.password = password
        self.cert_path = cert_path
        self.port = port
        self.log = logging.getLogger(__name__)
        self.mqtt_client = self._get_mqtt_client()

    def set_on_message(self, on_message):
        self.mqtt_client.on_message = on_message

    def set_on_connect(self, on_connect):
        self.mqtt_client.on_connect = on_connect

    def set_on_publish(self, on_publish):
        self.mqtt_client.on_publish = on_publish

    def set_on_subscribe(self, on_subscribe):
        self.mqtt_client.on_subscribe = on_subscribe

    def set_on_disconnect(self, on_disconnect):
        self.mqtt_client.on_disconnect = on_disconnect

    def connect(self):
        if not self.was_connected:
            self.mqtt_client.connect(self.address, self.port)
            self.was_connected = True
        else:
            self.mqtt_client.loop_stop()
            self.mqtt_client.reconnect()

        self.mqtt_client.loop_start()

    def disconnect(self):
        self.mqtt_client.disconnect()

    def loop_start(self):
        self.mqtt_client.loop_start()

    def loop_stop(self):
        self.mqtt_client.loop_stop()

    def subscribe(self, topic):
        self.mqtt_client.subscribe(topic)

    def publish(self, topic, payload):
        self.mqtt_client.publish(topic, payload)

    def get_address(self):
        return self.address

    def _get_mqtt_client(self):
        mqtt_client = mqtt.Client(client_id=self.blid)
        mqtt_client.username_pw_set(username=self.blid, password=self.password)

        if not self.cert_path:
            return mqtt_client

        if not os.path.isfile(self.cert_path):
            raise Exception("can't find certificate on path = " + self.cert_path)

        self.log.debug("Setting TLS certificate")
        try:
            mqtt_client.tls_set(
                ca_certs=self.cert_path,
                cert_reqs=ssl.CERT_NONE,
                tls_version=ssl.PROTOCOL_TLS)
        except ValueError:  # try V1.3 version
            self.log.warning("TLS Setting failed - trying 1.3 version")
            mqtt_client._ssl_context = None
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            ssl_context.verify_mode = ssl.CERT_NONE
            ssl_context.load_default_certs()
            mqtt_client.tls_set_context(ssl_context)
        mqtt_client.tls_insecure_set(True)

        return mqtt_client
