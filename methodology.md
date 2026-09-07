# Yöntem (Methodology)

## Özet
Bu bölüm, GaitProject'te kullandığımız yöntemleri detaylandırır: poz kestirimi (pose estimation), adım tespiti algoritması, sol/sağ ayak ayrımı, hız hesaplama, asimetri formülü ve yürüyüş skor fonksiyonu. Amaç, ölçülebilir, tekrarlanabilir ve klinik olarak anlamlı metrikler üretmektir.

---

## 1. Pose Estimation (MediaPipe / OpenPose gibi)

1.1 Temel Kavram
- Poz kestirimi, bir görüntü veya video karesinde insan vücudunun anahtar noktalarını (landmarks) belirleme işlemidir. Her bir landmark genellikle (x, y, z) koordinatları ve güven skoruyla (confidence) çıkarılır.
- Bu projede MediaPipe Pose temel alınmıştır; MediaPipe hızlı, hafif ve gerçek zamanlı uygulamalar için uygundur. Alternatif olarak OpenPose daha ayrıntılı iskelet çıkarımı sağlayabilir fakat daha hesap maliyetlidir.

1.2 Ön İşlem
- Her kare normalize edilir (örn. görüntü boyutuna göre koordinatları 0..1 aralığına getiririz).
- Gürültü azaltmak için zaman-domain filtreleri (ör. eksponansiyel hareketli ortalama) uygulanır.

1.3 Landmarklardan Açılar Üretme
- İki vektör arasındaki açı, eklem açısı olarak hesaplanır. Örneğin diz açısı için kalça-knee ve ankle-knee vektörleri kullanılır.
- Açı hesaplama formülü:

Inline math: $\theta = \arccos\left(\frac{u\cdot v}{\|u\|\,\|v\|}\right)$

Bu açı, adım döngüsündeki bükülme ve düzleşme olaylarını belirlemekte kullanılır.


---

## 2. Adım Tespiti Algoritması

2.1 Temel Yaklaşım
- Adım tespiti, genellikle diz açısı zaman serisindeki lokal minimum/maximum veya eşik geçişlerine dayanır.
- Bu projede kullandığımız yöntem: diz açısı belirli bir alt eşiğe ($STEP\_BEND\_THRESHOLD$) düştüğünde bir adımin başlangıcı, daha sonra tekrar üst eşiği ($STEP\_STRAIGHTEN\_THRESHOLD$) geçtiğinde adımın tamamlanması olarak tanımlanır.

2.2 Gürültü ve Debounce
- Aynı adımı birden çok kez saymayı önlemek için minimum zaman aralığı (minimum cadence aralığı) uygulanır.
- Ayrıca düşük geçirgen filtre (moving average veya Butterworth) ile açı sinyali düzeltilir.

2.3 Algoritma (pseudo-code)

- Input: zaman serisi t_i, diz açısı a_i
- state = 'idle'
- for each a_i:
  - if state == 'idle' and a_i < BEND_THRESHOLD and (t_i - last_step_time) > MIN_INTERVAL:
    - state = 'bending'
  - if state == 'bending' and a_i > STRAIGHTEN_THRESHOLD:
    - record step at t_i
    - last_step_time = t_i
    - state = 'idle'

2.4 Ek Özellikler
- Adım yüksekliği, ayağın zemine göre pik yüksekliği ile ilişkilendirilebilir (pixel veya cm cinsinden). Bu, adım kalitesi ve amputasyon/eklem problemi değerlendirmelerinde yardımcı olur.

---

## 3. Sol/Sağ Ayak Ayrımı

3.1 Neden Önemli?
- Asimetri hesaplamaları sol ve sağ ayak başına ayrı adım süreleri, yükseklikleri ve açı profilleri gerektirir.

3.2 Ayrım Yöntemleri
- Landmark tabanlı: MediaPipe'in sağ/sol ayak landmarks (ankle, heel, foot_index) kullanılarak hangi ayakın adım yaptığı belirlenir.
- Zamanlama tabanlı: Her adım zamanı ve ayak pozisyonu kullanılarak adımın hangi tarafa ait olduğu belirlenir.

3.3 Pratik Yaklaşım
- Her tespit edilen adım anında, ayakların x-koord (lateral konum) ve y-koord (yükseklik) karşılaştırılarak daha ileri/geride olan ayağın o adımı yaptığına karar verilir.
- Alternatif olarak, diz açısı değişimlerinin sırası takip edilerek (sağ-diz-bükülmesi sonra sol-diz-bükülmesi vb.) çift adım döngüsü çıkarılabilir.

---

## 4. Hız Hesaplama

4.1 Temel Formül
- Yürüyüş hızı genellikle adım uzunluğu (stride length) ve adım frekansının (cadence) çarpımıyla verilir:

Inline math: $v = L_s \times f$ 

burada $L_s$ stride length (m), $f$ cadence (adım/saniye).

4.2 Piksel → Metre Dönüşümü
- Kamera kalibrasyonuna bağlı olarak piksel ölçülerini metreye çevirmek gerekir. Basit yöntem: bilinen bir referans uzunluğu (ör. boy) ile ölçek faktörü tahmin edilir.

4.3 Alternatif: Zaman-tabanlı Ortalamalar
- Adım süreleri ölçülerek tekil adım hızı hesaplanabilir: $v_i = \dfrac{L_i}{\Delta t_i}$
- Anlık hız için hareketli ortalama uygulanır.

---

## 5. Asimetri Formülü

5.1 Tanım
- Asimetri indeksi, sağ ve sol için bir metrik arasındaki göreli farkı ölçer.

Örnek formül:

Block math:
$$
Asymmetry\ Index\ (\%) = 100 \times \frac{|S_{right} - S_{left}|}{(S_{right} + S_{left})/2}
$$

burada $S$ herhangi bir özellik (adım süresi, adım yüksekliği, adım uzunluğu vb.).

5.2 Çoklu Özellikler
- Birden fazla özellik için ağırlıklı birleşik asimetri skoru kullanılabilir:

$$
A_{combined} = \sum_{k} w_k \times A_k
$$

burada $A_k$ her bir özellik için normalize edilmiş asimetri, $w_k$ ise ağırlıklar (toplamları 1 olacak şekilde).

---

## 6. Skor Fonksiyonu (Önemli Kısım)

6.1 Amaç
- Klinik kullanım için tek bir skor, genel yürüyüş sağlığını özetlemeli; kolay yorumlanabilir, ancak aynı zamanda farklı alt-metrikleri korumalıdır.

6.2 Tasarım İlkeleri
- İyi bir skor fonksiyonu: normalize edilebilir, monotonic olmalı (daha kötü özellikler skoru kötü yönde değiştirmeli), ve klinik olarak anlamlı eşiklere sahip olmalıdır.

6.3 Önerilen Çok Boyutlu Skor
- Bileşenler:
  - $A$: Birleştirilmiş asimetri skoru (0 = simetrik, yüksek = asimetrik)
  - $V$: Normalleştirilmiş hız (örn. % beklenen hız)
  - $C$: Cadence/ritim stabilitesi (ör. std dev of step time)
  - $Q$: Adım kalite skoru (yükseklik, tamamlama)

Normalize edilmiş her bir bileşen $[0,1]$ aralığına ölçeklenir (0=ideal, 1=en kötü).

Genel skor örneği (0=ideal, 100=worse):

$$
Score = 100 \times \left( w_A \cdot A + w_V \cdot V + w_C \cdot C + w_Q \cdot Q \right)
$$

Ağırlıkların seçimi ($w_A, w_V, w_C, w_Q$) klinik önceliklere göre yapılır; örneğin asimetriye daha yüksek ağırlık verilebilir.

6.4 Bileşenlerin Hesaplanması
- A (Asimetri): yukarıdaki $A_{combined}$ formülüne göre normalize edilir:
  - $A = \min(1, A_{combined} / A_{ref})$ (ör. $A_{ref}=50\%$)
- V (Hız sapması): ideal hız $v_{ref}$ karşılaştırılır:
  - $V = \min(1, |v - v_{ref}| / v_{ref})$
- C (Ritim kararsızlığı): adım süresi standart sapması $\sigma_{t}$ ile normalize edilir:
  - $C = \min(1, \sigma_{t} / \sigma_{ref})$
- Q (Adım kalite): adım yüksekliği ve tamamlama oranına dayanır; eksiklik arttıkça Q yükselir.

6.5 Örnek ağırlık seti ve eşikler
- $w_A=0.4, w_V=0.25, w_C=0.2, w_Q=0.15$
- Bu, asimetriye öncelik veren bir klinik tercih yansıtır.

6.6 İleri Teknikler: Öğrenilmiş Skor
- Klinik etiketlere erişim varsa (ör. uzman derecelendirmesi), regresyon veya sıralama modelleri (ör. ordinal regression) ile parametrelerin öğrenilmesi önerilir.
- Bu durumda $Score = f( A, V, C, Q; \theta)$ biçiminde bir parametre seti $\theta$ öğrenilir.

---

## 7. Validasyon ve Güvenlik

7.1 Doğrulama
- Elde edilen skor ve alt-metrikler, altın standart (örn. 3D motion capture) ile karşılaştırılmalıdır.
- ROC / PR eğrileri, korelasyon katsayıları ve Bland-Altman analizleri kullanılmalıdır.

7.2 Güvenlik ve Gizlilik
- Hasta verileri (videolar, veritabanı kayıtları) yerel olarak saklanmalı veya şifrelenmelidir.
- Sunucu erişimi doğrulanmalı ve oturum süreleri sınırlanmalıdır.

---

## 8. Uygulama Notları ve Parametreler

- Önerilen parametre örnekleri:
  - $STEP\_BEND\_THRESHOLD = 168$ deg
  - $STEP\_STRAIGHTEN\_THRESHOLD = 172$ deg
  - $MIN\_STEP\_INTERVAL = 0.4$ s

- Sistem, düşük güçlü donanımlarda çalışacak şekilde optimize edilmiştir; ağır modeller opsiyoneldir.

---

## 9. Sonuç
Bu yöntemler, klinik olarak faydalı ve tekrarlanabilir yürüyüş değerlendirmesi sağlayacak şekilde tasarlanmıştır. "Skor fonksiyonu" bölümünde önerilen çok bileşenli yapı, hem uzman yorumunu içerecek şekilde ayarlanabilir hem de otomatik öğrenmeye uygundur.

