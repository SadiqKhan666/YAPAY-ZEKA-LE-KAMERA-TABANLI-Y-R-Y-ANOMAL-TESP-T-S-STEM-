# Yapay Zeka ile Kamera Tabanlı Yürüyüş Anomali Tespit Sistemi

Kamera görüntüsünden insan pozu çıkararak yürüyüş özelliklerini analiz eden ve anormal yürüyüş durumlarını tespit etmeye yardımcı olan Python tabanlı web uygulaması.

## Teknolojiler

- Python
- Flask
- OpenCV
- MediaPipe Pose
- NumPy
- SQLite
- Makine öğrenimi model ağırlıkları (`.pkl`)

## Çalıştırma

```powershell
python -m pip install -r requirements.txt
python flask_server.py
```

Uygulama başladıktan sonra tarayıcıdan `http://127.0.0.1:5000` adresini açın.

## Klasörler

- `models/`: Model ağırlıkları
- `templates/`: Flask HTML şablonları
- `static/`: Statik web arayüzü dosyaları
- `pose_detect.py`: Kamera ve poz tespit işlemleri
- `flask_server.py`: Web sunucusu ve analiz akışı
