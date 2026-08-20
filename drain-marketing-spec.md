# Drain Marketing & Growth Spec (MVP)

Bu doküman, Drain ürününün pazarlama ve büyüme açısından aldığı stratejik kararları ve bunlara bağlı ürün/geliştirme gereksinimlerini özetler. Amaç, geliştirici ekibin **marketing ile uyumlu bir ürün deneyimi** inşa etmesini sağlamaktır.

---

## 1. Ürün Pozisyonu

**Marka adı:** Drain  
**Domain:** `drainmind.com`  
**Kategori:** Mesleki Almanca (Fachsprache) için kişiselleştirilmiş okuma/konuşma koçu.

**Pozisyonlama:**

- Geleneksel dil öğrenme uygulaması **DEĞİL**.
- Bilimsel temeli:
  - Stephen Krashen – *Comprehensible Input*
  - Paul Nation – *%95 bilinen / %5 bilinmeyen kelime oranı*
- Kullanıcıya satılan şey:
  - “Kelime ezberi” değil, **anlaşılır ve optimize edilmiş girdiyle daha hızlı öğrenme**.
  - Dijital bir “Kelime Beyni” (knowledge graph) inşa etme ve bunu istediği zaman export edebilme.

---

## 2. Hedef Kitle (ICP)

**Öncelikli ICP (MVP): Sağlık Personeli – Pflege**

- Almanya’da çalışan / çalışmak isteyen:
  - Hemşireler (Pflegekräfte)
  - Klinik/yaşlı bakım merkezi personeli
- Zorunlu ihtiyaç:
  - Fachsprachenprüfung (B2/C1 Pflege dil sınavı) geçmek.
- Ödeme motivasyonu:
  - Sınavı geçmeden işe başlayamıyor / Approbation alamıyor.
  - *“Dil öğrenmek”* için değil, *“sınavı geçmek ve işe başlamak”* için para veriyor.

**Sekonder ICP (daha sonra):**

- IT profesyonelleri (C1 iş Almancası, iş görüşmesi, terfi hedefi).
- Şimdilik ürün ve mesajlaşma sadece Pflege odaklı tasarlanacak.

---

## 3. Brand & Naming

- **Ana marka:** Drain
- **Domain:** `drainmind.com` (kullanıcıya iletişimde sadece “Drain” kullanılacak).
- Logo:
  - Üstte huni/damla formu (dil girdisi → süzme).
  - Altta 3–4 sinaps/nöron düğümü (dijital kelime beyni).
  - Monoline, tek renk (deep teal), minimalist.

---

## 4. Değer Önerisi ve Tagline'lar

**Ana değer önerisi:**

> Kullanıcının seviyesini ve kelime hakimiyetini takip ederek, her gün sadece onun anlayabileceği ve gelişmesine gerçekten katkı sağlayan Almanca metin/diyaloglar üretir.  
> Böylece sınav ve iş hedeflerine daha kısa sürede ulaşmasını sağlar.

**Tagline seti (kullanım alanına göre):**

- Kullanıcı odaklı (landing hero / app):
  - **“Drain — Meaningful input for faster learning.”**
- Bilimsel/teorik (about / investor deck / teknik sayfa):
  - **“Drain — Personalized comprehensible input.”**

Kural:  
Landing page ve app içinde birincisi ön planda; “About” veya yatırımcı sunumlarında ikincisi kullanılacak.

---

## 5. Funnel & UX Gereksinimleri

Bu bölüm, marketing stratejisini destekleyen **ürün içi akışları** tanımlar.

### 5.1. Landing Page

**Amaç:**  
Pflege hedef kitlesine tek cümlede net bir vaat:  
> “Fachsprachenprüfung’u ezbere değil, kişisel anlamlı girdiyle daha hızlı geç.”

**Geliştirici gereksinimi:**

- Tek sayfalık landing:
  - Hero:
    - Logo + “Drain”
    - Tagline: “Meaningful input for faster learning.”
    - Tek CTA: “7 gün ücretsiz dene” (trial flow’a götürür).
  - Problem bölümü:
    - “Kelime ezberi işe yaramıyor / sınavda akılda kalmıyor” anlatımı.
  - Nasıl çalışır bölümü:
    - %95 bilinen / %5 yeni kelime mantığı basit bir görselle.
    - “Dil motoru seni tanıdıkça metinler sana göre ayarlanır.”
  - Dijital Beyin (Obsidian/Markdown export) bölümü:
    - Kelime grafından export’a giden basit bir görsel.
    - “Öğrendiğin dil bir uygulamada hapis değil; sana ait bir dijital beyin olarak kalır.” mesajı.

### 5.2. Lead Magnet & Email Capture (Opsiyonel ama marketing için önemli)

- Basit bir form:
  - “Fachsprachenprüfung için en kritik 300 Pflege kelimesi + 20 örnek diyalog PDF”
  - e-mail alanı + onay.
- Geliştirici:
  - Supabase veya benzeri DB’de `leads` tablosu (email, segment, created_at).
  - Bu form, drainmind.com üzerinde ayrı bir sekme veya section olabilir.

### 5.3. Signup & Pricing (MVP)

**MVP fiyatlandırma (marketing kararı):**

- Free/trial:
  - 7 gün boyunca günde sınırlı metin/diyalog (örneğin 1–3).
- Paid:
  - **Exam package önerisi (gelecek aşama):** 3 aylık tek ödeme (örneğin 99€).
  - MVP’de basit bir aylık plan da olabilir (örneğin 29€/ay).

**Geliştirici gereksinimi:**

- Kullanıcı modeli:
  - `plan` (free, trial, paid)
  - `trial_start`, `trial_end`
  - `subscription_status`
- Flow:
  - Landing CTA → signup → trial start.
  - Trial bitiminde in-app ve e-mail “paket seç” ekranı.

---

## 6. In-App Marketing Özellikleri (Product-Led Growth)

Marketing stratejisi, ürünün kendisini **koç ve motivasyon aracı** olarak kullanıyor. Geliştiricinin implement etmesi gereken kritik davranışlar:

### 6.1. Onboarding – Seviye ve Kalibrasyon

**Problem:**  
Kullanıcının B1/B2/C1 sertifikası, tüm kelimeleri bildiği anlamına gelmiyor. Onboarding’de yanlış seviye → churn.

**Karar:**

- Kullanıcı beyan seviyesini (örneğin “B2 Pflege”) girer.
- Ardından **3 kalibrasyon metni** gösterilir:
  1. Beyan edilen seviyenin **bir alt seviyesi**.
  2. Aynı seviye, kelimelerin mastery başlangıcı **0.55** kabul edilerek.
  3. Aynı seviye, kelimelerin mastery başlangıcı **0.75** kabul edilerek.

- Kullanıcı her metni 1–5 yıldız ile puanlar.
- Ek giriş:
  - “Bu metin sana çok kolay / tam kıvamında / çok zor geldi mi?” (3 seçenek)
- Sistem bu üç metinden sonra **başlangıç mastery bandını** otomatik seçer.

**Geliştirici için:**

- Model düzeyinde:
  - `declared_level`
  - `mastery_score` (0.0–1.0)
  - `confidence_score` (prior güveni)
- Onboarding flow:
  - Seviye formu → 3 metin gösterimi → rating ve zorluk geri bildirimi → başlangıç ayarı.

### 6.2. Rating & Mastery Update

Her metnin sonunda:

- 1–5 yıldız rating.
- Opsiyonel zorluk seçimi (“kolay / tam kıvam / zor”).

**Karar:**

- 1–2 yıldız → ilgili kelimelerde negatif güncelleme.
- 3 yıldız → nötr.
- 4–5 yıldız + “tam kıvam” → en güçlü pozitif update.
- “Çok kolay” → mastery artışı sınırlı (zaten bilineni tekrar etmeyi engelle).
- “Çok zor” → ilgili kelimeler bir süre geri çekilsin, daha fazla anchor gerekli.

**Geliştirici:**

- Kelime bazlı:
  - `mastery_score` update fonksiyonu.
  - `evidence_count` (kelime kaç metinde görüldü).
- Metin bazlı:
  - rating loglanmalı (analytics için).

### 6.3. Dijital Beyin (Obsidian/Markdown Export)

**Marketing kararı:**  
Bu özellik kullanıcıya “dil seviyesi bana ait, platforma hapis değil” güveni veriyor → lock-in.

**Geliştirici gereksinimi:**

- Her kullanıcı için:
  - Kelime grafı (nodes: kelimeler, edges: ilişkiler).
  - Mastery ve örnek cümleler.

- Export formatı:
  - `.md` dosyaları:
    - Her kelime için ayrı bir Markdown dosyası (örnek cümleler, mastery, tags).
    - Aralarındaki ilişki için `[[wikilinks]]` yapısı.
  - `.zip` içinde paketlenmiş Vault.

- UI:
  - Ayarlar / profil kısmında “Kelime beynini indir (.zip)” butonu.

### 6.4. Gamification (Bilimle uyumlu)

Marketing kararı:  
Gamification olacak, ama **oyunu değil öğrenmeyi optimize edecek**.

**Geliştirici gereksinimi:**

- Streak:
  - Günlük en az 1 anlamlı metin/diyalog tamamlayana streak.
  - “Streak freeze” (örneğin haftada 1 gün affedici mekanizma).
- Görsel graf:
  - Kullanıcının kelime beyni basit bir node-link diagramı olarak gösterilebilir.
  - Haftalık “Beynin bu hafta X yeni bağlantı büyüttü” kartı (paylaşılabilir).
- %95/%5 göstergesi:
  - Her metnin başında/sonunda:
    - “Bugün X yeni kelime, Y tanıdık kelime gördün.” şeklinde rozet.

---

## 7. B2B / Enterprise Hazırlığı (MVP + Sonrası)

Marketing hedefi:  
Uzun vadeli gelir için klinikler ve işe alım ajansları üzerinden B2B.

**Geliştirici için gereksinim:**

- Kurumsal müşteri modeli:
  - `organization` tablosu (clinic/agency).
  - `candidate` tablosu (organization’a bağlı kullanıcılar).
- Admin/HR paneli:
  - Aday bazlı ilerleme raporu:
    - Aktif gün sayısı.
    - Kelime mastery gelişimi.
    - Simüle sınav performansı (ileride).

Bu, MVP’de tamamen hazır olmak zorunda değil; ama veri modeli düzeyinde hazırlık yapılması, marketing tarafı için kritik.

---

## 8. Analytics & Ölçüm

Marketing, ürün içi veriye dayanacak. Geliştiricinin event bazlı logging kurması gerekiyor.

**Minimum event set:**

- `landing_view` (kaynak: organik, ads, vs.)
- `signup_started`, `signup_completed`
- `trial_started`, `trial_converted_to_paid`
- `onboarding_completed` (3 metin + rating bitmiş)
- `content_generated` (metin/diyalog)
- `content_completed` (sonuna kadar okundu/oynatıldı)
- `rating_submitted` (1–5 + zorluk)
- `streak_day_completed`
- `export_downloaded` (Obsidian/dijital beyin zip)

Bu event’ler Supabase veya ayrı bir analytics sistemiyle toplanabilir.

---

## 9. Roadmap Öncelikleri (Developer için sıralama)

1. **Core onboarding + kalibrasyon flow** (seviye → 3 metin → rating → mastery başlangıcı).
2. **Rating → mastery güncelleme fonksiyonu** (MVP basit ama çalışır).
3. **Dijital beyin export (Markdown + zip)**.
4. **Streak + basit graf/gamification ekranı**.
5. **Landing page (hero, explain, CTA) + trial flow**.
6. **Analytics event logging**.

Bu noktalar tamamlandığında, marketing tarafı Drain’i:
- “Meaningful input for faster learning.”
- “Personalized comprehensible input.”
tezleriyle sahada rahatlıkla konumlandırabilir.

---
