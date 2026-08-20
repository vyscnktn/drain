# CLAUDE.md — German Learning App (Krashen Engine)

Bu dosya, Claude Code'a projenin amacını, mevcut veritabanı yapısını ve çalışma kurallarını anlatır. **Bu dosyayı her görev başında dikkate al.**

---

## 1. Proje Özeti

Almanca öğrenme uygulaması (MVP). Pedagojik temel: **Stephen Krashen'in Comprehensible Input (i+1) teorisi** + **Paul Nation'ın %95 bilinen kelime oranı** yaklaşımı.

Kesin kurallar:
- **Çeviri yok.** Başka dilde ipucu yok. Açıklamalar yine Almanca (`german_gloss`, `usage_note_de`).
- Metinler LLM ile üretilir; hedef: metindeki kelimelerin ~%95'i kullanıcı tarafından biliniyor olmalı.
- Kişiselleştirme: kullanıcının kelime hakimiyet durumu (`user_word_state`) üzerinden.

Kullanıcı profili hedef domain'leri: `IT`, `HEALTH`, `ACADEMIC`.

---

## 2. Mimari (planlanan)

```
Frontend (React/Next.js - publishable key ile, RLS aktif)
   |
FastAPI backend (Python, service role key - RLS bypass, SADECE server'da)
   |
Supabase (Postgres + pgvector)  +  LLM API
```

- Kritik yazma işlemleri (mastery güncelleme, `generated_text_words` kaydı vb.) **backend** yapar; service role key asla istemciye verilmez.
- Kullanıcı tarayıcıdan sadece kendi verisini okur (RLS policy'leri buna göre kurulu).

---

## 3. Supabase Veritabanı (KURULDU — DEĞİŞTİRME)

### Tablolar

| Tablo | Görev |
|---|---|
| `auth.users` | Supabase Auth (otomatik) — giriş kimliği |
| `public.profiles` | Kullanıcı profili: `id` (FK → auth.users), `full_name`, `target_domain` ('IT'/'HEALTH'/'ACADEMIC'), `target_level`, `plan`, `trial_started_at`, `created_at` |
| `public.words` | Ortak kelime havuzu (tüm kullanıcılar için aynı) |
| `public.word_edges` | Kelimeler arası yönlü ilişki ağı (graph) |
| `public.user_word_state` | Kullanıcıya özel öğrenme durumu (kişiselleştirmenin kalbi) |
| `public.generated_texts` | LLM'in ürettiği metinler |
| `public.generated_text_words` | Metin ↔ kelime köprü tablosu (many-to-many) |
| `public.text_ratings` | Kullanıcının metne verdiği 1–5 yıldız |

### `words` kolonları
- `id` bigint identity PK
- `lemma` text NOT NULL UNIQUE — kelimenin kök hali
- `surface_form` text — kullanıcıya gösterilen doğal biçim (örn. `die Rückmeldung`)
- `pos` text — 'NOUN','VERB','ADJ','ADV','PHRASE'
- `domain` text NULLABLE — NULL = genel çekirdek kelime; aksi halde 'IT'/'HEALTH'/'ACADEMIC' (CHECK constraint)
- `cefr_level` text — 'A1','A2','B1','B2','C1'
- `zipf_score` real — frekans/yaygınlık skoru
- `german_gloss` text — Almanca kısa açıklama (çeviri DEĞİL)
- `usage_note_de` text — Almanca kullanım notu
- `embedding` vector(768) — pgvector, semantic search için (şimdilik çoğu NULL)
- `source_tag` text — CHECK: 'goethe_a1','goethe_a2','goethe_b1','telc_reference','it_book','health_book','academic_book','manual'
- `source_ref` text — detay kaynak adı (kitap adı vb.)
- `is_core` boolean NOT NULL DEFAULT false — genel A1–B1 çekirdek listeden mi
- `notes` text
- `created_at`

### `word_edges` kolonları
- PK: (`source_word_id`, `target_word_id`, `relation_type`) — her ikisi de FK → `words(id)`
- `relation_type`: 'PREREQUISITE_FOR','OFTEN_CO_OCCURS_WITH','USED_IN_SCENARIO','CAUSES','SYNONYM_OF','OPPOSITE_OF'
- `weight` real, `is_curated` boolean, `evidence_source` text, `created_at`

### `user_word_state` kolonları
- PK: (`user_id`, `word_id`) — FK → auth.users ve words
- `mastery_score` real (0.00–1.00), `exposure_count` int, `last_seen_at`, `last_rating`, `created_at`, `updated_at`

### `generated_texts` kolonları
- `id` PK, `user_id` FK, `domain`, `level`, `anchor_word_id` FK → words, `content` text, `unknown_ratio` real, `validation_passed` boolean, `created_at`

### `generated_text_words` kolonları
- PK: (`generated_text_id`, `word_id`) — FK'ler
- `occurrences` int, `is_target` boolean

### `text_ratings` kolonları
- `id` PK, `generated_text_id` FK, `user_id` FK, `rating` int (1–5), `created_at`

### RLS (Row Level Security) — TÜM kullanıcı verisi tablolarında AKTİF
- `profiles`, `user_word_state`, `generated_texts`, `generated_text_words`, `text_ratings`: `enable row level security` açık.
- Policy mantığı: `auth.uid() = user_id` ile kullanıcı sadece kendi satırlarını görür/yazar (`select_own`, `insert_own` pattern'i).
- `generated_text_words` için policy, parent `generated_texts` üzerinden `exists (...)` ile kontrol eder.
- UPDATE/DELETE policy'leri MVP'de bilinçli olarak YOK (yüzeyi küçük tut).
- `words` ve `word_edges` ortak havuz: herkese okunabilir.

---

## 4. Mevcut Veri Durumu

- Test kullanıcısı: Supabase Dashboard → Authentication → Users üzerinden oluşturuldu (gerçek e-posta, UUID elde mevcut).
- `profiles`: bu kullanıcı için 1 satır (`target_domain='IT'`, `target_level='B2'`, `plan='free'`).
- `words`: 8 örnek kelime (id 1–8): deployment, fehlschlagen, rueckmeldung, variable, funktion, symptom, studie, argumentieren.
- `word_edges`: 4 örnek ilişki (deployment→fehlschlagen vb.).
- `user_word_state`: henüz BOŞ (bilinçli — gerçek kelime listesi importundan sonra dinamik oluşacak).

---

## 5. Veri Import Stratejisi (SIRADAKI ANA İŞ)

1. **A1/A2/B1 genel çekirdek:** Goethe Wortliste'leri **referans** olarak kullanılır; kendi normalize edilmiş lemma listemiz oluşturulur (PDF içeriğini, örnek cümleleri birebir kopyalama — telif). Import'ta: `domain=NULL`, `is_core=true`, `source_tag='goethe_a1'|'goethe_a2'|'goethe_b1'`.
2. **B1 sonrası domain katmanı:** IT Ausbildung kitapları, hemşirelik hazırlık kitapları (örn. Linie 1 Pflege), akademik Almanca kitapları → metin çıkar → **lemmatize** et → `domain='IT'|'HEALTH'|'ACADEMIC'`, `is_core=false`, `source_tag='it_book'|'health_book'|'academic_book'`.
3. Import aracı: CSV → Supabase import veya Python pipeline (lemmatization + normalizasyon + CSV üretimi).

---

## 6. Öğrenme Döngüsü (backend'de implemente edilecek)

1. Kullanıcının iyi bildiği kelimeyi **anchor** seç (`user_word_state.mastery_score` yüksek).
2. `word_edges` üzerinden anchor'a bağlı, az bilinen hedef kelime(ler)i bul.
3. LLM'e: anchor + hedef kelimeler + domain + seviye ile metin ürettir.
4. `unknown_ratio` hesapla, hedef ~%5 bilinmeyen → `validation_passed`.
5. Metni `generated_texts`'e, içindeki kelimeleri `generated_text_words`'e yaz.
6. Kullanıcı 1–5 yıldız verir (`text_ratings`).
7. Backend: rating'e göre metindeki kelimelerin `mastery_score`/`exposure_count` değerlerini günceller (`is_target=true` kelimelere daha yüksek etki).

---

## 7. Claude Code İçin Çalışma Kuralları

- Kullanıcı DB/SQL'de **başlangıç seviyesi**: her SQL adımını ne/neden/nereye açıklayarak ver; query'ler bir kerelik kurulum mu yoksa tekrarlı mı belirt.
- Supabase şemasını **değiştirme**; gerekirse önce kullanıcıya öner, onay al.
- Migration tarzı değişikliklerde `if not exists` / `drop ... if exists` kullan (idempotent olsun).
- Yeni kolon eklerken mevcut CHECK constraint'leri bozma; önce drop, sonra yeniden add pattern'i.
- Çeviri üretme: kullanıcıya gösterilecek her şey Almanca içerik mantığında olmalı.
- `surface_form` yazarken isimler artikelli (`der/die/das`) tutulur.
- MVP sade tutulur: yeni tablo/özellik önermeden önce "bu MVP için şart mı?" diye sor.
- Secret key'ler (service role, LLM API key) sadece backend env'te; frontend'e publishable key.
