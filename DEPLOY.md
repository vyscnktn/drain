# Drain — AWS Production Deployment Rehberi (v1)

Bu rehber, **Drain** uygulamasını AWS üzerinde sıfırdan production ortamına taşımak için hazırlanmıştır.

---

## 🏛️ Mimari Özeti

* **Frontend:** Next.js (SSR / React) → **AWS Amplify Hosting** (Monorepo root: `frontend/`)
* **Backend:** FastAPI (Python 3.12) → **AWS ECR + AWS App Runner** (Port: `8000`)
* **Database & Auth:** **Supabase Cloud** (Managed Postgres + pgvector)

---

## 📋 1. AWS ECR'de Repo Oluşturma & Docker Image Push

AWS CLI yapılandırılmış bir terminalde çalıştırın (Bölge: `eu-central-1` önerilir):

```bash
# 1.1 AWS Değişkenlerini Tanımlayın
export AWS_REGION="eu-central-1"
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPO_NAME="drain-backend"

# 1.2 ECR Private Repository Oluşturun
aws ecr create-repository \
    --repository-name $ECR_REPO_NAME \
    --image-scanning-configuration scanOnPush=true \
    --region $AWS_REGION

# 1.3 ECR'a Docker Login Olun
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# 1.4 Backend Docker Image'ını Derleyin ve Push Edin
docker build -t $ECR_REPO_NAME ./backend
docker tag $ECR_REPO_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest
```

---

## ⚙️ 2. AWS App Runner Servisi Oluşturma

1. **AWS Console** → **App Runner** → **Create service** adımlarına gidin.
2. **Source:**
   * **Repository type:** *Container registry*
   * **Provider:** *Amazon ECR*
   * **Image URI:** `$AWS_ACCOUNT_ID.dkr.ecr.eu-central-1.amazonaws.com/drain-backend:latest`
   * **Deployment settings:** *Automatic* (veya *Manual*)
   * **ECR access role:** App Runner servis rolünü seçin veya oluşturun (`AppRunnerECRAccessRole`).
3. **Configure service:**
   * **Service name:** `drain-backend-prod`
   * **Port:** `8000`
   * **CPU & Memory:** `1 vCPU, 2 GB` (Başlangıç için yeterlidir)
   * **Environment variables:**

| Değişken Adı | Değer / Açıklama |
|---|---|
| `SUPABASE_URL` | Supabase proje URL'i (`https://xyz.supabase.co`) |
| `SUPABASE_SECRET_KEY` | Supabase Service Role Secret Key (Backend admin erişimi, RLS bypass — `SUPABASE_SERVICE_ROLE_KEY` de geçerlidir) |
| `SUPABASE_JWKS_URL` | Supabase Auth JWKS URL (`https://xyz.supabase.co/auth/v1/.well-known/jwks.json`) |
| `GEMINI_API_KEY` | Google Gemini API Key (Birincil LLM motoru — metin üretimi) |
| `NIM_API_KEY` | NVIDIA NIM API Key (Yedek LLM motoru & offline lemmatizer enrichment) |
| `ENVIRONMENT` | `production` (Swagger/OpenAPI docs endpoint'lerini kapatır) |
| `FRONTEND_ORIGIN` | `http://localhost:3000` *(Amplify domain'i oluşunca güncellenecek)* |

4. **Create & Deploy** butonuna tıklayın. Servis deploy edildiğinde size bir URL verecektir (örn: `https://abc123xyz.eu-central-1.awsapprunner.com`).

---

## 🌐 3. AWS Amplify Hosting (Frontend Deploy)

1. **AWS Console** → **AWS Amplify** → **Host web app** seçeneğine tıklayın.
2. **GitHub Bağlantısı:**
   * GitHub hesabınızı yetkilendirin ve `drain` (PRIVATE) reposunu seçin.
   * **Branch:** `main`
3. **App settings:**
   * Amplify monorepo ayarını repo kökündeki [`amplify.yml`](file:///home/can/drain/amplify.yml) dosyasından otomatik algılayacaktır.
4. **Environment variables (Amplify Console):**

| Değişken Adı | Değer / Açıklama |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase Proje URL'i |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase Publishable / Anon Key |
| `NEXT_PUBLIC_API_URL` | App Runner servis URL'i (2. adımdaki URL) |

5. **Save and Deploy** butonuna basın. Build tamamlandığında Amplify size canlı domain'i verecektir (örn: `https://main.d1234567.amplifyapp.com`).

---

## 🔄 4. Çapraz Bağlantı (CORS Ayarı — KRİTİK)

Frontend ve Backend'in birbiriyle güvenli iletişim kurabilmesi için:

1. **AWS App Runner** → `drain-backend-prod` → **Configuration** → **Configure** sekmesine gidin.
2. `FRONTEND_ORIGIN` değişkenini güncelleyin:
   ```text
   FRONTEND_ORIGIN=https://main.d1234567.amplifyapp.com,https://your-custom-domain.com
   ```
3. **Apply changes** butonuna basın.

---

## 📧 5. Supabase E-Posta Doğrulama & Yönlendirme Ayarı (Redirect URLs)

Kayıt olan kullanıcıların doğrulama e-postasına tıkladığında canlı Amplify adresinize yönlenmesi için:

1. **Supabase Dashboard** → **Authentication** → **URL Configuration** menüsüne gidin.
2. **Site URL**: Canlı frontend adresinizi girin (örn: `https://main.d1234567.amplifyapp.com`).
3. **Redirect URLs** (İzin Verilen Yönlendirme Listesi):
   - `http://localhost:3000/**` *(Yerel geliştirme için)*
   - `https://*.amplifyapp.com/**` *(Amplify preview ve canlı domainleri için)*
   - `https://your-custom-domain.com/**` *(Özel domaininiz için)*
4. **Save** butonuna basın.

---

## 🧪 6. Canlı Smoke Testi Çalıştırma

Deploy tamamlandıktan sonra lokal makinenizden API sağlığını doğrulamak için:

```bash
python scripts/smoke_test.py https://abc123xyz.eu-central-1.awsapprunner.com
```

Tüm testler yeşil yandığında (`5/5 PASS`) uygulamanız başarıyla canlıya alınmış demektir! 🎉
