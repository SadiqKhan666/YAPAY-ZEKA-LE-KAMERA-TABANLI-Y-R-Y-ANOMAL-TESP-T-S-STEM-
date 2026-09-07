from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch

# PDF olustur
doc = SimpleDocTemplate("gait_analysis_report.pdf", pagesize=letter)
styles = getSampleStyleSheet()

# Baslik stili
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=16,
    spaceAfter=30,
)

# Normal metin stili
normal_style = styles['Normal']

# Icerik
story = []

# Baslik
story.append(Paragraph("Gait Analysis Sistemi Gelistirme Raporu", title_style))
story.append(Spacer(1, 12))

# Tarih ve bilgiler
story.append(Paragraph("<b>Tarih:</b> 15 Mayis 2026", normal_style))
story.append(Paragraph("<b>Sistem:</b> AI Destekli Yurume Analizi ve Doktor Onay Pipeline'i", normal_style))
story.append(Paragraph("<b>Gelistirici:</b> GitHub Copilot", normal_style))
story.append(Spacer(1, 12))

# 1. Giris
story.append(Paragraph("1. Giris", styles['Heading2']))
story.append(Paragraph("Bu rapor, gait (yurume) analizi sistemindeki son gelismeleri ozetlemektedir. Sistem, MediaPipe ve OpenCV kullanarak gercek zamani pose tespiti yapan bir AI tabanli yuruyus analizi uygulamasiadir. Son gelistirmelerle sistem, gelismis ozellik cikarimi, makine ogrenmesi entegrasyonu ve doktor onayli veri etiketleme pipeline'i ile guclendirilmistir.", normal_style))
story.append(Spacer(1, 12))

# 2. Sistem Mimarisi
story.append(Paragraph("2. Sistem Mimarisi", styles['Heading2']))
story.append(Paragraph("<b>Ana Bilesenler:</b>", normal_style))
story.append(Paragraph("- pose_detect.py: Cekirdek analiz motoru, ozellik cikarimi ve AI model egitimi", normal_style))
story.append(Paragraph("- flask_server.py: Web sunucusu, hasta yonetimi ve doktor onay arayuzu", normal_style))
story.append(Paragraph("- gait.db: SQLite veritabani, analiz kayitlari ve doktor etiketleri icin", normal_style))
story.append(Paragraph("- templates/review.html: Doktor onay paneli arayuzu", normal_style))
story.append(Spacer(1, 12))

# 3. Gelismis Ozellik Cikarimi
story.append(Paragraph("3. Gelismis Ozellik Cikarimi (pose_detect.py)", styles['Heading2']))

story.append(Paragraph("3.1 SignalFilter Sinifi", styles['Heading3']))
story.append(Paragraph("- <b>Amac:</b> Gurultu azaltma ve sinyal yumusatma", normal_style))
story.append(Paragraph("- <b>Ozellikler:</b> Savitzky-Golay filtresi, Hareketli ortalama, Medyan filtresi", normal_style))
story.append(Paragraph("- <b>Avantaj:</b> Daha stabil adim tespiti ve daha guvenilir metrikler", normal_style))

story.append(Paragraph("3.2 AdvancedGaitFeatures Sinifi", styles['Heading3']))
story.append(Paragraph("- <b>Amac:</b> Derin yuruyus analizi", normal_style))
story.append(Paragraph("- <b>Ozellikler:</b> Adim uzunlugu hesaplama, Yurume hizi analizi, Asimetri olcumu, Z-ekseni varyasyonu, Klinik skorlama sistemi", normal_style))

story.append(Paragraph("3.3 WindowedFeatureExtractor Sinifi", styles['Heading3']))
story.append(Paragraph("- <b>Amac:</b> Zaman penceresi tabanli ozellik cikarimi", normal_style))
story.append(Paragraph("- <b>Ozellikler:</b> Hareketli pencere analizi, Istatistiksel ozellikler (ortalama, standart sapma, egim), Frekans domain analizi", normal_style))
story.append(Paragraph("- <b>Avantaj:</b> Daha zengin ozellik vektoru icin model egitimi", normal_style))

story.append(Paragraph("3.4 HybridGaitClassifier Sinifi", styles['Heading3']))
story.append(Paragraph("- <b>Amac:</b> Kural tabanli + AI hibrit siniflandirma", normal_style))
story.append(Paragraph("- <b>Ozellikler:</b> Kural tabanli on siniflandirma, XGBoost tabanli AI model, Guven skoru hesaplama, Ozellik onemliligi analizi", normal_style))

story.append(Paragraph("3.5 AutoTrainingPipeline Sinifi", styles['Heading3']))
story.append(Paragraph("- <b>Amac:</b> Otomatik model guncelleme", normal_style))
story.append(Paragraph("- <b>Ozellikler:</b> Veri seti buyume takibi, Otomatik yeniden egitim tetikleme, Model performans izleme, Ozellik secimi optimizasyonu", normal_style))
story.append(Spacer(1, 12))

# 4. Doktor Onay Paneli
story.append(Paragraph("4. Doktor Onay Paneli (flask_server.py)", styles['Heading2']))
story.append(Paragraph("<b>Veritabani Sema Guncellemeleri:</b>", normal_style))
story.append(Paragraph("analyses tablosuna eklenen alanlar:", normal_style))
story.append(Paragraph("- ai_prediction: AI modelinin tahmini", normal_style))
story.append(Paragraph("- doctor_label: Doktor tarafindan onaylanan etiket", normal_style))
story.append(Paragraph("- avg_step_time: Ortalama adim suresi", normal_style))
story.append(Paragraph("- z_variation: Z-ekseni varyasyonu", normal_style))
story.append(Paragraph("- avg_asymmetry: Ortalama asimetri", normal_style))
story.append(Paragraph("- gait_speed: Yurume hizi", normal_style))

story.append(Paragraph("4.1 /review (GET)", styles['Heading3']))
story.append(Paragraph("- <b>Islev:</b> Onay bekleyen analiz kayitlarini listele", normal_style))
story.append(Paragraph("- <b>Donus:</b> Hasta bilgileri, AI tahminleri, guven skorlari", normal_style))

story.append(Paragraph("4.2 /approve (POST)", styles['Heading3']))
story.append(Paragraph("- <b>Islev:</b> Doktor etiketini kaydet ve dataset'e ekle", normal_style))
story.append(Paragraph("- <b>Parametreler:</b> Kayit ID, doktor etiketi", normal_style))
story.append(Paragraph("- <b>Yan Etki:</b> Dataset guncelleme ve model yeniden egitimi tetikleme", normal_style))

story.append(Paragraph("<b>Veri Akisi:</b>", normal_style))
story.append(Paragraph("1. AI analiz sonucu veritabanina kaydedilir (ai_prediction)", normal_style))
story.append(Paragraph("2. Doktor /review sayfasinda kayitlari inceler", normal_style))
story.append(Paragraph("3. Doktor etiketi secer ve onaylar", normal_style))
story.append(Paragraph("4. Onay sonrasi gercek etiket dataset'e eklenir", normal_style))
story.append(Paragraph("5. Yeterli veri biriktiğinde model otomatik yeniden egitilir", normal_style))
story.append(Spacer(1, 12))

# 5. Kullanici Arayuzu
story.append(Paragraph("5. Kullanici Arayuzu (templates/review.html)", styles['Heading2']))
story.append(Paragraph("<b>Ozellikler:</b>", normal_style))
story.append(Paragraph("- Tablo Gorunumu: Hasta, tarih, AI tahmin, guven skoru", normal_style))
story.append(Paragraph("- Durum Gostergeleri: Renk kodlu cip'ler (AI tahmin, beklemede, uyumsuzluk)", normal_style))
story.append(Paragraph("- Onay Formu: Dropdown ile etiket secimi", normal_style))
story.append(Paragraph("- Responsive Tasarim: Mobil uyumlu", normal_style))

story.append(Paragraph("<b>Etiket Secenekleri:</b>", normal_style))
story.append(Paragraph("- NORMAL: Normal yuruyus", normal_style))
story.append(Paragraph("- ABNORMAL: Genel anormallik", normal_style))
story.append(Paragraph("- PARKINSONS: Parkinson benzeri yuruyus", normal_style))
story.append(Paragraph("- IMBALANCE: Denge sorunu", normal_style))
story.append(Spacer(1, 12))

# 6. Teknik Detaylar
story.append(Paragraph("6. Teknik Detaylar", styles['Heading2']))
story.append(Paragraph("<b>Ozellik Vektoru:</b>", normal_style))
story.append(Paragraph("Model egitimi icin kullanilan 15+ ozellik:", normal_style))
story.append(Paragraph("- Temel metrikler: adim sayisi, sure, hiz", normal_style))
story.append(Paragraph("- Asimetri olcumleri: sol/sag karsilastirmasi", normal_style))
story.append(Paragraph("- Hareket analizi: z-varyasyonu, egim", normal_style))
story.append(Paragraph("- Pencere tabanli: istatistiksel ozellikler", normal_style))
story.append(Paragraph("- Klinik skorlar: agirlikli degerlendirme", normal_style))

story.append(Paragraph("<b>Model Egitimi:</b>", normal_style))
story.append(Paragraph("- Algoritma: XGBoost (gradient boosting)", normal_style))
story.append(Paragraph("- Ornek Esik: 20 onayli kayit sonrasi yeniden egitim", normal_style))
story.append(Paragraph("- Degerlendirme: Accuracy, precision, recall, F1-score", normal_style))
story.append(Paragraph("- Ozellik Onemliligi: Otomatik ozellik secimi", normal_style))

story.append(Paragraph("<b>Guvenlik ve Kalite:</b>", normal_style))
story.append(Paragraph("- Doktor onayli etiketleme", normal_style))
story.append(Paragraph("- AI tahminlerinin insan dogrulamasi", normal_style))
story.append(Paragraph("- Veri kalitesi kontrolu", normal_style))
story.append(Paragraph("- Otomatik model iyilestirme", normal_style))
story.append(Spacer(1, 12))

# 7. Sistem Akisi
story.append(Paragraph("7. Sistem Akisi", styles['Heading2']))
story.append(Paragraph("Video Giris → Pose Tespiti → Ozellik Cikarimi → AI Tahmin → DB Kaydet<br/>↓<br/>Doktor Inceleme → Etiket Onay → Dataset Guncelleme → Model Yeniden Egitim", normal_style))
story.append(Spacer(1, 12))

# 8. Sonuc ve Faydalar
story.append(Paragraph("8. Sonuc ve Faydalar", styles['Heading2']))
story.append(Paragraph("<b>Basarilar:</b>", normal_style))
story.append(Paragraph("- Gercek zamani yuruyus analizi", normal_style))
story.append(Paragraph("- Gelismis AI ozellik cikarimi", normal_style))
story.append(Paragraph("- Doktor onayli veri etiketleme", normal_style))
story.append(Paragraph("- Otomatik ogrenme pipeline'i", normal_style))
story.append(Paragraph("- Web tabanli doktor arayuzu", normal_style))

story.append(Paragraph("<b>Klinik Faydalar:</b>", normal_style))
story.append(Paragraph("- Daha dogru teshis destegi", normal_style))
story.append(Paragraph("- Doktor-AI isbirligi", normal_style))
story.append(Paragraph("- Surekli model iyilestirme", normal_style))
story.append(Paragraph("- Standartlastirilmis degerlendirme", normal_style))

story.append(Paragraph("<b>Teknik Faydalar:</b>", normal_style))
story.append(Paragraph("- Moduler mimari", normal_style))
story.append(Paragraph("- Olceklenir veri pipeline", normal_style))
story.append(Paragraph("- Kalite guvence mekanizmalari", normal_style))
story.append(Paragraph("- Otomatik optimizasyon", normal_style))

story.append(Paragraph("Sistem artik uretim seviyesinde bir AI destekli tibbi analiz araci olarak kullanilmaya hazirdir. Doktor onay dongusu ile model kalitesi surekli artacaktir.", normal_style))

# PDF olustur
doc.build(story)
print("PDF raporu olusturuldu: gait_analysis_report.pdf")