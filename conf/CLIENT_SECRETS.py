# Localhost and port 9000 are the default VRChat OSC Listen ports
OSC_CONFIG = {
    "address": "127.0.0.1",
    "publish_port": 9000,
    "listen_port": 9001
}
MQTT_CONFIG = {
    "address": "example.com",
    "port": 8883,
    "keepalive": 30,
    "username": "optionalusername",
    "password": "thepassword"
}
# This setup assumes the MQTT server is publicly accessible
# and is tls-encrypted
CONFIG = {
    "publish_topics": {
        "spartan/pings": "/avatar/parameters/ping",
        "spartan/public/alert": "/avatar/parameters/alert",
        "public/example": None
    },
    "listen_topics": {
        "/avatar/parameters/alertall": "spartan/public/alert"
    },
    "osc_config": OSC_CONFIG,
    "mqtt_config": MQTT_CONFIG
}
