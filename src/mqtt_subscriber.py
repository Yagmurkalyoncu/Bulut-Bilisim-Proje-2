"""
mqtt_subscriber.py
-------------------
MQTT topic'lerini dinler, gelen veriyi AWS Kinesis'e iletir.
mqtt_publisher.py ile birlikte kullanılır.

Kullanım:
  Terminal 1: python mqtt_publisher.py
  Terminal 2: python mqtt_subscriber.py
"""

import paho.mqtt.client as mqtt
import json
import boto3
import logging
import os
import time
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

BROKER      = os.getenv("MQTT_BROKER", "broker.hivemq.com")
PORT        = int(os.getenv("MQTT_PORT", 1883))
TOPIC_SUB   = "iot/sensors/+/all"
STREAM_NAME = os.getenv("KINESIS_STREAM_NAME", "iot-sensor-stream")
CLIENT_ID   = f"iot-subscriber-{int(time.time())}"

kinesis = boto3.client(
    "kinesis",
    region_name=os.getenv("AWS_REGION", "eu-west-1"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

received_count = 0


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"Broker'a bağlandı. Topic dinleniyor: {TOPIC_SUB}")
        client.subscribe(TOPIC_SUB, qos=1)
    else:
        logger.error(f"Bağlantı hatası: rc={rc}")


def on_message(client, userdata, msg):
    global received_count
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        received_count += 1

        # Kinesis'e ilet
        kinesis.put_record(
            StreamName=STREAM_NAME,
            Data=msg.payload,
            PartitionKey=data.get("sensor_id", "unknown")
        )
        logger.info(
            f"[#{received_count}] MQTT → Kinesis | "
            f"Topic: {msg.topic} | "
            f"Temp: {data.get('temperature')}°C"
        )
    except Exception as e:
        logger.error(f"Mesaj işleme hatası: {e}")


def main():
    client = mqtt.Client(client_id=CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message

    logger.info(f"MQTT Broker'a bağlanılıyor: {BROKER}:{PORT}")
    client.connect(BROKER, PORT, keepalive=60)
    logger.info("Dinleniyor... Ctrl+C ile durdur.")
    client.loop_forever()


if __name__ == "__main__":
    main()