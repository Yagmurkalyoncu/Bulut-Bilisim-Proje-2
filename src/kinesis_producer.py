"""
kinesis_producer.py
--------------------
WebSocket sunucusundan veri alır ve AWS Kinesis Data Streams'e gönderir.

Akış:
  sensor_simulator.py (ws://localhost:8765)
      → kinesis_producer.py
          → AWS Kinesis Data Streams (iot-sensor-stream)
              → Lambda (otomatik tetiklenir)
                  → DynamoDB

Kullanım:
  python kinesis_producer.py

Gereksinimler:
  - .env dosyasında AWS kimlik bilgileri tanımlı olmalı
  - Kinesis stream önceden oluşturulmuş olmalı (aws_setup.py ile)
"""

import asyncio
import websockets
import json
import boto3
import logging
import os
import time
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# AWS Kinesis istemcisi
kinesis = boto3.client(
    "kinesis",
    region_name=os.getenv("AWS_REGION", "eu-west-1"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

STREAM_NAME = os.getenv("KINESIS_STREAM_NAME", "iot-sensor-stream")
WS_URI      = f"ws://{os.getenv('WEBSOCKET_HOST','localhost')}:{os.getenv('WEBSOCKET_PORT','8765')}"

# İstatistik sayaçları
stats = {"sent": 0, "errors": 0, "start_time": time.time()}


def send_to_kinesis(data: dict) -> bool:
    """
    Tek bir kaydı Kinesis'e gönderir.
    PartitionKey olarak device_id kullanılır — aynı sensör
    verileri hep aynı shard'a gider (sıra garantisi).
    """
    try:
        response = kinesis.put_record(
            StreamName=STREAM_NAME,
            Data=json.dumps(data).encode("utf-8"),
            PartitionKey=data["device_id"]
        )
        shard_id    = response["ShardId"]
        sequence_no = response["SequenceNumber"][:20] + "..."
        logger.debug(f"Kinesis OK | Shard: {shard_id} | Seq: {sequence_no}")
        return True

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(f"Kinesis hatası [{error_code}]: {e}")
        return False


async def consume_and_forward():
    """
    WebSocket bağlantısını açık tutar, gelen her mesajı
    parse edip Kinesis'e iletir.
    Bağlantı koptuğunda 5 saniye bekleyip yeniden dener.
    """
    retry_delay = 5

    while True:
        try:
            logger.info(f"WebSocket'e bağlanılıyor: {WS_URI}")
            async with websockets.connect(WS_URI) as ws:
                logger.info("WebSocket bağlantısı kuruldu. Veri bekleniyor...")
                retry_delay = 5  # Başarılı bağlantıda sıfırla

                async for raw_message in ws:
                    data = json.loads(raw_message)

                    success = send_to_kinesis(data)

                    if success:
                        stats["sent"] += 1
                        logger.info(
                            f"✓ [{data['device_id']}] → Kinesis | "
                            f"Temp: {data['temperature']}°C | "
                            f"Toplam gönderilen: {stats['sent']}"
                        )
                    else:
                        stats["errors"] += 1

        except websockets.exceptions.ConnectionRefusedError:
            logger.warning(f"WebSocket sunucusuna bağlanılamadı. {retry_delay}s sonra tekrar denenecek...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)  # Exponential backoff, max 60s

        except Exception as e:
            logger.error(f"Beklenmeyen hata: {e}")
            await asyncio.sleep(retry_delay)


def print_stats():
    """Gönderilen/hata istatistiklerini yazdır."""
    elapsed = time.time() - stats["start_time"]
    rate    = stats["sent"] / elapsed if elapsed > 0 else 0
    logger.info(
        f"İstatistikler → Gönderilen: {stats['sent']} | "
        f"Hata: {stats['errors']} | "
        f"Hız: {rate:.2f} kayıt/s"
    )


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Kinesis Producer Başlatılıyor")
    logger.info(f"Hedef stream: {STREAM_NAME}")
    logger.info(f"Bölge: {os.getenv('AWS_REGION', 'eu-west-1')}")
    logger.info("=" * 50)

    try:
        asyncio.run(consume_and_forward())
    except KeyboardInterrupt:
        logger.info("Durduruluyor...")
        print_stats()
