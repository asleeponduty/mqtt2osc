"""
client.py
Sample bidirectional MQTT<->OSC subscriber/publisher.
1. This script listens to a publicly readable MQTT* server for a message on a topic. 
On message, it publishes to OSC if valid.

2. This script starts an OSC server which handles all incoming messages. 
If a message appears on a configured topic and it's value is 'True', 
it publishes a MQTT message to the configured topic and then
sets the value of the OSC topic to 'False'

please use `pip install paho-mqtt python-osc` to use this.
Note that in this script, it's expected that the server is TLS-encrypted

@author asleeponduty
"""
import struct
import time
import paho.mqtt.client as paho

import uuid
from client_utils import SimpleMQTT2OSC

MY_UUID = uuid.getnode()

# * * * * * * EXAMPLE * * * * * *
def sample_on_mqtt(mqtt2osc: SimpleMQTT2OSC, message: paho.MQTTMessage):
    """
    Example callback function for doing things with the data after pinging OSC with it
    :param mqtt: SimpleMQTT2OSC object
    :param message: paho MQTTMessage
    :return: None
    """
    osc_topic = mqtt2osc.publish_topics.get(str(message.topic))
    if osc_topic:
        mqtt2osc.osc.send_message(osc_topic, True)
        # The "spartan/pings" topic has a known structure in this example
        if message.topic == "spartan/pings":
            time_ns, user_id, message_id = struct.unpack(
                "!QQQ", message.payload)
            delta = int((time.time_ns() - time_ns) / 1000000)
            print(
                f"{message.topic}: user {str(user_id)} in msg {str(message_id)} delta:{delta}ms"
            )
        elif message.topic == "spartan/public/alert":
            print(f"{message.topic}: a SPARTAN is in need of your help!")
    else:
        # In this example, "public/example" has no osc topic.
        # So instead we just output the message to console
        print(f"{message.topic}: {str(message.payload.decode('utf-8'))}")


def sample_on_osc(mqtt2osc: SimpleMQTT2OSC, address, args):
    """
    Example callback function for handling an incoming OSC message
    :param mqtt: SimpleMQTT2OSC object
    :param address: message topic. 
    :param args: value of the topic message 
    :return: None
    """
    mqtt_topic = mqtt2osc.listen_topics.get(str(address))
    if mqtt_topic:
        if args == True:
            data_struct = struct.pack("!QQQ", time.time_ns(), MY_UUID, 0)
            mqtt2osc.publish_message(mqtt_topic, data_struct)
            print(f"{address}: published to {mqtt_topic}")
            mqtt2osc.osc.send_message(address, False)



if __name__ == '__main__':
    # using defaults provided above
    print("Starting @PING-to-VRC OSC listener")
    print("This will set '/avatar/ping' to TRUE every time a ping comes in.")
    print(" and will set '/avatar/public/alert' to TRUE every time avatar parameter 'alertall' is TRUE.")
    print("Press CTRL+C in this window to quit")
    listener = SimpleMQTT2OSC(on_mqtt=sample_on_mqtt, on_osc=sample_on_osc)
    listener.start()

    # spin forever as this is a sample:
    try:
        while listener.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("CTRL+C")
        listener.stop()

    listener.join(1)
    print("bye")