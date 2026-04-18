import paho.mqtt.client as mqtt
import boto3
import json
import os
from dotenv import load_dotenv

# .env dosyasındaki AWS bilgilerini yükle 
load_dotenv()

# AWS Kinesis Yapılandırması [cite: 10, 27]
kinesis_client = boto3.client(
    'kinesis',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)
STREAM_NAME = os.getenv('KINESIS_STREAM_NAME')

# MQTT Yapılandırması [cite: 7]
MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "bulut_bilisim/iot_sensor"

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"MQTT Broker'a bağlandı. Sonuç: {rc}")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        # MQTT'den gelen veriyi çöz [cite: 3]
        payload = msg.payload.decode()
        data = json.loads(payload)
        print(f"Veri Alındı: {data}")

        # Veriyi AWS Kinesis'e gönder [cite: 4, 12]
        kinesis_client.put_record(
            StreamName=STREAM_NAME,
            Data=json.dumps(data),
            PartitionKey=data.get('device_id', 'default_id')
        )
        print("AWS Kinesis'e başarıyla aktarıldı.")
    except Exception as e:
        print(f"Hata: {e}")

# MQTT Client kurulumu [cite: 29]
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

print("MQTT dinleniyor...")
client.connect(MQTT_BROKER, 1883, 60)
client.loop_forever()