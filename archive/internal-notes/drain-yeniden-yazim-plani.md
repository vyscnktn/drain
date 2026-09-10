# Drain — Yeniden Yazım Planı (Taslak)

*Hazırlanma tarihi: 28 Ağustos 2026*

## 0. Bu plan neye dayanıyor

Bu dokümanı yazmadan önce mevcut `drain` projesine baktım: git geçmişi, dosya boyutları, hangi dosyaların ne sıklıkta değiştiği ve birkaç kritik dosyanın (`onboarding.py`, `llm_engine.py`, `lemmatizer.py`, `krashen_engine.py`, `pipeline.py`) içeriği.

Üç somut tespit, aşağıdaki önerilerin temelini oluşturuyor:

**Proje küçük ve genç.** 20 Ağustos'ta başlamış, 10 commit var, toplam kod ~5100 satır (backend ~2000, frontend ~3100). Bu, yıllarca büyümüş bir "kod yığını" değil. Yani sorunun kaynağı büyük ihtimalle mimari çürüme değil, birkaç spesifik tasarım kararı.

**Sorun tüm projeye yayılmış değil, iki noktada yoğunlaşmış.** 10 commit içinde `Onboarding.tsx` 8 kez, `onboarding.py` 5 kez, `llm_engine.py` 4 kez değişmiş — auth, config, krashen_engine gibi kısımlar nispeten sakin kalmış. Yani en kırılgan yer: **onboarding + LLM metin üretim akışı**.

**Veri tarafında söylediğin sorun kodda gerçekten görünüyor.** `pipeline.py`'deki `/ingest` endpoint'i sadece `domain` parametresi alıyor, `subdomain` diye bir alan hiç yok. Buna karşılık `onboarding.py` ve veritabanı şeması `domain` + ayrı bir `subdomain` alanını bekliyor. `llm_engine.py` içindeki `SCENARIOS` sözlüğünde ise `IT`, `HEALTH` ve `MEDIZIN` aynı seviyede, birbirinden bağımsız anahtarlar olarak duruyor — yani "HEALTH domain'i altında MEDIZIN bir subdomain'dir" fikri üç farklı dosyada üç farklı şekilde (ya da hiç) modellenmiş. Senin "subdomainler 2 ana domain altında birleşti, domain kelimeleri domain dışından geliyor" gözlemin, tam olarak bu tutarsızlığın belirtisi. Ayrıca `lemmatizer.py`'deki `enrich_lemmas_fast` fonksiyonu, LLM kullanılmadığında her kelime için şablon bir açıklama üretiyor ("Wichtiger Fachbegriff aus dem Bereich {domain}") ve kitaptan çıkan hiçbir kelime için "bu gerçekten o domain'e özgü mü, yoksa zaten genel çekirdek kelime mi" diye bir kontrol yapılmıyor — kitaptaki her sık geçen kelime doğrudan domain kelimesi sayılıyor.

Bu üç tespit ışığında plan iki ana bacağa ayrılıyor: **(A) veri/kelime pipeline'ı** ve **(B) uygulama mimarisi (onboarding + LLM akışı + genel yapı)**. Aşağıda her biri için karar noktaları var; her birinde bir önerim var ama nihai karar senin.

---

## 1. Hedef ve kapsam tanımı

"Minimalist ve verimli" ifadesini somutlaştıralım, yoksa ölçülemez:

- Yeni backend'de her endpoint, her tablo, her arka plan görevi için "MVP için şart mı?" sorusu cevaplanmış olmalı (bu kural zaten `CLAUDE.md`'de var, korunmalı).
- Bir subsystem'de birden fazla zaman aşımı katmanı iç içe olmayacak (şu an provider timeout 25s, hard timeout 40s, chain timeout 45s şeklinde üçlü bir yapı var — bu hem anlaşılması hem debug edilmesi zor).
- Global, süreç-içi (in-memory) state (örn. `_CALIBRATION_CACHE`) olmayacak; her state ya veritabanında ya da istemcide olacak. In-memory cache sunucu yeniden başlayınca / birden fazla worker çalışınca sessizce bozulan bir kaynak.
- Domain/subdomain gibi taksonomi bilgisi **tek bir yerde** tanımlanacak (tek "source of truth"), hem backend hem frontend oradan okuyacak.

**Karar 0 — Onay:** Bu dört ilkeyi hedef kabul ediyor musun, yoksa eklemek/çıkarmak istediğin bir ilke var mı?

---

## 2. Genel mimari

**Karar 1 — Backend/Frontend ayrımı.** Şu an FastAPI (Python) + Next.js (TypeScript) + Supabase üçlüsü var. Bu ayrım kendi başına kötü değil ama bir MVP için iki ayrı runtime, iki ayrı dil, iki ayrı deploy hattı (Amplify + ayrı backend deploy) anlamına geliyor.
- *Öneri:* Ayrımı koru (FastAPI + Next.js), çünkü lemmatizasyon (spaCy, Python-native) ve LLM orkestrasyonu backend'de kalmalı; bunu Next.js API route'larına taşımak spaCy gibi Python-only araçları terk etmeyi gerektirir. Asıl minimalizm kazancı mimariyi değiştirmekten değil, backend içindeki katman sayısını azaltmaktan gelecek.
- *Alternatif:* Tamamen Next.js + Supabase Edge Functions (Python pipeline'ı ayrı, tek seferlik bir script/cron olarak çalışır, canlı API'de Python olmaz). Daha az hareketli parça ama edge function'larda spaCy gibi ağır bağımlılıklar çalıştırmak zor.

**Karar 2 — Veritabanı.** Supabase + Postgres + pgvector şeması genel olarak makul kurulmuş (RLS, service-role ayrımı doğru düşünülmüş). Sorun şema tasarımında değil, şemayı besleyen pipeline'da.
- *Öneri:* Şemayı koru, `words`/`word_edges`/`user_word_state` tablolarını sıfırdan kurmaya gerek yok. Asıl değişiklik: `domain` alanına ek olarak **gerçek bir `subdomains` referans tablosu** (ya da en azından sabit bir enum + FK) eklemek, şu anki serbest metin `subdomain` alanının yerine.
- *Alternatif:* Domain/subdomain'i tamamen düzleştirip (IT, IT_BACKEND, HEALTH_PFLEGE, HEALTH_MEDIZIN, HEALTH_PHYSIO, ACADEMIC gibi tek seviyeli bir liste) hiyerarşi karmaşasını baştan ortadan kaldırmak. Daha basit ama "domain bazlı genel istatistik" gibi sorguları biraz zorlaştırır.

**Karar 3 — LLM sağlayıcı stratejisi.** Şu an Gemini (birincil) + NVIDIA NIM (yedek) + iç içe timeout'lar + global cache var. Commit geçmişi bu zincirin defalarca "sertleştirildiğini" gösteriyor (`harden LLM fallback chain`, `timeout hardening`) — yani zaten kırılgan olduğu biliniyor.
- *Öneri:* Tek sağlayıcı + basit retry (örn. 2 deneme, sabit backoff) ile başla. İki sağlayıcılı fallback, gerçek trafik ve gerçek downtime verisi olmadan şu aşamada karmaşıklığı hak etmiyor. Gerekirse ileride tekrar eklenir.
- *Alternatif:* İki sağlayıcıyı koru ama fallback mantığını LLM çağrısını yapan tek bir fonksiyona indir (şu an birden fazla yerde tekrarlanan try/except-timeout deseni var gibi görünüyor); en azından kod tekrarını kaldır.

---

## 3. Veri modeli: Domain / Subdomain hiyerarşisi

Bu, senin en somut şikayetinin kaynağı olduğu için ayrı başlık açıyorum.

**Karar 4 — Hiyerarşi nasıl modellenecek.** Şu an üç farklı dosyada üç farklı model var: DB şemasında `domain` (enum: IT/HEALTH/ACADEMIC) + `subdomain` (serbest metin, nullable); `onboarding.py`'de `Literal['IT','HEALTH','ACADEMIC']` + ayrı `subdomain: Optional[str]`; `llm_engine.py`'de ise `IT`, `HEALTH`, `MEDIZIN` düz, birbirinden bağımsız sözlük anahtarları.
- *Öneri:* Tek bir `TAXONOMY` sabiti (örn. `app/core/taxonomy.py`) tanımla: `{"IT": [], "HEALTH": ["PFLEGE", "MEDIZIN", "PHYSIOTHERAPIE"], "ACADEMIC": []}` gibi. Hem backend hem frontend (build-time'da senkronize edilen bir kopya ya da backend'den çekilen bir `/taxonomy` endpoint'i ile) bu tek kaynaktan okusun. Yeni bir subdomain eklemek tek dosyada bir satır olsun.
- Bu değişikliğin gerektirdiği şey: `pipeline.py`'deki `/ingest` endpoint'ine eksik olan `subdomain` parametresini eklemek ve `lemmatizer.py`'nin domain etiketini üretirken bu taksonomiye karşı doğrulama yapması.

**Karar 5 — MVP'de hangi domain/subdomain'ler olacak.** `documents/` klasöründeki kaynaklara bakınca zaten şu eşleme ortaya çıkıyor: `informatik/` → IT, `medizin/` + `pflege/` + `physiotherapie/` → HEALTH'in üç subdomain'i, `academisch/` → ACADEMIC. `wortliste/` (Goethe A1/A2/B1 listeleri) ise domain'siz genel çekirdek kelime kaynağı.
- *Öneri:* MVP'yi bu beşliyle sınırla (IT, HEALTH→PFLEGE/MEDIZIN/PHYSIOTHERAPIE, ACADEMIC) — zaten elindeki kaynaklar bu. Yeni domain eklemeyi ileri bir faza bırak.

**Karar 6 — Domain kelimesi neye göre belirlenecek.** Şu anki pipeline, bir kitaptan çıkan ve `min_freq=2` eşiğini geçen her kelimeyi otomatik olarak o kitabın domain'ine ait sayıyor. Bu, senin "domain kelimeleri domain dışından" dediğin sorunun kök nedeni: bir hemşirelik kitabındaki gündelik kelimeler (örn. "sagen", "wichtig", "Zeit") HEALTH domain kelimesi olarak işaretleniyor, halbuki bunlar zaten genel A1-B1 çekirdek listesinde olması gereken kelimeler.
- *Öneri:* İki aşamalı filtre: (1) önce kelimeyi genel çekirdek listeye (Goethe Wortliste) karşı kontrol et — oradaysa `domain=NULL, is_core=true` olarak işaretle, domain kitabından geldiği için değil; (2) sadece çekirdek listede olmayan kelimeler domain-spesifik aday olsun. İstersen ek olarak bir "ayırt edicilik" skoru (bu kelime bu kitapta, genel dilden ne kadar daha sık geçiyor — basit bir oran hesabı, TF-IDF gerekmez) ekleyip düşük skorluları elemek.

**Karar 7 — Kelime açıklamaları (`german_gloss`, `usage_note_de`) gerçek mi şablon mu olacak.** Şu anki `enrich_lemmas_fast(use_llm=False)` modu her kelime için birebir aynı kalıp cümleyi üretiyor — pedagojik değeri sıfıra yakın.
- *Öneri:* Import bir defalık, toplu bir iş olduğu için (canlı kullanıcı trafiği değil) LLM enrichment'ı varsayılan yap, hız kaygısıyla şablona düşme; maliyet ve süre kelime sayısına göre önceden hesaplanabilir bir iş.
- *Alternatif:* Şablonu koru ama en azından şablonun içine kelimenin POS'una ve gerçek örnek cümlesine (kitaptan alınan orijinal cümle) referans ekle, tamamen jenerik olmasın.

**Karar 8 — Import idempotency.** Aynı kitap iki kez import edilirse ne olacak, kötü bir batch fark edilirse geri alınabilecek mi (örn. `import_batch_id` gibi bir alan, silmek/rollback yapmak için)?
- *Öneri:* `words` tablosuna `import_batch_id` ekle; kötü bir import'u tek sorguyla geri almak mümkün olsun. Şu an bu yok, yani kirli veri fark edilse bile temizlemek zor.

---

## 4. Onboarding / metin üretim akışı

Commit geçmişinin en çok yamadığı yer burası, o yüzden en detaylı bölüm bu.

**Karar 9 — Senkron mu, arka plan görevi mi.** Şu anki tasarım: kullanıcı onboarding'e başlıyor → backend `BackgroundTasks` ile arka planda metin üretiyor → frontend polling ile "hazır mı?" diye soruyor → sonuç `_CALIBRATION_CACHE` adlı process-içi bir sözlükte tutuluyor. Bu, hem "neden bazen kayboluyor" (worker restart, birden fazla instance) hem de "neden bazen yarım kalıyor" (polling/timeout senkronizasyonu) tipi hataların doğal kaynağı.
- *Öneri A (en minimalist):* Tamamen senkron yap. LLM çağrısı 5-10 saniye sürüyorsa, kullanıcıya bir loading state göster ve tek istekte cevabı bekle. Arka plan görevi + polling + cache — üçü birden — MVP için gereken karmaşıklık değil, "kullanıcı 8 saniye bekliyor" sorunundan kaçmak için eklenmiş bir çözüm gibi duruyor. Bu bekleme süresi gerçekten kabul edilemezse (kullanıcı testi göstermiyor mu?), o zaman B'ye geç.
- *Öneri B (async gerekiyorsa):* Arka plan görevini koru ama state'i in-memory dict yerine `generated_texts` tablosuna bir `status` kolonu (`pending`/`ready`/`failed`) ekleyerek veritabanında tut. Böylece hangi worker/instance çalışırsa çalışsın state kaybolmaz, sunucu restart'ından etkilenmez.
- **Bu karar, planın en önemli tek maddesi.** Hangisini seçeceğin büyük ölçüde "gerçek kullanıcı kaç saniye bekleyebilir" sorusuna bağlı — bunu birlikte netleştirelim.

**Karar 10 — Hata mesajları.** Şu an görünen `OVERLOAD_MESSAGE` ("Der Dienst ist gerade überlastet") hem timeout'ta hem muhtemelen başka hata türlerinde de gösteriliyor gibi duruyor.
- *Öneri:* Hata tiplerini ayır (timeout / sağlayıcı hatası / geçersiz LLM cevabı / ağ hatası) ve her biri için farklı, kullanıcıya ne yapması gerektiğini söyleyen mesaj üret. Şu anki tek-mesaj yaklaşımı debug'ı da zorlaştırıyor (log'da gerçek sebep var ama kullanıcıya hep aynı şey gösteriliyor).

**Karar 11 — Frontend tarafı.** `Onboarding.tsx` 8 kez değişmiş; büyük ihtimalle backend'deki state modeli (preparing/ready/error) her değiştiğinde frontend'in de peşinden koşması gerekmiş.
- *Öneri:* Backend'deki durum modelini netleştirdikten (Karar 9) sonra `Onboarding.tsx`'i sıfırdan, küçük ve net bir state machine (örn. `idle | loading | ready | error`) olarak yeniden yaz — mevcut bileşeni yamamak yerine.

---

## 5. Test ve doğrulama

Mevcut projede zaten 4 test dosyası var (`test_krashen_ratio`, `test_krashen_filter`, `test_onboarding_logic`, `test_llm_fallback`) — bu iyi bir refleks, atılmamalı.

**Karar 12:** Yeniden yazımda önce test mi (özellikle `krashen_engine.py`'deki filtre mantığı ve `is_valid_target_word` gibi ince iş kuralları için — bunlar küçük ama kaybedilmemesi gereken bilgi) yoksa önce çalışan prototip, sonra test mi?
- *Öneri:* `krashen_engine.py`'nin filtre mantığı (INVALID_LEMMAS seti, mastery hesaplama vb.) zaten test edilmiş ve stabil — bunu olduğu gibi taşı, testleriyle birlikte. Asıl yeniden yazılacak yer (onboarding akışı) için önce davranışı test olarak yaz (hangi state'ten hangi state'e ne zaman geçilmeli), sonra kodu o teste göre kur.

---

## 6. Geçiş stratejisi

**Karar 13 — Mevcut veri.** Supabase'de şu an 8 örnek kelime, 4 örnek ilişki, 1 test kullanıcısı var — gerçek/canlı kullanıcı verisi yok.
- *Öneri:* Şemayı koru, örnek veriyi sil, gerçek importu Karar 6-8'deki düzeltilmiş pipeline ile baştan yap. Kaybedilecek gerçek kullanıcı verisi olmadığı için bu adımda risk yok.

**Karar 14 — Hangi kod olduğu gibi taşınacak, hangisi atılacak.**
- Taşınacak (stabil, az değişmiş, iş mantığı değerli): `krashen_engine.py`, `auth.py`, `config.py`, `limiter.py`, veritabanı şeması.
- Yeniden yazılacak (kırılgan, çok yamalı): `onboarding.py`, `Onboarding.tsx`, `llm_engine.py`'nin fallback/cache kısmı, `pipeline.py` + `lemmatizer.py`'nin domain etiketleme kısmı.
- *Öneri:* Bu net ayrım da göstermiyor mu ki tam bir "sıfırdan proje" değil, hedefli bir yeniden yazım daha doğru bir çerçeveleme? Yine de "sıfırdan yeni repo" hissini istiyorsan, bu taşınacak parçaları yeni repoya bilinçli olarak kopyalayarak başlarız — kayıp olmaz, sadece git geçmişi sıfırlanır.

**Karar 15 — Nasıl ilerleyeceğiz.** Aynı repoda yeni bir branch mi, yoksa yepyeni bir repo mu?
- *Öneri:* Yeni branch (`rewrite/v2` gibi) — mevcut `main` bozulmadan, deploy edilebilir halde kalır, geçiş bittiğinde merge edilir. Yeni repo, sana "temiz sayfa" hissini psikolojik olarak daha çok verir ama pratik bir fayda sağlamaz ve deploy/env config'lerini (Amplify, `.env`, Supabase bağlantıları) baştan kurmayı gerektirir.

---

## 7. Sonraki adım

Bu doküman bir taslak — her "Karar" başlığının altına kendi tercihini yazıp (öneriyi kabul/değiştir/reddet) bana geri gönderebilirsin, ya da birlikte madde madde geçip her birine burada karar verebiliriz. En kritik ve en çok etkisi olacak iki karar **Karar 9** (senkron/async) ve **Karar 4** (taksonomi modeli) — istersen bunlardan başlayalım.
