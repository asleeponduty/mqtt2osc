import asyncio

import discord
import time
import datetime as dt
import paho.mqtt.client as paho
import re
import ssl
import struct
import sys
from conf.SECRETS import TOKEN, MQTT_USER, MQTT_PW, MQTT_ADDR

RUN = True
MQTT_CONFIG = {"address": MQTT_ADDR,
               "port": 8883,
               "keepalive": 30,
               "publish_topic": "spartan/pings",
               "username": MQTT_USER,
               "password": MQTT_PW}
ROLE_PING_ID = 651240835664576543
disc_client = discord.Client(max_messages=None, guild_subscriptions=False)
mqtt_client = paho.Client()


def on_connect(client: paho.Client, userdata, flags, rc):
    global RUN
    if rc != 0:
        print(f"Failed to connect [{str(rc)}]:" + paho.connack_string(rc))
        RUN = False
    else:
        print(f'{dt.datetime.now()} Connected to MQTT server [{MQTT_CONFIG["address"]}]!')


def on_disconnect(client: paho.Client, userdata, rc):
    if rc != 0 and RUN:
        print(f"Unexpected disconnection:" + paho.connack_string(rc))


def setup_mqtt():
    global mqtt_client
    print(f'{dt.datetime.now()} Setting up MQTT')
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.tls_set_context(ssl.create_default_context())
    mqtt_client.username_pw_set(MQTT_CONFIG["username"], MQTT_CONFIG["password"])
    mqtt_client.connect(MQTT_CONFIG["address"], MQTT_CONFIG["port"], MQTT_CONFIG["keepalive"])


async def loop_mqtt():
    global mqtt_client
    global RUN
    setup_mqtt()
    while RUN and disc_client and not disc_client.is_closed() and not disc_client.loop.is_closed():
        try:
            mqtt_client.loop(0.5)
            await asyncio.sleep(0.5)
        except Exception:
            RUN = False
            raise


@disc_client.event
async def on_message(message: discord.Message):
    global mqtt_client
    if message.guild is not None:
        count = 0
        count_msg = ""
        for m in re.finditer(f"(<@&{ROLE_PING_ID}>)", message.content, re.IGNORECASE):
            data_struct = struct.pack("!QQQ", time.time_ns(), message.author.id, message.id)
            mqtt_client.publish(topic=MQTT_CONFIG["publish_topic"], payload=data_struct)
            if count > 0:
                count_msg = f" instance {count + 1}"
            print(f'{dt.datetime.now()} Published role mention from [{message.author.name}]{count_msg}')
            count += 1
            sys.stdout.flush()


@disc_client.event
async def on_error(event_method, args, kwargs):
    raise


@disc_client.event
async def on_ready():
    await disc_client.wait_until_ready()
    print(f'{dt.datetime.now()} Connected to Discord as [{disc_client.user.name}]')
    sys.stdout.flush()
    init_activity = discord.Activity(type=discord.ActivityType.listening,
                                     name="phone tag")
    await disc_client.change_presence(activity=init_activity,
                                      status=discord.Status.dnd)
    if disc_client.loop.is_running():
        disc_client.loop.create_task(loop_mqtt())


if __name__ == '__main__':
    print(f'{dt.datetime.now()} Started.')
    disc_client.run(TOKEN)
    disc_client.close()
    print(f'{dt.datetime.now()} bye')
