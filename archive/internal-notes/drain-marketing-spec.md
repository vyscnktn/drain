# Drain Marketing & Growth Spec (MVP)

This document summarizes Drain's strategic marketing and growth decisions, along with the corresponding product and engineering requirements. Its purpose is to ensure the development team builds a product experience that is **fully aligned with marketing strategy**.

---

## 1. Product Positioning

**Brand name:** Drain  
**Domain:** `drainmind.com`  
**Category:** Personalized reading/speaking coach for professional German (Fachsprache).

**Positioning:**

- **NOT** a traditional language learning app.
- Scientific foundation:
  - Stephen Krashen – *Comprehensible Input*
  - Paul Nation – *95% known / 5% unknown vocabulary ratio*
- What we sell to users:
  - Not "vocabulary memorization," but **faster learning through optimized, comprehensible input**.
  - Building a portable "Digital Brain" (knowledge graph) that users own and can export anytime.

---

## 2. Target Audience (ICP)

**Primary ICP (MVP): Healthcare Professionals – Pflege**

- Working or seeking work in Germany:
  - Nurses (Pflegekräfte)
  - Clinic/elderly care facility staff
- Mandatory requirement:
  - Passing the Fachsprachenprüfung (B2/C1 medical language exam).
- Payment motivation:
  - Cannot start working / obtain Approbation without passing the exam.
  - They pay not to *"learn German"* but to *"pass the exam and start working."*

**Secondary ICP (later stage):**

- IT professionals (C1 business German, job interviews, career advancement).
- For now, product and messaging are designed exclusively for Pflege.

---

## 3. Brand & Naming

- **Primary brand:** Drain
- **Domain:** `drainmind.com` (user-facing communications use only "Drain").
- Logo:
  - Funnel/droplet shape on top (language input → filtering).
  - 3–4 synapse/neural nodes below (digital vocabulary brain).
  - Monoline, single color (deep teal), minimalist.

---

## 4. Value Proposition & Taglines

**Core value proposition:**

> We track each user's level and vocabulary mastery to generate daily German texts/dialogues they can actually understand and that genuinely advance their progress.  
> This gets them to exam and job readiness faster.

**Tagline set (by context):**

- User-facing (landing hero / app):
  - **"Drain — Meaningful input for faster learning."**
- Scientific/theoretical (about page / investor deck / technical docs):
  - **"Drain — Personalized comprehensible input."**

**Rule:**  
The first tagline takes precedence on landing page and in-app; the second is reserved for "About" sections or investor presentations.

---

## 5. Funnel & UX Requirements

This section defines **in-product flows** that support the marketing strategy.

### 5.1. Landing Page

**Goal:**  
Communicate a single clear promise to the Pflege target audience:  
> "Pass the Fachsprachenprüfung not by memorizing, but through personalized meaningful input — faster."

**Engineering requirements:**

- Single-page landing:
  - Hero:
    - Logo + "Drain"
    - Tagline: "Meaningful input for faster learning."
    - Single CTA: "Start free trial" (leads to trial flow).
  - Problem section:
    - Narrative around "Vocabulary memorization doesn't work / doesn't stick in the exam."
  - How it works section:
    - Simple visualization of the 95% known / 5% new word logic.
    - Message: "The language engine adapts texts to your level as it learns you."
  - Digital Brain (Obsidian/Markdown export) section:
    - Simple visual showing vocabulary graph → export flow.
    - Message: "The language you learn isn't trapped in an app; it stays with you as a digital brain you own."

### 5.2. Lead Magnet & Email Capture (Optional but marketing-critical)

- Simple form:
  - "300 most critical Pflege words for Fachsprachenprüfung + 20 sample dialogues PDF"
  - Email field + consent.
- Engineering:
  - `leads` table in Supabase or similar DB (email, segment, created_at).
  - This form can be a separate tab or section on drainmind.com.

### 5.3. Signup & Pricing (MVP)

**MVP pricing (marketing decision):**

- Free/trial:
  - 7 days, limited texts/dialogues per day (e.g., 1–3).
- Paid:
  - **Exam package recommendation (future phase):** 3-month single payment (e.g., €99).
  - MVP can also offer a simple monthly plan (e.g., €29/month).

**Engineering requirements:**

- User model:
  - `plan` (free, trial, paid)
  - `trial_start`, `trial_end`
  - `subscription_status`
- Flow:
  - Landing CTA → signup → trial start.
  - End of trial → in-app and email "choose your package" screen.

---

## 6. In-App Marketing Features (Product-Led Growth)

The marketing strategy uses the product itself as the **coach and motivation tool**. Critical behaviors for engineering to implement:

### 6.1. Onboarding – Level & Calibration

**Problem:**  
A user's B1/B2/C1 certificate doesn't mean they know all vocabulary at that level. Wrong level at onboarding → churn.

**Decision:**

- User enters their declared level (e.g., "B2 Pflege").
- Then shown **3 calibration texts**:
  1. **One level below** declared level.
  2. Same level, assuming vocabulary mastery starts at **0.55**.
  3. Same level, assuming vocabulary mastery starts at **0.75**.

- User rates each text 1–5 stars.
- Additional input:
  - "Was this text too easy / just right / too difficult for you?" (3 options)
- After these three texts, the system automatically selects the **starting mastery band**.

**For engineering:**

- Model level:
  - `declared_level`
  - `mastery_score` (0.0–1.0)
  - `confidence_score` (prior confidence)
- Onboarding flow:
  - Level form → 3 text presentations → rating and difficulty feedback → initial setting.

### 6.2. Rating & Mastery Update

At the end of each text:

- 1–5 star rating.
- Optional difficulty selection ("easy / just right / hard").

**Decision:**

- 1–2 stars → negative update on related vocabulary.
- 3 stars → neutral.
- 4–5 stars + "just right" → strongest positive update.
- "Too easy" → mastery increase limited (prevents re-teaching already known content).
- "Too difficult" → related vocabulary temporarily withdrawn, more anchors needed.

**Engineering:**

- Vocabulary level:
  - `mastery_score` update function.
  - `evidence_count` (how many texts this word appeared in).
- Text level:
  - Rating must be logged (for analytics).

### 6.3. Digital Brain (Obsidian/Markdown Export)

**Marketing decision:**  
This feature gives users the confidence that "my language level belongs to me, not locked in the platform" → lock-in.

**Engineering requirements:**

- For each user:
  - Vocabulary graph (nodes: words, edges: relationships).
  - Mastery and example sentences.

- Export format:
  - `.md` files:
    - Separate Markdown file per word (example sentences, mastery, tags).
    - `[[wikilinks]]` structure for relationships.
  - Packaged as `.zip` Vault.

- UI:
  - "Download your Digital Brain (.zip)" button in settings/profile section.

### 6.4. Gamification (Science-aligned)

**Marketing decision:**  
Gamification exists, but **optimizes learning, not gameplay**.

**Engineering requirements:**

- Streak:
  - Daily streak for completing at least 1 meaningful text/dialogue.
  - "Streak freeze" (e.g., 1 forgiven day per week).
- Visual graph:
  - User's vocabulary brain displayed as a simple node-link diagram.
  - Weekly "Your brain grew X new connections this week" card (shareable).
- 95/5 indicator:
  - At the start/end of each text:
    - Badge showing "Today you saw X new words, Y familiar words."

---

## 7. B2B / Enterprise Preparation (MVP + Beyond)

**Marketing goal:**  
Long-term revenue through B2B via clinics and recruitment agencies.

**Engineering requirements:**

- Corporate client model:
  - `organization` table (clinic/agency).
  - `candidate` table (users linked to organization).
- Admin/HR panel:
  - Candidate-level progress report:
    - Active day count.
    - Vocabulary mastery progression.
    - Simulated exam performance (future).

This doesn't need to be fully built in MVP; but preparing the data model level is critical for the marketing side.

---

## 8. Analytics & Measurement

Marketing will be driven by in-product data. Engineering needs to implement event-based logging.

**Minimum event set:**

- `landing_view` (source: organic, ads, etc.)
- `signup_started`, `signup_completed`
- `trial_started`, `trial_converted_to_paid`
- `onboarding_completed` (3 texts + rating finished)
- `content_generated` (text/dialogue)
- `content_completed` (read/played to end)
- `rating_submitted` (1–5 + difficulty)
- `streak_day_completed`
- `export_downloaded` (Obsidian/digital brain zip)

These events can be collected via Supabase or a separate analytics system.

---

## 9. Roadmap Priorities (Developer sequence)

1. **Core onboarding + calibration flow** (level → 3 texts → rating → mastery initialization).
2. **Rating → mastery update function** (MVP simple but functional).
3. **Digital brain export (Markdown + zip)**.
4. **Streak + basic graph/gamification screen**.
5. **Landing page (hero, explain, CTA) + trial flow**.
6. **Analytics event logging**.

Once these are complete, the marketing side can confidently position Drain with:
- "Meaningful input for faster learning."
- "Personalized comprehensible input."

---
