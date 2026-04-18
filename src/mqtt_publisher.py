"""
mqtt_publisher.py
------------------
MQTT protokolü ile sensör verisi yayınlar.
Ücretsiz HiveMQ public broker kullanır, kayıt gerekmez.

Topic yapısı:
  iot/sensors/{sensor_id}/all   - tüm veriler JSON

Kullanım:
  python mqtt_publisher.py
"""

import paho.mqtt.client as mqtt
import json
import time
import random
import math
import logging
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

BROKER     = os.getenv("MQTT_BROKER", "broker.hivemq.com")
PORT       = int(os.getenv("MQTT_PORT", 1883))
TOPIC_BASE = "iot/sensors"
CLIENT_ID  = f"iot-publisher-{int(time.time())}"


def on_connect(client, userdata, flags, rc):
    codes = {
        0: "Bağlantı başarılı",
        1: "Hatalı protokol versiyonu",
        2: "Geçersiz client ID",
        3: "Sunucu kullanılamıyor",
        4: "Hatalı kullanıcı adı/şifre",
        5: "Yetkisiz",
    }
    logger.info(f"MQTT Broker: {codes.get(rc, 'Bilinmeyen hata')}")


def on_publish(client, userdata, mid):
    logger.debug(f"Mesaj yayınlandı: mid={mid}")


def generate_reading(sensor_id: str) -> dict:
    """Gerçekçi sensör verisi üret."""
    hour  = datetime.now().hour
    cycle = math.sin((hour - 6) * math.pi / 12)
    return {
        "sensor_id":   sensor_id,
        "timestamp":   int(time.time()),
        "datetime":    datetime.now(timezone.utc).isoformat(),
        "temperature": round(22 + cycle * 6 + random.gauss(0, 0.5), 2),
        "humidity":    round(55 - cycle * 8 + random.gauss(0, 1.5), 2),
        "pressure":    round(1013.0 + random.gauss(0, 1.5), 2),
        "co2_ppm":     round(410 + random.gauss(0, 10), 1),
    }


def main():
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_publish = on_publish

    logger.info(f"MQTT Broker'a bağlanılıyor: {BROKER}:{PORT}")
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()

    sensors = ["ankara-01", "ankara-02", "ankara-03"]

    logger.info(f"Yayın başlıyor. Durdurmak için Ctrl+C")

    try:
        while True:
            for sensor_id in sensors:
                reading = generate_reading(sensor_id)
                topic   = f"{TOPIC_BASE}/{sensor_id}/all"
                client.publish(topic, json.dumps(reading), qos=1)
                logger.info(
                    f"[{sensor_id}] "
                    f"Temp: {reading['temperature']}°C | "
                    f"Nem: {reading['humidity']}% | "
                    f"CO2: {reading['co2_ppm']} ppm"
                )
            time.sleep(3)

    except KeyboardInterrupt:
        logger.info("Durduruluyor...")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()