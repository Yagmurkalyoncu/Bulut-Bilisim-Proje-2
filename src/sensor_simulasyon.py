import json
import random
import time
from datetime import datetime

# Proje 2: IoT Veri Simülatörü
def veri_uret():
    # Raporda istenen basit veri akışı yapısı [cite: 15]
    sensor_id = "IOT-DEVICE-01"
    sicaklik = round(random.uniform(20.0, 30.0), 2)
    nem = round(random.uniform(40.0, 60.0), 2)
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "device_id": sensor_id,
        "temperature": sicaklik,
        "humidity": nem,
        "timestamp": zaman
    }

if __name__ == "__main__":
    print("Gerçek zamanlı veri akışı simüle ediliyor... [Ctrl+C ile durdur]")
    while True:
        data = veri_uret()
        print(f"Gönderilen Veri: {json.dumps(data)}")
        time.sleep(2) # Veri akış hızı