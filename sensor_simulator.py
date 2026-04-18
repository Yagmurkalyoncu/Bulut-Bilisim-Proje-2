"""
sensor_simulator.py
--------------------
Gerçek zamanlı IoT sensör verisi simüle eder.
WebSocket sunucusu olarak çalışır: ws://localhost:8765

Üretilen veriler:
  - Sıcaklık (°C)
  - Nem (%)
  - Basınç (hPa)
  - Işık yoğunluğu (lux)
  - CO2 seviyesi (ppm)

Kullanım:
  python sensor_simulator.py
"""

import asyncio
import websockets
import json
import random
import time
import math
import logging
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Bağlı istemcileri takip et
connected_clients: set = set()

# Sensör konfigürasyonu
SENSORS = [
    {"id": "sensor-ankara-01", "location": "Ankara-Merkez",  "floor": 1},
    {"id": "sensor-ankara-02", "location": "Ankara-Çankaya", "floor": 2},
    {"id": "sensor-ankara-03", "location": "Ankara-Keçiören", "floor": 3},
]


def generate_sensor_data(sensor: dict, tick: int) -> dict:
    """
    Gerçekçi sensör verisi üretir.
    Gün içi değişimi simüle etmek için sinüs dalgası kullanır.
    """
    hour = datetime.now().hour
    # Gün içi sıcaklık değişimi: sabah soğuk, öğle sıcak
    daily_cycle = math.sin((hour - 6) * math.pi / 12)

    # Her sensör için hafif farklı baseline değerler
    base_temp = 20 + sensor["floor"] * 0.5

    return {
        "device_id":    sensor["id"],
        "location":     sensor["location"],
        "timestamp":    int(time.time()),
        "datetime":     datetime.now(timezone.utc).isoformat(),
        "temperature":  round(base_temp + daily_cycle * 8 + random.gauss(0, 0.3), 2),
        "humidity":     round(60 - daily_cycle * 10 + random.gauss(0, 1.0), 2),
        "pressure":     round(1013.25 + random.gauss(0, 2.0), 2),
        "light":        round(max(0, 500 * daily_cycle + random.gauss(0, 20)), 1),
        "co2_ppm":      round(400 + random.gauss(0, 15) + tick % 50, 1),
        "tick":         tick
    }


async def broadcast_to_all(message: str):
    """Tüm bağlı istemcilere veri gönder."""
    if connected_clients:
        await asyncio.gather(
            *[client.send(message) for client in connected_clients],
            return_exceptions=True
        )


async def sensor_handler(websocket):
    """
    Yeni bir WebSocket bağlantısı geldiğinde çalışır.
    İstemciyi kayıt eder, bağlantı kopunca temizler.
    """
    client_addr = websocket.remote_address
    connected_clients.add(websocket)
    logger.info(f"Yeni bağlantı: {client_addr} | Toplam: {len(connected_clients)}")

    try:
        # Bağlantıyı açık tut
        await websocket.wait_closed()
    finally:
        connected_clients.discard(websocket)
        logger.info(f"Bağlantı kapandı: {client_addr} | Toplam: {len(connected_clients)}")


async def data_producer():
    """
    Arka planda her 2 saniyede bir tüm sensörlerden veri üretip yayınlar.
    """
    tick = 0
    logger.info("Veri üretici başladı. Her 2 saniyede veri yayınlanacak...")

    while True:
        for sensor in SENSORS:
            data = generate_sensor_data(sensor, tick)
            message = json.dumps(data, ensure_ascii=False)

            if connected_clients:
                await broadcast_to_all(message)
                logger.info(
                    f"[{sensor['id']}] "
                    f"Temp: {data['temperature']}°C | "
                    f"Nem: {data['humidity']}% | "
                    f"CO2: {data['co2_ppm']} ppm"
                )

        tick += 1
        await asyncio.sleep(2)


async def main():
    host = "localhost"
    port = 8765

    logger.info("=" * 50)
    logger.info("IoT Sensör Simülatörü Başlatılıyor")
    logger.info(f"WebSocket adresi: ws://{host}:{port}")
    logger.info(f"Aktif sensör sayısı: {len(SENSORS)}")
    logger.info("=" * 50)

    # WebSocket sunucusu ve veri üreticiyi paralel çalıştır
    async with websockets.serve(sensor_handler, host, port):
        await data_producer()


if __name__ == "__main__":
    asyncio.run(main())
