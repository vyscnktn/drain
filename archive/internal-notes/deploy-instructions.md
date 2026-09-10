# Deploy Talimatları — Agent Görev Dosyası (v1)

Bu dosya, dil öğrenme uygulamasının AWS'e ilk production deploy'u için agent'ın yapacağı işleri tanımlar.
Güvenlik kuralları için `supabase-security-guidelines.md` ve `app-security-guidelines.md` BAĞLAYICIDIR — bu dosyadaki hiçbir adım onları ihlal edemez.

## Kilitlenen Mimari (değiştirilemez, sorun olursa kullanıcıya sor)

```
GitHub repo (PRIVATE olmalı)
   ├── frontend/ (Next.js)  → AWS Amplify Hosting
   └── backend/  (FastAPI)  → Dockerfile → AWS ECR → AWS App Runner

Backend → Supabase (service_role, env'den)
Backend → LLM API'leri (key'ler env'den, provider abstraction korunur)
Frontend → Supabase (sadece publishable/anon key) + Backend API
```

## Agent'ın Görevleri (sırayla)

### Görev 1 — Deploy öncesi güvenlik taraması (app-security Kural 10)

Değişiklik yapmadan önce çalıştır ve sonuçları raporla:
1. `gitleaks detect --source . --verbose` — tüm git geçmişi
2. `pip-audit` (backend) ve `npm audit` (frontend)
3. FastAPI'de `debug=False` ve `/docs` endpoint'inin production'da kapalı olduğunu doğrula (örn. `ENV=production` kontrolüyle)
4. `.gitignore` içinde `.env*` olduğunu doğrula

Kritik bulgu varsa DUR, kullanıcıya raporla, onay bekle.

### Görev 2 — Backend Dockerfile (App Runner için)

`backend/Dockerfile` oluştur:
- Base: `python:3.12-slim`
- `requirements.txt`'ten kurulum (pin'li versiyonlar)
- Çalıştırma: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Non-root user ile çalıştır (`useradd` + `USER`)
- `.dockerignore` oluştur: `venv/`, `__pycache__/`, `.env*`, `tests/`, `*.md`
- Lokalde build testi yap: `docker build -t drain-backend ./backend` ve container'ı ayağa kaldırıp `/health` (yoksa ekle: basit health endpoint) kontrolü

### Görev 3 — `.env.example` dosyaları

- `backend/.env.example`: `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_JWKS_URL`, `GEMINI_API_KEY`, `NIM_API_KEY`, `ENVIRONMENT`, `FRONTEND_ORIGIN` — hepsi BOŞ değerle
- `frontend/.env.example`: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL` — hepsi BOŞ değerle
- Gerçek `.env` dosyalarına DOKUNMA

### Görev 4 — CORS production hazırlığı

`main.py`'deki CORS whitelist'i env'den okunsun: `FRONTEND_ORIGIN` env değişkeni (virgülle ayrılmış liste). Lokal default: `http://localhost:3000`. Canlı Amplify domain'i deploy sonrası kullanıcı tarafından env'e eklenecek.

### Görev 5 — Amplify build config

Repo köküne `amplify.yml` oluştur (frontend `frontend/` alt dizinindeyse monorepo ayarı `applicationsRoot: frontend` ile). Node versiyonunu pin'le. Build komutu Next.js standart (`npm ci && npm run build`).

### Görev 6 — Smoke test scripti

`scripts/smoke_test.py` oluştur — deploy sonrası çalıştırılacak:
1. Backend `/health` → 200 beklenir
2. Auth'suz korumalı endpoint → 401 beklenir
3. Geçersiz domain değeriyle istek → 422 beklenir
4. Rate limit tetikleme testi (ard arda 15+ istek → 429 beklenir)
Base URL'yi argüman olarak alsın: `python scripts/smoke_test.py https://xxx.awsapprunner.com`

### Görev 7 — Deploy dokümanı (kullanıcı için)

`DEPLOY.md` oluştur — kullanıcının AWS Console'da ELLE yapacağı adımlar, numaralı ve basit dille:
1. ECR'de repo oluşturma + image push komutları (docker build/tag/push, `aws ecr get-login-password` dahil)
2. App Runner servisi oluşturma: ECR image seçimi, port 8000, env değişkenleri listesi (hangi değer nereye)
3. Amplify app oluşturma: GitHub bağlantısı (PRIVATE repo — GitHub App yetkisi), env değişkenleri
4. App Runner URL'sini frontend env'ine + Amplify domain'ini backend CORS env'ine ekleme (çapraz bağlantı adımı — atlanırsa uygulama çalışmaz)
5. Smoke test çalıştırma

## Kesin Yasaklar

- Hiçbir gerçek secret hiçbir dosyaya yazılmaz (görev 3'teki .env.example'lar boş kalır)
- DB şemasına dokunulmaz (14 policy + tablolar sabit)
- `user_id` client'tan alınmaz, JWT'den çözülür (mevcut auth.py korunur)
- Provider abstraction bozulmaz; LLM model isimleri env'den okunmaya devam eder
- Deploy komutlarını agent KENDİSİ çalıştırmaz (AWS Console işlemleri kullanıcıya ait); agent sadece dosya/kod hazırlar

## Tamamlanma Kriteri

Tüm görevler bitince: `git diff` özeti + Görev 1 tarama sonuçları + lokal Docker build başarı kanıtı kullanıcıya raporlanır. Kullanıcı onayı olmadan AWS'de hiçbir kaynak oluşturulmaz.
