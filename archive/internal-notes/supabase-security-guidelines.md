# Supabase Güvenlik Kuralları — Agent Talimatları

Bu dosya, bu repoda Supabase ile ilgili HER kod/SQL yazımında uyulması zorunlu güvenlik kurallarını tanımlar. Kaynak: Supabase resmi dokümanları ve yaygın üretim hataları analizi (Ağustos 2026).

Proje tabloları: `profiles`, `words`, `word_edges`, `user_word_state`, `generated_texts`, `generated_text_words`, `text_ratings`

---

## KURAL 1 — Her yeni tabloda RLS hemen açılır

Yeni bir tablo oluşturduğunda, aynı migration içinde MUTLAKA:

```sql
alter table public.<tablo_adi> enable row level security;
```

- RLS açık ama policy'siz tablo = kimse erişemez (güvenli ama bozuk).
- RLS kapalı tablo = herkes her şeye erişir (FELAKET). İkisi de kabul edilemez: RLS aç + en az bir policy yaz.

## KURAL 2 — auth.uid() HER ZAMAN (select auth.uid()) olarak yazılır

YANLIŞ (her satır için fonksiyon yeniden çalışır — 100K satırda 5 saniyeye çıkabilir):
```sql
using (auth.uid() = user_id)
```

DOĞRU (sorgu başına bir kez hesaplanır, InitPlan):
```sql
using ((select auth.uid()) = user_id)
```

Aynı kural `auth.jwt()` ve diğer fonksiyonlar için de geçerli.

⚠️ MEVCUT POLICY'LERİMİZDE BU HATA VAR. Düzeltme migration'ı yazılacak: tüm mevcut policy'ler `drop policy` + `create policy` ile `(select auth.uid())` pattern'ine çevrilecek. Etkilenen policy'ler: profiles (3), user_word_state (3), words (1), word_edges (1), generated_texts (2), generated_text_words (1), text_ratings (2).

## KURAL 3 — Policy'ler role kapsamlı yazılır

Her policy'de `to authenticated` (veya gerekiyorsa `to anon`) belirtilir. Role belirtilmezse policy `public`'e uygulanır ve gereksiz yere her sorguda değerlendirilir.

```sql
create policy "x_select_own" on public.x
  for select to authenticated
  using ((select auth.uid()) = user_id);
```

## KURAL 4 — Policy koşulunda kullanılan kolonlara index

RLS koşulunda geçen her kolon (primary key / unique değilse) index'lenir:

```sql
create index if not exists idx_user_word_state_user_id on public.user_word_state (user_id);
create index if not exists idx_generated_texts_user_id on public.generated_texts (user_id);
create index if not exists idx_text_ratings_user_id on public.text_ratings (user_id);
create index if not exists idx_text_ratings_generated_text_id on public.text_ratings (generated_text_id);
create index if not exists idx_generated_text_words_text_id on public.generated_text_words (generated_text_id);
```

İndex'siz policy kolonu = her sorguda sequential scan.

## KURAL 5 — RLS filtreleme için DEĞİL, güvenlik için kullanılır

Uygulama sorguları kendi `.eq('user_id', userId)` filtresini ekler; RLS üstüne güvenlik ağı olarak kalır. "RLS zaten filtreliyor" diye uygulama tarafındaki where koşulunu kaldırma.

## KURAL 6 — service_role key ASLA client'a çıkmaz

- Frontend'de SADECE publishable/anon key. `NEXT_PUBLIC_` / `VITE_` prefix'li env'de service_role YASAK.
- service_role sadece FastAPI backend env'inde.
- Bu reponun hiçbir yerine key hardcode edilmez. `.env` dosyaları `.gitignore`'da olmalı.
- service_role RLS'i TAMAMEN bypass eder (BYPASSRLS) — backend'de kullanırken ownership kontrolü kodda yapılır (örn. rating yazarken `user_id` JWT'den gelen kullanıcıyla eşleşmeli, client'tan gelen user_id'ye güvenilmez).

## KURAL 7 — Sonsuz recursion kontrolü

Bir policy kendi tablosunu sorgularsa (örn. profiles policy'si içinde profiles'a select) sonsuz döngü hatası oluşur. Tablolar arası kontrol gerekiyorsa `security definer` fonksiyon kullan ve fonksiyonda `set search_path = public` sabitle.

⚠️ Mevcut `generated_text_words` policy'miz `generated_texts`'i sorguluyor — bu recursion DEĞİL (farklı tablo), ama generated_texts'in kendi policy'si ile birlikte pahalı olabilir. Değişiklik yapılırken EXPLAIN ANALYZE ile ölç.

## KURAL 8 — Client'tan gelen user_id'ye güvenme

Hiçbir zaman client'ın gönderdiği `user_id` ile yazma yapma. Her zaman server tarafında JWT'den çözülen kullanıcı kimliğini kullan. RLS policy'leri de aynı şekilde `(select auth.uid())` üzerine kurulu.

## KURAL 9 — NULL auth.uid() davranışı

Giriş yapmamış kullanıcıda `auth.uid()` NULL döner ve `NULL = user_id` koşulu hiçbir satırla eşleşmez — bu güvenlidir. AMA "herkese açık" policy'lerde (`words`, `word_edges` gibi) bunun bilinçli tasarım olduğundan emin ol. words/word_edges için `for select to authenticated using (true)` tercihimiz: giriş yapmamış kullanıcı kelime havuzunu göremez.

## KURAL 10 — Değişiklikten sonra test

Her RLS/policy değişikliğinden sonra:
1. SQL Editor'da denetim sorgusu çalıştır (aşağıda).
2. İki farklı test kullanıcısıyla A/B testi: kullanıcı A, kullanıcı B'nin `user_word_state`/`generated_texts`/`text_ratings` satırlarını görememeli.

### Denetim sorguları

```sql
-- 1. RLS kapalı tablo var mı? (public şemada, sonuç BOŞ olmalı)
select tablename from pg_tables
where schemaname = 'public' and not rowsecurity;

-- 2. RLS açık ama policy'siz tablo var mı? (sonuç BOŞ olmalı)
select t.tablename from pg_tables t
where t.schemaname = 'public' and t.rowsecurity
and not exists (
  select 1 from pg_policies p
  where p.schemaname = 'public' and p.tablename = t.tablename
);

-- 3. Tüm policy'leri listele (gözden geçirme için)
select tablename, policyname, cmd, roles, qual, with_check
from pg_policies where schemaname = 'public' order by tablename;

-- 4. auth.uid() wrap edilmemiş policy kaldı mı? (sonuç BOŞ olmalı)
select tablename, policyname from pg_policies
where schemaname = 'public'
and (qual like '%auth.uid()%' or with_check like '%auth.uid()%')
and qual not like '%select auth.uid()%'
and coalesce(with_check,'') not like '%select auth.uid()%';
```

## KURAL 11 — Migration disiplini

- Tüm şema/policy değişiklikleri idempotent olur: `if not exists`, `drop policy if exists` kullan.
- Policy değiştirme = `drop policy if exists <ad> on <tablo>;` + `create policy` aynı migration içinde.
- Production'a çıkmadan önce Kural 10'daki 4 denetim sorgusu çalıştırılır ve sonuçları boş/temiz olduğu doğrulanır.

---

## Öncelikli yapılacaklar (bu proje için)

1. [ ] Mevcut 13 policy'yi `(select auth.uid())` pattern'ine migrate et (Kural 2).
2. [ ] Kural 4'teki indexleri ekle (user_id / generated_text_id kolonları).
3. [ ] Denetim sorgularını çalıştır, sonuçları raporla.
4. [ ] Backend'de service_role kullanılan her endpoint'te ownership kontrolünü gözden geçir (Kural 6/8).
