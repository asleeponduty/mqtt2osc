"""
client_subscriber.py
Sample MQTT->OSC subscriber/publisher to the role-pinging topic.
This script listens to a publicly readable MQTT* server for a message on a topic. 
On message, it publishes to OSC if valid.

please use `pip install paho-mqtt python-osc` to use this.
Note that in this script, it's expected that the server is TLS-encrypted

@author asleeponduty
"""
import struct
import threading
import time
import paho.mqtt.client as paho
from pythonosc import udp_client
import ssl
from conf.CLIENT_SECRETS import CONFIG


# * * * * * * EXAMPLE * * * * * *
def sample_callback(mqtt, message: paho.MQTTMessage):
    """
    Example callback function for doing things with the data after pinging OSC with it
    :param mqtt: SimpleMQTT2OSC object
    :param message: paho MQTTMessage
    :return: None
    """
    osc_topic = mqtt.topics.get(str(message.topic))
    if osc_topic and message.topic == "spartan/pings":
        # The "spartan/pings" topic has a known structure in this example
        mqtt.osc.send_message(osc_topic, True)
        time_ns, user_id, message_id = struct.unpack("!QQQ", message.payload)
        delta = int((time.time_ns() - time_ns) / 1000000)
        print(f"{message.topic}: user {str(user_id)} in msg {str(message_id)} delta:{delta}ms")
    else:
        # In this example, "public/example" has no osc topic.
        # So instead we just output the message to console
        print(f"{message.topic}: {str(message.payload.decode('utf-8'))}")


# * * * * * * BEGIN * * * * * *
class SimpleMQTT2OSC(threading.Thread):

    def __init__(self, config=CONFIG, callback_fun=sample_callback, debug=False):
        """
        MQTT Listener for managing incoming messages.
        Use the '.start()' member to launch this thread.

        :param config: a dictionary of address, port, keepalive, topic, and optional username/password
        :param callback_fun: message handler function. see :func:`client_subscriber.on_message`
        :param debug: boolean. spam the console.
        """
        super().__init__()
        assert isinstance(config, dict), "Config must be a dictionary"
        for item in ["address", "port", "keepalive", "topics", "osc_config"]:
            assert item in config, f"Config missing field {item}"

        self.debug = debug
        assert isinstance(config["osc_config"], dict), "OSC config must be a dictionary"
        osc_config = config["osc_config"]
        self.osc = udp_client.SimpleUDPClient(osc_config["address"], osc_config["port"])
        self.server_address = config["address"]
        self.server_port = config["port"]
        self.server_keepalive = config["keepalive"]
        self.topics = config["topics"]
        self.credentials = None

        if "username" in config and "password" in config:
            self.credentials = (config["username"], config["password"])

        assert callable(callback_fun), "Callback must be a function"
        self.callback = callback_fun

        # Finally:
        self.__RUN__ = True
        self.__client__ = self.setup_client()

    def run(self):
        while self.__RUN__ and self.is_alive():
            try:
                self.__client__.loop(timeout=1.0)
            except Exception as e:
                print(e)
                break
        self.__client__.disconnect()

    def stop(self):
        self.__RUN__ = False

    def on_connect(self, client: paho.Client, userdata, flags, rc):
        if rc != 0:
            print(f"Failed to connect [{str(rc)}]:" + paho.connack_string(rc))
            self.__RUN__ = False
        else:
            print(f"Connected to {self.server_address} | Listening to:")
            for mqtt_topic, osc_topic in self.topics.items():
                client.subscribe(mqtt_topic)
                print(f"\t+ {mqtt_topic}")

    def on_disconnect(self, client: paho.Client, userdata, rc):
        if rc != 0 and self.__RUN__:
            print(f"Unexpected disconnection:" + paho.connack_string(rc))
            self.__RUN__ = False

    def on_log(self, client, userdata, level, buf):
        print(f"LOG [{level}]: ", buf)

    def on_message(self, client, userdata, message):
        """
        Parse the MQTT message and poke OSC

        :param client: paho MQTT client object.
        :param userdata: the private user data as set in the client object
        :param message: an instance of MQTTMessage. This is a class with members [topic, payload, qos, retain]
        :return: None
        """
        if self.callback:
            self.callback(self, message)

    def setup_client(self):
        client = paho.Client()
        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.on_message = self.on_message
        if self.debug:
            client.on_log = self.on_log
        client.tls_set_context(ssl.create_default_context())
        if self.credentials:
            client.username_pw_set(self.credentials[0], self.credentials[1])
        client.connect(self.server_address, self.server_port, self.server_keepalive)
        return client


if __name__ == '__main__':
    # using defaults provided above
    print("Starting @PING-to-VRC OSC listener")
    print("This will set '/avatar/ping' to TRUE every time a ping comes in.")
    print("Press CTRL+C in this window to quit")
    listener = SimpleMQTT2OSC()
    listener.start()

    # spin forever as this is a sample:
    try:
        while listener.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        listener.stop()

    listener.join(1)
    print("bye")
