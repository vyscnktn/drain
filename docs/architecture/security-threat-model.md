# Security Architecture & STRIDE Threat Model

## 1. Security Architecture Principles

Drain enforces a **Defense-in-Depth, Zero-Trust Architecture** designed to protect user privacy, prevent unauthorized learning score manipulation, eliminate credential leakage, and protect against prompt injection attacks.

```mermaid
flowchart TD
    subgraph UntrustedZone [Public / Internet]
        Browser[Client Browser]
    end

    subgraph PerimeterZone [Edge / CDN]
        WAF[AWS Amplify Edge / SSL Termination]
    end

    subgraph ServiceZone [Backend Service VPC]
        FastAPI[FastAPI Container]
        JWTAuth[Bearer JWT Validator]
        Guardrails[Prompt Sanitizer]
    end

    subgraph TrustedDataZone [Supabase Cloud VPC]
        RLS[PostgreSQL Row-Level Security Engine]
        DB[(PostgreSQL Database)]
    end

    Browser -->|HTTPS| WAF
    WAF --> FastAPI
    FastAPI --> JWTAuth
    JWTAuth --> Guardrails
    Guardrails -->|Service Role (Protected Network)| RLS
    RLS --> DB
```

---

## 2. STRIDE Threat Analysis

| Threat Category | Threat Scenario | Impact | Applied Mitigation |
|---|---|---|---|
| **Spoofing** | Attacker attempts to impersonate another learner to view/modify progress. | High | Cryptographically verified Supabase GoTrue JWTs; `auth.uid() = user_id` enforced across all relational queries. |
| **Tampering** | Malicious user modifies HTTP payload to artificially set mastery scores to 1.0. | High | All state-mutating endpoints (`/onboarding/complete`, `/reader/rate`) run strictly on the backend with server-side validation; direct client writes disabled via RLS. |
| **Repudiation** | User denies performing actions or generating content. | Low | Immutable audit logging in `generated_texts` and `text_ratings` with user FK, timestamp, and generation parameters. |
| **Information Disclosure** | Unauthorized query dumps other learners' reading histories or personal profiles. | Critical | Postgres Row-Level Security (RLS) enabled on `profiles`, `user_word_state`, `generated_texts`, `generated_text_words`, and `text_ratings`. |
| **Denial of Service (DoS)** | Script floods `/reader/generate` to exhaust LLM API credits or trigger provider rate limits. | High | In-memory / edge rate limiting, backend thread pool timeouts (`PROVIDER_TIMEOUT=25s`, `CHAIN_TIMEOUT=45s`), and subscription status verification. |
| **Elevation of Privilege** | Client attempts to acquire `service_role` superuser access to bypass security rules. | Critical | `service_role` key strictly stored as backend environment variable; client receives only public `anon_key` with zero schema modification rights. |

---

## 3. Database Row-Level Security (RLS) Permissions Matrix

| Table | Policy Name | Operation | Target Role | Security Expression / Condition |
|---|---|---|---|---|
| `public.profiles` | `select_own` | `SELECT` | `authenticated` | `auth.uid() = id` |
| `public.profiles` | `insert_own` | `INSERT` | `authenticated` | `auth.uid() = id` |
| `public.user_word_state` | `select_own` | `SELECT` | `authenticated` | `auth.uid() = user_id` |
| `public.user_word_state` | *Service Role* | `ALL` | `service_role` | Backend API only (bypasses RLS for automated calculations) |
| `public.generated_texts` | `select_own` | `SELECT` | `authenticated` | `auth.uid() = user_id` |
| `public.generated_text_words` | `select_own` | `SELECT` | `authenticated` | `EXISTS (SELECT 1 FROM generated_texts WHERE id = generated_text_id AND user_id = auth.uid())` |
| `public.text_ratings` | `select_own` | `SELECT` | `authenticated` | `auth.uid() = user_id` |
| `public.text_ratings` | `insert_own` | `INSERT` | `authenticated` | `auth.uid() = user_id` |
| `public.words` | `read_all` | `SELECT` | `anon`, `authenticated` | `true` (Public lexicon read) |
| `public.word_edges` | `read_all` | `SELECT` | `anon`, `authenticated` | `true` (Public graph edges read) |

---

## 4. LLM Prompt Injection & Output Guardrails

1. **System Prompt Isolation**: Prompts strictly separate system instructions (`SYSTEM_PROMPT`) from dynamic runtime variables.
2. **Context Escaping**: User inputs (e.g. target domains or manual vocabulary searches) are sanitized against control characters and template delimiters.
3. **CEFR Output Validation**: The NLP evaluator verifies that the LLM has generated valid German text conforming to length and sentence limits before committing records to database storage or rendering in the UI.
