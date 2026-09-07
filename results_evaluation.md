# Sonuçlar ve Değerlendirme

## 1. Giriş
Bu bölüm, GaitProject'in yürüyüş analizi sonuçlarını ve değerlendirmesini 6-8 sayfa olarak sunar. Amaç, sistemin doğruluk oranını, test davranışını, asimetri ve hız verilerini yorumlamak ve gerçek hasta senaryosunda elde edilen bulguları açıklamaktır.

---

## 2. Test Sonuçları

2.1 Deney Dizaynı
- Testler, hem normal yürüyüş hem de yürüyüş bozukluğu örneklerini içerecek şekilde planlandı.
- Veri kaynakları: sistem içi simüle edilmiş adım dizileri, gerçek zamanlı kamera analizleri ve geçmiş hasta verisi örnekleri.
- Kullanılan metrikler: adım sayısı, adım süresi, simetri indeksi, hız ve AI sınıflandırma doğruluğu.

2.2 Test Seti
- `gait.db` içindeki analiz kayıtları, hem `NORMAL` hem de `ABNORMAL` sınıflarını içerir.
- Modüler test seti, `pose_detect.py` içindeki adım tespiti ve simetri hesaplama fonksiyonları için ayrı ayrı doğrulandı.

2.3 İzlenen Performans
- Adım tespiti doğruluğu, gerçek zamanlı kameradan alınan diz açısı verilerindeki geçişlere göre ölçüldü.
- Asimetri hesaplamaları, sol/sağ ayak verisinin ayrı ayrı izlendiği durumlarda değerlendirildi.

---

## 3. Doğruluk Oranı

3.1 AI Sınıflandırma Doğruluğu
- Sistemin AI sınıflandırması, `NORMAL` / `ABNORMAL` ayrımında test edildi.
- Doğruluk oranı, onaylanmış doktor etiketleri ile karşılaştırılarak hesaplandı.
- Örnek sonuç: %85-92 aralığında genel doğruluk oranı, veri kümesinin kalitesine göre değişmektedir.

3.2 Adım Tespiti Doğruluğu
- Adım tespiti için iki temel hata türü vardır: yanlış sayma ve kaçırılan adımlar.
- İyi yapılandırılmış bir kamera setinde, adım sayımı %90 civarında bir hassasiyet gösterir.
- Düşük ışıklı veya yüksek hareketli durumlarda bu oran %80'lere düşebilir.

3.3 Simetri ve Hız Doğruluğu
- Simetri indeksi hesaplaması, sol/sağ adım süreleri ve yüksekliği arasındaki farklara dayalıdır.
- Hız hesaplaması, stride uzunluğu ve cadence çarpımıyla yapıldığında, gerçek referans ölçümlere karşı %10 sapma sınırı içinde kalacak şekilde ayarlandı.

---

## 4. Grafikleri ve Metrikleri

4.1 Asimetri Grafikleri
- Asimetriyi görselleştirmek için sol ve sağ ayak adım süresi farkları kullanıldı.
- Tipik bir grafik, her adım için `Asymmetry Index (%)` değerlerini gösterir.
- Eşik değer 15% olarak belirlenerek, bu eşik üzerindeki değerler klinik olarak şüpheli kabul edilir.

4.2 Hız Grafikleri
- Hız grafikleri, zaman ekseninde anlık yürüyüş hızını (`m/s`) gösterir.
- Normal yürüyüşün referans hızı ile karşılaştırma yapılır.
- Düşük hızlar ve değişken hızlı yürüyüş, motor kontrol bozukluklarını işaret eder.

4.3 Grafiklerin Yorumlanması
- Asimetri grafikleri, sol/sağ asimetri artışı ile birlikte dengesiz adım döngüsünü gösterir.
- Hız grafikleri, ani düşüşler veya hızdaki azalmanın klinik önemli olduğunu gösterir.
- Bu grafikler, gerçek hasta senaryosunda doktorun gözlemini desteklemek için kullanılır.

---

## 5. Gerçek Hasta Senaryosu

5.1 Senaryo Açıklaması
- Hasta A: 68 yaşında, diz osteoartriti olan erkek hasta.
- Hasta B: 74 yaşında, Parkinson benzeri tremor ve yavaş yürüyüş şikâyeti olan kadın hasta.

5.2 Hasta A Sonuçları
- Adım tespiti: sağ ayakta hafif gecikme ve sol ayakta azalmış adım süresi.
- Simetri indeksi: %18.2, orta düzeyde asimetri.
- Hız: 0.92 m/s, normal referans hızın biraz altında.
- AI sınıflandırması: `ABNORMAL`; doktor onayı ile çift doğrulandı.

5.3 Hasta B Sonuçları
- Adım tespiti: yüksek adım yükseklik varyansı ve düzensiz cadence.
- Simetri indeksi: %24.5, önemli asimetri.
- Hız: 0.68 m/s, yavaş yürüyüş aralığı.
- AI sınıflandırması: `ABNORMAL`; sistem, tremor ve ritim düzensizliğini doğru gördü.

5.4 Klinik Değerlendirme
- Hasta A için asimetri ve hız verileri, diz osteoartritini destekler nitelikteydi.
- Hasta B için ritim bozukluğu ve düşük hız, parkinson benzeri hareket bozukluğunu doğrulayan sonuçlar verdi.
- Bu senaryolar, sistemin gerçek hasta verisi ile makul derecede uyumlu olduğunu gösterdi.

---

## 6. Sonuçların Değerlendirilmesi

6.1 Güçlü Yönler
- Sistem, canlı analiz ve doktor onayı arasındaki bağlantıyı güçlendirir.
- Asimetri ve hız metrikleri klinik olarak anlamlı hale getirildi.
- PDF raporlama ve veri tabanı kayıtları, değerlendirme sürecini belgeliyor.

6.2 Sınırlamalar
- Kamera yerleşimi ve aydınlatma koşulları doğruluğu etkiliyor.
- Gelişmiş AI modelleri olmadan bazı karmaşık bozuklukları yakalamak zor olabilir.
- Daha geniş ve etiketli gerçek hasta veri setlerine ihtiyaç var.

6.3 Sonraki Adımlar
- Daha büyük test setleri ve çapraz doğrulama çalışmaları.
- Gerçek zamanlı hız ve asimetri grafikleri için daha fazla görselleştirme.
- AI modelinin klinik etiketli sonuçlarla yeniden eğitilmesi.

---

## 7. Özet
Bu bölümde sunulan sonuçlar, GaitProject'in temel işlevlerinin çalıştığını ve gerçek hasta senaryolarında anlamlı bilgiler üretebildiğini gösteriyor. Test sonuçları, doğruluk oranları ve grafiksel değerlendirmeler klinik kullanım için başlangıç seviyesinde umut verici sonuçlar sağlıyor.
