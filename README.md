
# IoT Gerçek Zamanlı Veri Akışı Projesi

> 3522 Bulut Bilişim Dersi — Proje 2

## 📌 Proje Özeti

Python ile gerçek zamanlı IoT sensör verisi simüle edilir. WebSocket üzerinden toplanan veriler AWS Kinesis Data Streams'e gönderilir. Lambda fonksiyonu bu veriyi işleyerek DynamoDB'ye kaydeder. Streamlit dashboard ile canlı görselleştirme yapılır.

## 🎥 Proje Videosu
https://youtu.be/9Bd3GAjUrng?si=uIQiNuqLXblM1K6B

## ✅ Sistem Durumu
- Kinesis Stream: `iot-sensor-stream` (us-east-1)
- DynamoDB: `IoTSensorData` 
- Lambda: `iot-kinesis-processor`
- Dashboard: `streamlit run dashboard/dashboard.py`
- Sensörler: Ankara-Merkez, Çankaya, Keçiören, Gölbaşı
## 🏗️ Sistem Mimarisi

```
Sensör Simülatörü (Python)
        ↓ WebSocket (ws://localhost:8765)
Kinesis Producer
        ↓ AWS SDK (boto3)
AWS Kinesis Data Streams
        ↓ Trigger (otomatik)
AWS Lambda Fonksiyonu
        ↓ boto3
AWS DynamoDB
        ↑
Streamlit Dashboard (okuma)
```

## 🛠️ Kullanılan Teknolojiler

| Katman | Teknoloji |
|--------|-----------|
| Backend dili | Python 3.11 |
| Protokol | WebSocket (`websockets` kütüphanesi) |
| Alternatif protokol | MQTT (`paho-mqtt`, HiveMQ broker) |
| Veri akışı | AWS Kinesis Data Streams |
| İşleme | AWS Lambda |
| Veritabanı | AWS DynamoDB |
| Dashboard | Streamlit + Plotly |
| İzleme | AWS CloudWatch |

## 📁 Proje Yapısı

```
iot-cloud-project/
├── src/
│   ├── sensor_simulator.py   # IoT sensör simülatörü (WebSocket sunucusu)
│   ├── kinesis_producer.py   # WebSocket → AWS Kinesis köprüsü
│   ├── mqtt_publisher.py     # MQTT alternatif yayıncı
│   ├── mqtt_subscriber.py    # MQTT → Kinesis köprüsü
│   └── aws_setup.py          # AWS kaynak kurulum scripti
├── lambda/
│   └── lambda_function.py    # Kinesis → DynamoDB Lambda fonksiyonu
├── dashboard/
│   └── dashboard.py          # Streamlit gerçek zamanlı dashboard
├── docs/
│   └── report.pdf            # Proje raporu
├── requirements.txt
├── .env.example              # Ortam değişkenleri şablonu
└── README.md
```


## 📊 Veri Formatı

Her sensör kaydı şu alanları içerir:

```json
{
  "device_id": "sensor-ankara-01",
  "location": "Ankara-Merkez",
  "timestamp": 1718000000,
  "datetime": "2024-06-10T12:00:00+00:00",
  "temperature": 24.35,
  "humidity": 58.72,
  "pressure": 1014.5,
  "light": 320.0,
  "co2_ppm": 415.3
}
```

