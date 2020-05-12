import logging
import ssl
import paho.mqtt.client as mqtt
from roomba.const import MQTT_ERROR_MESSAGES


class RoombaMQTTClient:
    address = None
    port = None
    blid = None
    password = None
    log = None
    was_connected = False
    on_connect = None
    on_disconnect = None

    def __init__(self, address, blid, password, port=8883):
        self.address = address
        self.blid = blid
        self.password = password
        self.port = port
        self.log = logging.getLogger(__name__)
        self.mqtt_client = self._get_mqtt_client()

    def set_on_message(self, on_message):
        self.mqtt_client.on_message = on_message

    def set_on_connect(self, on_connect):
        self.on_connect = on_connect

    def set_on_publish(self, on_publish):
        self.mqtt_client.on_publish = on_publish

    def set_on_subscribe(self, on_subscribe):
        self.mqtt_client.on_subscribe = on_subscribe

    def set_on_disconnect(self, on_disconnect):
        self.on_disconnect = on_disconnect

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

    def subscribe(self, topic):
        self.mqtt_client.subscribe(topic)

    def publish(self, topic, payload):
        self.mqtt_client.publish(topic, payload)

    def _get_mqtt_client(self):
        mqtt_client = mqtt.Client(client_id=self.blid)
        mqtt_client.username_pw_set(username=self.blid, password=self.password)
        mqtt_client.on_connect = self._internal_on_connect
        mqtt_client.on_disconnect = self._internal_on_disconnect

        self.log.debug("Setting TLS certificate")
        try:
            mqtt_client.tls_set(
                cert_reqs=ssl.CERT_NONE,
                tls_version=ssl.PROTOCOL_TLS,
                ciphers='DEFAULT:!DH')
        except ValueError:  # try V1.3 version
            self.log.warning("TLS Setting failed - trying 1.3 version")
            mqtt_client._ssl_context = None
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            ssl_context.verify_mode = ssl.CERT_NONE
            ssl_context.set_ciphers('DEFAULT:!DH')
            ssl_context.load_default_certs()
            mqtt_client.tls_set_context(ssl_context)
        mqtt_client.tls_insecure_set(True)

        return mqtt_client

    def _internal_on_connect(self, client, userdata, flags, rc):
        self.log.debug("Connected to Roomba %s, response code = %s", self.address, rc)
        connection_error = MQTT_ERROR_MESSAGES[rc]
        if self.on_connect is not None:
            self.on_connect(connection_error)

    def _internal_on_disconnect(self, client, userdata, flags, rc):
        self.log.debug("Disconnected from Roomba %s, response code = %s", self.address, rc)
        connection_error = MQTT_ERROR_MESSAGES[rc]
        if self.on_disconnect is not None:
            self.on_disconnect(connection_error)
