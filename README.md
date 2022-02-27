# MQTT to OSC listener
Subscribes to a MQTT topic and publishes to an OSC topic. 

This enables automated actions to drive OSC parameters on your local machine. 

With VRChat's adoption of OSC parameter control, this will serve as a great starting point for some neat behaviors

## What?!

When a discord bot, IoT device, or *other* publishes to a MQTT topic on an accessible server, this script will handle that message and emit a signal on a local OSC topic.

In this example, a discord bot listening for a role ping will publish a message to an accessible MQTT server.   
The client subscribes to this topic, and publishes a boolean 'ping' avatar parameter to a running VRChat client on reception. 

## Client:

`client_subscriber.py`: The MQTT to OSC bridge. Listens to the configured MQTT topics and publishes accordingly.  
Hint: This is what you give people

### Client Requirements:

- Read access to a MQTT server on the public internet
- Python3+
- Pip Packages: `paho-mqtt` and  `python-osc`


## Server:

`bot_publisher.py`:  
Uses a discord bot in a server to monitor a role ping. If present, it publishes to an mqtt topic.  
This should be used more as an example with what you can do. 

`discord-ping-monitor.service`:  
Sample linux `systemd` service for running the listen bot, assuming you clone this repository to `/opt/mqtt2osc`

### Server Requirements:

- Write access to a MQTT server on the public internet
- Python3+
- Pip Packages: `paho-mqtt` and `discord.py`

Made by @asleeponduty over the course of a Saturday