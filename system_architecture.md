# Sistem Tasarımı: GaitProject

## 1. Genel Mimari
GaitProject, yürüyüş analizi için bir uçtan uca çözüm sunar. Sistem, canlı kamera verisini işler, adım ve simetri metriklerini hesaplar, yapay zeka tabanlı sınıflandırma yapar ve sonuçları doktor onay sürecine gönderir.

Mimari üç ana katmandan oluşur:
- Donanım ve görüntü alma
- Hesaplama ve veri işleme
- Web tabanlı doktor paneli

Sistem hem yerel hem de klinik kullanım için tasarlanmıştır. Python tabanlı çekirdek modül `pose_detect.py` içinde yürütülen algoritmalar, Flask web sunucusu üzerinden güvenli bir doktor onay arayüzüyle entegre edilir.

## 2. Kamera Sistemi
Kamera sistemi, öncelikle kaldır vücut hareketlerini yakalamak için MediaPipe Pose ve OpenCV kullanır. Önerilen yerleşim:
- Sagittal/dikey görüş: diz hareketlerini ve ayak konumunu doğru tespit etmek için en ideal görüntü.
- Sabit bir arka plan ve iyi aydınlatma, hareketli nesnelerin neden olduğu yanlış pozladılamayı azaltır.

Donanım bileşenleri:
- USB kamera veya entegre dizüstü bilgisayarı kamerası
- 30 FPS veya daha yüksek görüntü hızı
- Çözünürlük olarak en az 640x480

Kamera girişi OpenCV ile alınır, ardından MediaPipe, gövde eklemlerini çıkararak eklem açılarını ve ayak konumunu belirler.

## 3. Veri Akışı
Veri akışı aşağıdaki adımlarla ilerler:
1. Kamera çerçevesi yakalanır.
2. MediaPipe Pose, insan vücut noktalarını çıkarır.
3. Poz koordinatlarından diz ve kalça açıları hesaplanır.
4. Adım deteksiyonu için diz açılarındaki değişim ve ayak yüksekliği analiz edilir.
5. Simetri indeksi, hız ve asimetri metrikleri hesaplanır.
6. Sonuçlar ön yüz için saklanır ve analize kayıt edilir.
7. Doktor onayı gerekiyorsa sonuçlar `gait.db` veritabanına yazılır.

Veri akışı, hem canlı analiz hem de sonrasında onay sürecine uygun olacak şekilde düzenlenir. Her analiz sonucunda `analyses` tablosuna kayıt eklenir.

## 4. Modüller
Sistem modüler bir yapıya sahiptir. Temel modüller:
- Görüntü işleme
- Adım tespiti
- Asimetri analizi
- AI modeli
- Doktor paneli

Bu modüller birbirine gevşek bağlıdır; böylece bir modülün hata vermesi diğerlerinin çalışmasını tamamen durdurmaz.

## 5. Görüntü İşleme
Görüntü işleme modülü, çerçeveleri ön işler ve MediaPipe ile eklem noktalarını çıkarır.
- `pose_detect.py` içinde OpenCV ile çerçeve yakalama
- MediaPipe Pose ile yüz, omuz, kalça, diz, ayak bileği ve ayak noktalarının çıkarılması
- Eşikli filtreler ve düşük geçirgen filtreler ile gürültü azaltımı

Açılar hesaplarken kullanılan fonksiyonlar:
- `calculate_angle()`
- `distance()`
- `estimate_pixel_to_cm_scale()`

Bu modül, gerçek zamanlı analiz için optimize edilmiştir ve GPU olmadan çalışabilecek şekilde tasarlanmıştır.

## 6. Adım Tespiti
Adım tespiti, diz açılarının belirli eşiklerin altına düşmesi ve tekrar yükselmesi mantığına dayanır.
- `STEP_BEND_THRESHOLD` ve `STEP_STRAIGHTEN_THRESHOLD` gibi sabitler kullanılır
- Her iki ayak için de adım sayıları ayrı ayrı hesaplanır
- Toplam adım sayısı, her iki ayak için eşiklenen adım sayısının iki katı olarak belirlenir

Bu modül, gerçek adım döngüsünü yakalamak için zaman ve açı toleransları kullanır. Minimum adım aralığı garantisi, aynı adımdan çoklu tespitleri önler.

## 7. Asimetri Analizi
Asimetri analizi, sol ve sağ taraf arasındaki farkları ölçer.
- Simetri indeksi: `|sol - sağ| / ortalama × 100`
- Adım süreleri ve adım yüksekliği farkları analiz edilir
- `avg_asymmetry` ve `z_variation` gibi metrikler hesaplanır

Bu analiz, yürüyüş bozuklukları, denge sorunları ve potansiyel patolojilerin tespitinde klinik olarak anlamlı girişimler sunar.

## 8. AI Modeli
Sistemde hem kural tabanlı sınıflandırma hem de isteğe bağlı yapay zeka modeli vardır.
- `pose_detect.py` içinde `classification_report` ve `confusion_matrix` desteği
- XGBoost tabanlı model (varsa) için otomatik eğitim/yeniden eğitim hattı
- Modelin çıktısı `ai_prediction` alanında saklanır

AI modelinin rolü:
- Yürüyüş durumunu `NORMAL` veya `ABNORMAL` olarak tahmin etmek
- Hastalık olasılıklarını desteklemek
- Onaylanmış doktor etiketleri ile gelecekteki eğitim verisini zenginleştirmek

Model yoksa sistem sebat eder ve sadece kural tabanlı sonuçlar kullanır.

## 9. Doktor Paneli
Doktor paneli Flask tabanlıdır ve şu özellikleri içerir:
- Doktor giriş ve oturum yönetimi
- Bekleyen analizlerin listelenmesi
- AJAX ile onay gönderme
- `doctor_label` alanının kaydedilmesi

Panelde sunulan akış:
1. Doktor `/login` üzerinden girer.
2. `/review` sayfasında doktor onay bekleyen kayıtları görür.
3. Her kayıt için `NORMAL` veya `ABNORMAL` seçebilir.
4. Onaylandığında kayıt veritabanına işlenir ve kullanıcıya satır anında kaldırılır.

Ayrıca `dashboard` API'si doktor paneline genel analiz sayısı ve durumu sağlar.

## 10. Entegrasyon ve Çıktılar
Sistem, canlı görüntü işleme ve web tabanlı değerlendirmeyi entegre eder.
- `gait.db` içinde kalıcı analiz kaydı
- `gait_dataset.csv` veya eğitim hattına yazılan onaylı etiketler
- Doğrulanmış sonuçlar `doctor_label` ile kayıt altına alınır

Gelecek geliştirmeler:
- Hasta geçmişi sayfaları
- Gelişmiş filtreleme ve raporlama
- Gerçek zamanlı video dashboard entegrasyonu
- Klinik kullanıcı dostu arayüz iyileştirmeleri

Bu mimari, hem araştırma hem de klinik değerlendirme için esnek bir temel sunar.
