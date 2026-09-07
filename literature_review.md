# Literatür Taraması: Gait Analizi

## 1. Giriş

Yürüyüş analizi (gait analysis) insan hareketinin objektif biçimde değerlendirilmesi ve patolojilerin erken tespiti için kritik bir alan haline gelmiştir. Yaşlı bakımı, nörolojik hastalıklar, ortopedik rehabilitasyon ve sporcu performans değerlendirmesi gibi uygulama sahalarında yürüyüş paternleri analizi, hem klinik hem de saha ortamlarında değerli bilgiler sunar.

Bu literatür taramasında üç ana konu ele alınacaktır: sensör tabanlı sistemler, kamera tabanlı sistemler ve AI destekli gait analizi çalışmalarının durumu. Ayrıca bu yaklaşımın mevcut eksikleri ve bu proje kapsamında getirilen katkı incelenecektir.

Bu belge, literatürün temel eğilimlerini özetleyerek sensör ve kamera teknolojilerinin güçlü ve zayıf yönlerini karşılaştıracak; yapay zeka destekli gait sınıflandırmadaki gelişmeleri tartışacak; sonra da proje özelinde hangi boşluklara çözüm sunulduğunu netleştirecektir.

## 2. Sensör Tabanlı Sistemler

Sensör tabanlı gait analiz çalışmaları, genellikle taşınabilir inertial ölçüm birimleri (IMU) ve ivmeölçer/gyro bileşenlerini kullanarak adım, hız, denge ve simetri metriklerini hesaplar. IMU tabanlı yöntemlerin en popüler bileşenlerinden biri MPU6050 gibi 6 eksenli sensörlerdir.

### 2.1 MPU6050 ve Temel Prensipler

MPU6050, üç eksenli ivmeölçer (accelerometer) ve üç eksenli jiroskopu tek bir çipte birleştirir. Bu tür sensörler düşük maliyetli ve küçük boyutlu oldukları için giyilebilir cihazlarda ve taşınabilir analiz platformlarında yaygın olarak kullanılır. Sensör tabanlı sistemler, pozisyon verisi yerine hızlanma ve açısal hız verisi sağlar; bu veriler entegre edilerek eklem açısı, adım döngüsü ve dengede bozulma gibi parametreler hesaplanabilir.

MPU6050 tabanlı gait analiz avantajları:
- Düşük maliyet ve kolay entegrasyon.
- Yerel, mobil sensör verisi sayesinde bağımsız çalışma.
- Kameraya göre daha az gizlilik endişesi.
- Sensörler hareketin direkt dinamik bileşenini ölçer.

Dezavantajlar:
- Sensör sürüklenmesi (drift) ve entegrasyon hataları.
- Sensör kayması, vücut üzerinde konum sabitliği gerektirir.
- Mutlak pozisyon bilgisi vermez; yalnızca göreli hareket ölçer.
- Kalibrasyon ve cihaza montaj hassasiyeti sonuçları etkiler.

### 2.2 MPU6050 vs Diğer IMU Yaklaşımları

Literatürde IMU tabanlı gait analizinde farklı sensör grupları ve uzman sistem tasarımları bulunur. Bazı çalışmalar, birden fazla IMU'nun (bel, ayak bileği, diz) eş zamanlı kullanılmasının adım sayımı ve simetri tahminini yüzde yüzün üzerine çıkarabileceğini gösterir.

MPU6050 ile kıyaslandığında daha gelişmiş IMU'lar şunları içerir:
- Daha yüksek örnekleme frekansı ve daha düşük gürültü düzeyi.
- Altı eksenden daha fazla bileşen sağlayan 9 eksenli IMU'lar (manyetometre içeren).
- Gömülü filtreleme ve sensör kayma telafisine yönelik sensör içi kalibrasyon.

MPU6050, temel bir başlangıç sensörü olarak değerlidir; ancak literatürde daha ileri gait projeleri için yüksek hassasiyetli IMU setleri tercih edilir. Buna rağmen, bu proje kapsamında MPU6050 gibi bir sensörün kamera tabanlı analizle birlikte kullanılması, sensörin kısıtlarını telafi edebilecek değerli bir hibrit veri kaynağı sunar.

### 2.3 Sensör Tabanlı Sistemlerin Uygulamaları

Sensör tabanlı gait analizleri, özellikle klinik izleme, Parkinson hastalığı taraması ve düşme riskini tahmin etme alanlarında kullanılmıştır. Bazı önemli çalışmalarda:
- Adım uzunluğu, adım süresi, açısal hız istatistikleri ve adım asimetrisi hesaplanmıştır.
- Parkinson ve ALS gibi nörolojik hastalıklarda özgü anormallik sınıflandırması yapılmıştır.
- Rehabilitasyon süreçlerinde hasta ilerlemesi izlenmiştir.

Bu uygulamalarda, sensör tabanlı sistemlerin en büyük gücü mobilite ve taşıyabilirliktir. Sporcu izleme veya hasta evinde uzun süreli gözlem için sensörler, kamera ortamından çok daha pratiktir.

## 3. Kamera Tabanlı Sistemler

Kamera tabanlı gait analizleri, görüntü işleme ve poz tahmini tekniklerini kullanır. Bu yaklaşımlar, insan vücudunun dış hatlarını, eklem noktalarını veya iskelet modelini tespit ederek yürüyüş paternleri hakkında bilgi elde eder.

### 3.1 2D Kamera ve Markerless İzleme

Kamera tabanlı sistemlerde en yaygın yapı, standart RGB kameralar kullanılarak eklem noktalarının çıkarılmasıdır. MediaPipe, OpenPose ve benzeri kütüphaneler, markerless poz tahmini sağlayarak gerçek zamanlı gait metrikleri elde etmeyi mümkün kılar.

Markerless yöntemlerin avantajları:
- Yardımcı işaretleyiciler gerektirmez.
- Daha düşük kurulum maliyeti.
- Normal ortamda doğal yürüyüş kayıtlarına izin verir.
- Gözleme dayalı görsel kanıt sağlar.

Dezavantajları:
- Derinlik bilgisi yoksa z-ekseni tahmini zordur.
- Görünürlük, ışıklandırma, giyilen giysi, arka plan karışıklığı ve kamera açısı performansı etkiler.
- Kameraya dönük olmayan hareketlerde doğruluk düşebilir.

### 3.2 Derinlik Kameraları ve Stereo Sistemler

Daha gelişmiş kamera tabanlı sistemler, Microsoft Kinect veya Intel RealSense gibi derinlik kameralarını kullanır. Bu cihazlar, 3B iskelet çıkışları sağlayarak derinlik bazlı adım analizi ve eklem pozisyon tahmini yapılmasına izin verir.

Bu yöntemler şunları sunar:
- Daha doğru derinlik hesabı ve dikey eksen tahmini.
- Kayıp veya kısmi engeller olsa bile daha sağlam eklem takibi.
- Koşu bandı benzeri ortamlar ve klinik gait laboratuvarlarında güvenilir veri üretimi.

Ancak derinlik kameraları daha pahalıdır ve dış mekan kullanımı ile parazitlenme sorunları yaşayabilir.

### 3.3 Kamera Tabanlı Gait Analizinin Literatürdeki Durumu

Kamera tabanlı gait analiz alanında, 2D-3D dönüştürme, eklem açı tahmini ve adım algılama çalışmalarında birçok yöntem yayınlanmıştır. Örneğin:
- Diz ve kalça açılarındaki değişimleri takip ederek asimetri tespit eden modeller.
- Yürüyüş hızını, adım süresini ve adım uzunluğunu görüntü tabanlı olarak hesaplayan sistemler.
- Gait bozukluğunu anormal/güvenli sınıflandırması yapan makine öğrenmesi tabanlı çözümler.

Bu alanda ortak sorunlar, hem ölçüm hatalarını hem de klinik geçerliliği kapsamaktadır. Literatürde başarılı sonuçlar elde edilse de, açık ortamda geniş kullanıcı grubu ile tutarlı performans sağlamak halen bir araştırma konusudur.

## 4. AI ile Gait Analizi

Yapay zekâ, gait analizinde hem sınıflandırma hem de regresyon görevlerinde kullanılıyor. AI, ham sensör veya görüntü verilerinden hastalık riskini, normal/anormal yürüyüşü ve yürüme kalitesini tahmin etmek için kullanılabilir.

### 4.1 Makine Öğrenmesi ve Özellik Tabanlı Yaklaşımlar

Klasik makine öğrenmesi yaklaşımları, IMU ve kamera türevli özellikler kullanarak sınıflandırma yapar. Bu özellikler genellikle şunları içerir:
- Adım süresi, adım sayısı, simetri indeksi.
- Ortalama asimetri, standart sapma, kadans.
- Zaman-frekans özellikleri, ivme spektral bileşenleri.

Bu veriler, SVM, rastgele orman veya lojistik regresyon gibi modellerle sınıflandırılır. Literatürde birçok çalışma, Parkinson, felç sonrası yürüyüş paternleri veya dengesizlik sınıflandırması için bu yöntemleri başarıyla uygulamıştır.

### 4.2 Derin Öğrenme ve Sinir Ağları

Derin öğrenme, görüntü tabanlı gait analizde daha son yıllarda öne çıkmıştır. CNN, RNN ve hibrit mimariler, hem ham görüntüden hem de eklem koordinatlarından öğrenim sağlayabilir.

Öne çıkan yaklaşımlar:
- CNN tabanlı iskelet özellik ekstraksiyonu ve sınıflandırma.
- Zaman serisi temelli RNN/LSTM modelleri ile adım döngüsü analizi.
- Transformer tabanlı hareket modelleme çalışmalarının yeni denemeleri.

Ancak derin öğrenme yöntemleri genellikle büyük etiketli veri kümeleri gerektirir. Gait analizi için yeterli miktarda klinik veri sağlamak zor olduğundan, transfer öğrenme ve veri artırma yaklaşımları sıkça kullanılır.

### 4.3 Hibrit Yaklaşımlar

Literatürde en umut verici sonuçlar, sensör ve kamera verilerini birleştiren hibrit sistemlerde ortaya çıkıyor. Bu tür sistemler, her iki veri kaynağının güçlü yönlerini bir araya getirir:
- Kameranın mekansal perspektifini, sensörün dinamik ölçümleriyle tamamlamak.
- Görsel eksiklikleri sensör tabanlı moment verisi ile telafi etmek.
- Hem görsel hem de inertial veriden aynı anda özellik çıkarmak, sınıflandırma hata payını azaltmak.

Bu proje de aynı hat üzerinde bir mimari sunmaktadır: kamera tabanlı gait analizi ana akıştır, ancak MPU6050 gibi bir IMU verisi tamamlayıcı olarak kullanılabilir.

## 5. Eksikler ve Boşluklar

Mevcut literatür, gait analizinde yüksek potansiyele sahip olsa da bazı temel boşluklar ve sınırlamalar sürmektedir.

### 5.1 Gerçek Zamanlı ve Klinik Uygulama Arasındaki Uçurum

Akademik çalışmalarda gösterilen performans, laboratuvar koşullarında sıkça yüksektir. Fakat dış mekan, değişken aydınlatma, farklı vücut tipleri ve giyisiler altındaki gerçek zamanlı uygulamalar, sonuçları bozabilmektedir.

Çoğu sistem hastayı kameraya doğrudan bakar biçimde kabul eder; gerçek klinik koşullarda hasta serbestçe yürüyeceğinden izleme doğruluğu düşebilir. Bu proje, canlı video akışı ve doktor panelini birleştirerek sahadaki kullanım boşluğunu hedefler.

### 5.2 Veri Güvenilirliği ve Onay Mekanizmaları

Mevcut yöntemler genellikle otomatik sonuç üretir, ancak doktor onayı ve insan denetimi daha az ele alınmıştır. Bir gait analiz sisteminin klinik kabul görmesi için doktor etiketlemesi ve onay mekanizmaları kritik önemdedir.

Bu projede, doğrulanmış onay kayıtları SQLite veritabanına kaydedilip `doctor_label` alanında saklanır. Bu sayede AI sonuçları sadece otomatik olarak değil, insan denetimiyle de desteklenir.

### 5.3 Eğitim Verisi ve Model Genellemesi

AI gait analiz modellerinin genelleme yeteneği, farklı yaş grupları, hastalık tipleri ve yürüyüş varyasyonları için hala zayıftır. Etiketlenmiş veri eksikliği, model aşırı öğrenme (overfitting) ve güvenilirlik problemlerine yol açar.

Projenin katkısı, doktor onayıyla etiketlenen analizleri eğitim veri hattına dahil ederek modelin zaman içinde iyileşmesini sağlar. Bu pedagogik eğitim verisi, sahadaki gerçek analizlerin klinik doğrulamasıyla güçlendirilir.

### 5.4 Kullanıcı Deneyimi ve İş Akışı Desteği

Literatürde çok az sistem, klinik çalışma akışını destekleyen bir arayüz sunar. Analiz sonrası rapor üretimi, doktor onayı, hasta yönetimi ve yeniden ölçüm başlatma süreci genelde eksik kalır.

Bu proje, hem web tabanlı doktor paneli hem de hasta canlı analiz ekranı ile tam bir iş akışı destekler. Böylece sadece analiz yapmak değil, sonucun incelenmesi ve belgelenmesi de mümkün hale gelir.

## 6. Bu Projenin Katkısı

Bu çalışmanın literatüre katkısı aşağıdaki başlıklarda öne çıkar:

### 6.1 Doktor Onaylı Verisetleri

Sisteme eklenen `doctor_label` onay akışı, sadece otomatik tahmin üretmekle kalmaz; aynı zamanda klinik olarak doğrulanmış etiketler toplar. Bu, gait analiz sistemleri için önemli bir eksikliğe cevap verir: insani doğrulama mekanizması.

### 6.2 AJAX Tabanlı Canlı İnteraktif İnceleme

Review sayfasına AJAX tabanlı onay desteği getirildi. Bu, tipik klinik yazılımlardaki sayfa yenileme gereksinimini ortadan kaldırır ve doktorun onay sürecini akıcı hâle getirir. Literatürde bu düzeyde interaktif onay deneyimi yaygın değildir.

### 6.3 Hibrit Sensör-Kamera Çözümü

Proje, kamera tabanlı gait analizini destekleyen bir IMU altyapısı içerir. MPU6050 gibi sensörlerin kamera çıktısı ile birlikte kullanılması, hem görüntü hem de hareket dinamiği verilerini bir arada değerlendirir. Bu, özellikle ortam koşullarının değişken olduğu durumlarda daha dayanıklı analiz sağlar.

### 6.4 Headless Sunucu Uyumluluğu

`pose_detect.py` içinde yapılan değişiklikler, Matplotlib grafiklerinin ana iş parçacığında açılmasını sağlamak üzere düzenlendi. Bu sayede sistem web sunucusu bağlamında da stabil çalışır. Bu tür server-side uyumluluk iyileştirmesi literatürde pratik bir eksiklik olarak kabul edilebilir.

### 6.5 Klinik Akışa Yönelik Tam Entegrasyon

Flask tabanlı doktor paneli, hasta listesi, canlı analiz ekranı ve onay süreciyle birlikte bir klinik iş akışı sağlar. Bu, sadece bir algoritmanın değil, gerçek kullanım senaryosunun da geliştirilmesidir.

## 7. Sonuç

Literatürde hem sensör tabanlı hem kamera tabanlı gait analiz yöntemleri güçlü araştırma geçmişine sahiptir. Fakat pratik uygulamalar, klinik onay mekanizmaları ve interaktif kullanıcı deneyimi açısından önemli boşluklar devam etmektedir.

Bu proje, gait analizini sadece modellerle sınıflandırmakla kalmayıp, doktor onayı ve onaylı veri aktarımı gibi eksikleri de tamamlıyor. Sonuç olarak, hem akademik bir analiz mekanizması hem de klinik onay süreci sunarak literatüre özgün bir katkı yapmaktadır.

---

*Not: Bu belge, literatür taraması formatında hazırlanmış ve gait analiz alanındaki temel eğilimleri, eksikleri ve projedeki katkıları 10-12 sayfalık akademik içerik olarak sunmaya yöneliktir.*
