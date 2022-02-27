"""
client_subscriber.py
Sample MQTT->OSC subscriber/publisher to the role-pinging topic.
This script listens to a publicly readable MQTT* server for a message on a topic. 
On message, it publishes to OSC if valid.

please use `pip install paho-mqtt python-osc` to use this.
Note that in this script, it's expected that the server is TLS-encrypted

@author asleeponduty
"""
from re import S
import threading
import paho.mqtt.client as paho
from pythonosc import udp_client, osc_server, dispatcher
import ssl
from conf.CLIENT_SECRETS import CONFIG


# * * * * * * BEGIN * * * * * *
class SimpleMQTT2OSC(threading.Thread):

    def __init__(self,
                 config=CONFIG,
                 on_mqtt=lambda _me, msg, : print(msg.topic),
                 on_osc=lambda _me, address, _data: print(f"{address}: {_data}"),
                 debug=False):
        """
        MQTT Listener for managing incoming messages.
        Use the '.start()' member to launch this thread.

        :param config: a dictionary of address, publish_port, keepalive, input_topics, and optional username/password
        :param callback_fun: message handler function. see :func:`client_subscriber.on_message`
        :param debug: boolean. spam the console.
        """
        super().__init__()
        assert isinstance(config, dict), "Config must be a dictionary"
        for item in ["mqtt_config", "osc_config"]:
            assert item in config, f"Config missing field {item}"

        self.debug = debug
        assert isinstance(config["osc_config"],
                          dict), "OSC config must be a dictionary"
        osc_config = config["osc_config"]
        for item in ["address", "publish_port", "listen_port"]:
            assert item in osc_config, f"osc_config missing field {item}"

        self.osc = udp_client.SimpleUDPClient(osc_config["address"],
                                              osc_config["publish_port"])


        assert isinstance(config["mqtt_config"],
                          dict), "MQTT config must be a dictionary"
                          
        mqtt_config = config["mqtt_config"]
        for item in ["address", "port", "keepalive"]:
            assert item in mqtt_config, f"osc_config missing field {item}"

        if config["publish_topics"]:
            assert isinstance(config["publish_topics"], dict), "publish_topics must be a dictionary of mqtt-topic: osc-topic"
        self.publish_topics = config["publish_topics"]
        
        if config["listen_topics"]:
            assert isinstance(config["listen_topics"], dict), "listen_topics must be a dictionary of osc-topic: mqtt-topic"
        self.listen_topics = config["listen_topics"]
        self.credentials = None

        if "username" in config and "password" in config:
            self.credentials = (config["username"], config["password"])

        assert callable(on_mqtt), "on_mqtt Callback must be a function"
        self.on_mqtt_cb = on_mqtt

        assert callable(on_osc), "on_osc Callback must be a function"
        self.on_osc_cb = on_osc

        # Finally:
        self.__RUN__ = True
        self.__client__ = self.setup_client(mqtt_config)
        self.__server__ = SimpleOSCServer(self, osc_config,
                                        self.on_osc)

    def run(self):
        self.__server__.start()
        while self.__RUN__ and self.is_alive():
            try:
                self.__client__.loop(timeout=1.0)
            except Exception as e:
                print(e)
                self.__server__.stop()
                break
        self.__client__.disconnect()

    def stop(self):
        self.__server__.stop()
        self.__RUN__ = False

    def on_connect(self, client: paho.Client, userdata, flags, rc):
        if rc != 0:
            print(f"Failed to connect [{str(rc)}]:" + paho.connack_string(rc))
            self.__RUN__ = False
        else:
            print(f"Connected to {userdata} | Listening to:")
            osc_escape = '\t -> \t osc|'
            mqtt_escape = '\t -> \tmqtt|'
            for mqtt_topic, osc_topic in self.publish_topics.items():
                client.subscribe(mqtt_topic)
                print(
                    f"\t+ mqtt|{mqtt_topic}{osc_escape + osc_topic if osc_topic else ''}"
                )
            for osc_listen, mqtt_publish in self.listen_topics.items():
                print(
                    f"\t+  osc|{osc_listen}{mqtt_escape + mqtt_publish if mqtt_publish else ''}"
                )

    def on_disconnect(self, client: paho.Client, userdata, rc):
        if rc != 0 and self.__RUN__:
            print(f"Unexpected disconnection:" + paho.connack_string(rc))
            self.__RUN__ = False

    def on_log(self, client, userdata, level, buf):
        print(f"LOG [{level}]: ", buf)

    def on_mqtt(self, client, userdata, message):
        """
        Parse the MQTT message and poke OSC

        :param client: paho MQTT client object.
        :param userdata: the private user data as set in the client object
        :param message: an instance of MQTTMessage. This is a class with members [topic, payload, qos, retain]
        :return: None
        """
        if self.on_mqtt_cb:
            self.on_mqtt_cb(self, message)

    def on_osc(self, address, args):
        if self.on_osc_cb:
            self.on_osc_cb(self, address, args)

    def publish_message(self, topic, value):
        self.__client__.publish(topic=topic, payload=value)

    def setup_client(self, mqtt_config):
        client = paho.Client()
        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.on_message = self.on_mqtt
        if self.debug:
            client.on_log = self.on_log
        client.tls_set_context(ssl.create_default_context())
        client.user_data_set(mqtt_config["address"])
        if mqtt_config["username"] and mqtt_config["password"] :
            client.username_pw_set(mqtt_config["username"], mqtt_config["password"])
        client.connect(mqtt_config["address"], mqtt_config["port"],
                       mqtt_config["keepalive"])
        return client


class SimpleOSCServer(threading.Thread):

    def __init__(self, mqtt, config, callback_fun, debug=False):
        """
        OSC *server* standalone thread class
        Use the '.start()' member to launch this thread.

        :param config: a dictionary containing address, listen_port
        :param callback_fun: message handler function. see :func:`client_subscriber.on_message`
        :param debug: boolean. spam the console.
        """
        super().__init__()
        assert isinstance(config, dict), "Config must be a dictionary"
        for item in ["address", "listen_port"]:
            assert item in config, f"Config missing field {item}"

        self.debug = debug

        self.server_address = config["address"]
        self.server_port = config["listen_port"]

        assert callable(callback_fun), "Callback must be a function"
        self.callback = callback_fun

        # Finally:
        self.server = self.setup_server()

    def run(self):
        try:
            self.server.serve_forever()
        except Exception as e:
            self.server.server_close()
            print(e)

    def stop(self):
        self.server.shutdown()

    def on_message(self, address, args):
        if self.callback:
            self.callback(address, args)

    def setup_server(self):
        message_dispatch = dispatcher.Dispatcher()
        message_dispatch.set_default_handler(self.on_message)
        server = osc_server.OSCUDPServer(
            (self.server_address, self.server_port), message_dispatch)
        return server
