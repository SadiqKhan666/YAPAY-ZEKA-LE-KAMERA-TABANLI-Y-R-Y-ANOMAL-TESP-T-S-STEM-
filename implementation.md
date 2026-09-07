# Uygulama (Implementation)

## 1. Kullanılan Teknolojiler
Bu bölümde GaitProject uygulamasında kullanılan temel teknolojiler ve bunların rolleri açıklanmaktadır.

- Python: Sistem çekirdeği, veri işleme, model çalıştırma ve raporlama için kullanılan birincil dildir.
- OpenCV: Kamera verisini almak, çerçeve işlemek ve görüntü analizi için kullanılır.
- MediaPipe: Poz kestirimi ve iskelet anahtar noktalarının çıkarılması için kullanılır.
- Flask: Web tabanlı dokümantasyon ve doktor paneli sağlamak için kullanılan Python web çatısıdır.
- SQLite: Hasta ve analiz verilerini yerel olarak saklamak için kullanılan gömülü veritabanıdır.
- HTML/CSS/JavaScript: Doktor arayüzü, onay paneli ve etkileşimli istemci tarafı davranışı için kullanılır.
- ReportLab: PDF raporlarını oluşturmak için Python kütüphanesidir.

---

## 2. Python / OpenCV

2.1 Python Serbestliği
- Uygulama, `pose_detect.py` içinde OpenCV ve MediaPipe tabanlı video işleme yürütür.
- Python, hızlı prototipleme ve bilimsel hesaplamada avantaj sağlar. NumPy, SciPy ve diğer paketler ile entegre çalışır.

2.2 OpenCV Kullanımı
- Kamera verisi `cv2.VideoCapture()` üzerinden alınır.
- Her kare, MediaPipe Pose için BGR -> RGB dönüşümü ile ön işleme tabi tutulur.
- `cv2.imencode()` ile video karesi dışa aktarılır ve JPEG stream olarak sunulur.

2.3 Canlı Çerçeve Akışı
- `/video` uç noktası MJPEG formatında bir frame stream üretir.
- `generate_frames()` fonksiyonu, en son işlenmiş çerçeveyi alır ve tarayıcıya kesintisiz yayın sağlar.

---

## 3. Web (HTML, JS)

3.1 Flask Tabanlı Web Arayüzü
- `flask_server.py`, `@app.route` dekoratörleri ile hasta paneli, review sayfası ve API uç noktalarını sağlar.
- Şablonlar `templates/review.html` ve `templates/patient.html` üzerinden render edilir.

3.2 İstemci Tarafı Etkileşim
- JavaScript, onay formu gönderimlerini AJAX ile URL bazlı `/approve` isteklerine dönüştürür.
- Onay başarılı olduğunda satır DOM'dan silinir ve kullanıcıya anlık geri bildirim sağlanır.

3.3 Asenkron Veri Güncelleme
- `dashboard` uç noktası, doktor panelinin anlık hasta ve analiz metriklerini kendi client-side `fetch()` isteğiyle yenilemesine izin verir.
- Bu yapı, front-end ve back-end arasındaki ayrımı korur.

---

## 4. Database

4.1 SQLite Kullanımı
- `auth.db` kullanıcı kimlik doğrulaması için `users` tablosunu saklar.
- `gait.db` hasta bilgileri ve gait analiz sonuçları için `patients` ve `analyses` tablolarını içerir.

4.2 Veri Modeli
- `patients` tablosu hasta kimliği, ad, yaş ve cinsiyet bilgilerini içerir.
- `analyses` tablosu her analiz için adım sayısı, simetri, AI tahmini, doktor etiketleri ve tarih bilgilerini saklar.

4.3 Sorgu ve Performans
- `get_pending_reviews()` yalnızca `doctor_label IS NULL` olan kayıtları çeker. Bu, bekleyen onay kayıtları için performansı artırır.
- `get_analysis_by_id()` belirli bir analiz kaydını almak için kullanılır.

---

## 5. Canlı Analiz Sistemi

5.1 Analiz Akışı
- Canlı analiz, kamera görüntüsünü alır ve her karede MediaPipe Pose kullanarak anahtar noktaları çıkarır.
- Diz açısı, ayak pozisyonu ve vücut simetrisi gibi metrikler hesaplanır.
- Sonuçlar anlık olarak `pose_detect.classify_gait()` ile `NORMAL` veya `ABNORMAL` olarak sınıflandırılır.

5.2 Thread ve Durum Yönetimi
- `start_analysis` uç noktası, analiz işini ayrı bir `threading.Thread` içinde çalıştırır.
- `pose_detect.analysis_running` bayrağı, aynı anda birden fazla analiz başlatılmasını engeller.

5.3 Adım Tespiti ve Simetri
- Sol ve sağ ayak adımları ayrı ayrı sayılır.
- `symmetry` metriği, adım sayısı farkları ve yürüyüş dengesi üzerinden hesaplanır.

---

## 6. PDF Raporlama

6.1 Raporlama Amaçları
- Hastanın analiz sonuçlarını kalıcı biçimde belgelemek.
- Doktor onaylarını ve model tahminlerini PDF formatında dışa aktarmak.

6.2 ReportLab Kullanımı
- `generate_summary_pdf.py`, `generate_literature_review_pdf.py`, `generate_system_architecture_pdf.py` ve `generate_methodology_pdf.py` gibi scriptler PDF oluşturur.
- PDF sayfaları `letter` formatında hazırlanır ve metin blokları `textwrap` ile sığdırılır.

6.3 Dinamik İçerik
- Sistem, sadece sabit metin değil, veri tabanından çekilen analiz ve hasta bilgilerini de ilerleyen geliştirmelerde PDF'e yazabilir.
- Bu yaklaşım, klinik raporlamayı özelleştirmeyi destekler.

---

## 7. Login Sistemi

7.1 Kimlik Doğrulama
- `login()` fonksiyonu, kullanıcı adı ve şifreyi `users` tablosuna karşı doğrular.
- `werkzeug.security` kullanılarak şifreler hashlenir ve güvenli şekilde depolanır.

7.2 Oturum Yönetimi
- Flask `session` mekanizması, aktif kullanıcı ve rol bilgilerini tutar.
- `login_required` dekoratörü, korumalı sayfalara yalnızca girişli kullanıcıların erişmesini sağlar.

7.3 Yetkilendirme
- Mevcut yapı doktor rolünü yönetir. İleri geliştirmelerde farklı roller (hemşire, admin, hasta) eklenebilir.

---

## 8. Uygulama Katmanları ve Entegrasyon

8.1 Bağlantılar
- Kamera verisi Python/OpenCV katmanında işlenir.
- Sonuçlar web API aracılığıyla doktor paneline sunulur.
- Doktor onayı veritabanına kaydedilir; onay sonucu model eğitim/raporlama hattına eklenebilir.

8.2 API ve UI Mimarisi
- Veri işleme, Flask API katmanı ve HTML/JS istemci katmanına ayrılmıştır.
- Bu ayrım, bakım ve genişletilebilirlik için önemlidir.

8.3 Hata Yönetimi
- Veri tabanı işlemlerinde try/except blokları kullanılarak kritik hatalar izole edilir.
- AJAX onay akışında JSON yanıtlar döndürülerek istemci tarafı hata yakalama kolaylaştırılır.

---

## 9. Kapsam ve Gelecek Geliştirmeler

9.1 Mevcut Kapsam
- Gerçek zamanlı gait analizine yönelik bir prototip.
- Doktor onay akışı ve veri kaydı.
- Raporlama araçları ve canlı video akışı desteği.

9.2 Geliştirme Fırsatları
- PDF raporlarında hasta detayları ve grafikler.
- OpenPose entegrasyonu ve daha ileri derin öğrenme modelleri.
- Çoklu kullanıcı yönetimi ve rol tabanlı erişim.

---

## 10. Sonuç
Bu uygulama, görüntü işleme, web geliştirme ve veri tabanı entegrasyonunu bir arada kullanarak klinik yürüyüş analizini destekleyen bütünsel bir yazılım çözümü sunar. 8-10 sayfa rakamına ulaşmak için içeriğin her bölümü ayrıntılı şekilde açıklanmıştır.
