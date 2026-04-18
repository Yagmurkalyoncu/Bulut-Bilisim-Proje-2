"""
lambda_function.py
-------------------
AWS Lambda fonksiyonu.
Kinesis Data Streams tarafından otomatik tetiklenir.

Görevler:
  1. Kinesis record'larını decode et (base64)
  2. JSON parse et
  3. Anomali tespiti yap (yüksek sıcaklık uyarısı)
  4. DynamoDB'ye yaz
  5. CloudWatch'a log at

DEPLOYMENT:
  Bu dosyayı ZIP'leyip AWS Lambda'ya yükleyin:
    zip lambda_function.zip lambda_function.py
  
  Konfigürasyon:
    - Runtime: Python 3.11
    - Handler: lambda_function.lambda_handler
    - Timeout: 30 saniye
    - Memory: 128 MB (yeterli)
    - Trigger: Kinesis stream (iot-sensor-stream), batch size: 10
"""

import json
import boto3
import base64
import logging
from decimal import Decimal
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
table    = dynamodb.Table("IoTSensorData")

# SNS client (anomali bildirimleri için - isteğe bağlı)
# sns = boto3.client("sns")
# ALERT_TOPIC_ARN = "arn:aws:sns:eu-west-1:ACCOUNT_ID:iot-alerts"

TEMP_ALERT_THRESHOLD = 30.0  # °C üzeri uyarı


def float_to_decimal(obj):
    """
    DynamoDB float kabul etmez, Decimal gerektirir.
    JSON'daki tüm float değerleri Decimal'a çevirir.
    """
    if isinstance(obj, float):
        return Decimal(str(round(obj, 4)))
    elif isinstance(obj, dict):
        return {k: float_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [float_to_decimal(i) for i in obj]
    return obj


def check_anomaly(data: dict) -> dict | None:
    """Basit anomali tespiti."""
    alerts = []

    if data.get("temperature", 0) > TEMP_ALERT_THRESHOLD:
        alerts.append(f"Yüksek sıcaklık: {data['temperature']}°C")

    if data.get("humidity", 0) > 90:
        alerts.append(f"Yüksek nem: {data['humidity']}%")

    if data.get("co2_ppm", 0) > 1000:
        alerts.append(f"Yüksek CO2: {data['co2_ppm']} ppm")

    return alerts if alerts else None


def lambda_handler(event, context):
    """
    Ana Lambda handler.
    event["Records"] içinde Kinesis kayıtları gelir.
    """
    processed = 0
    errors    = 0
    alerts    = 0

    for record in event.get("Records", []):
        try:
            # 1. Base64 decode + JSON parse
            raw     = base64.b64decode(record["kinesis"]["data"])
            data    = json.loads(raw.decode("utf-8"))

            device_id = data.get("device_id") or data.get("sensor_id", "unknown")
            timestamp = data.get("timestamp", 0)

            # 2. Anomali kontrolü
            anomaly_alerts = check_anomaly(data)
            if anomaly_alerts:
                alerts += 1
                logger.warning(
                    f"ANOMALI [{device_id}]: {', '.join(anomaly_alerts)}"
                )
                # İsteğe bağlı: SNS ile bildirim gönder
                # sns.publish(TopicArn=ALERT_TOPIC_ARN, Message=str(anomaly_alerts))

            # 3. DynamoDB item hazırla
            item = float_to_decimal({
                "device_id":   device_id,
                "timestamp":   timestamp,
                "location":    data.get("location", "unknown"),
                "temperature": data.get("temperature"),
                "humidity":    data.get("humidity"),
                "pressure":    data.get("pressure"),
                "light":       data.get("light"),
                "co2_ppm":     data.get("co2_ppm"),
                "has_alert":   bool(anomaly_alerts),
                "alerts":      anomaly_alerts or [],
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "kinesis_seq": record["kinesis"]["sequenceNumber"][:40],
            })

            # 4. DynamoDB'ye yaz
            table.put_item(Item=item)
            processed += 1

            logger.info(
                f"[{device_id}] Kaydedildi | "
                f"Temp: {data.get('temperature')}°C | "
                f"Nem: {data.get('humidity')}%"
            )

        except Exception as e:
            errors += 1
            logger.error(f"Kayıt işleme hatası: {e} | Record: {record}")

    logger.info(
        f"Batch tamamlandı | "
        f"İşlenen: {processed} | "
        f"Hata: {errors} | "
        f"Uyarı: {alerts}"
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "processed": processed,
            "errors":    errors,
            "alerts":    alerts
        })
    }
