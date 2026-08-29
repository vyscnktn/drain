import os
import time
import logging
import re
import random
import concurrent.futures
from dotenv import load_dotenv, find_dotenv
from google import genai
from google.genai import types
from openai import OpenAI
from fastapi import HTTPException, status
from typing import List, Tuple, Optional, Union, Dict, Any

logger = logging.getLogger(__name__)

# Always locate and load .env file
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    load_dotenv()

gemini_key = os.environ.get("GEMINI_API_KEY")

PROVIDER_TIMEOUT: float = 25.0
CHAIN_TIMEOUT: float = 45.0
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
OVERLOAD_MESSAGE: str = "Der Dienst ist gerade überlastet, bitte erneut versuchen."


# ─── Client factories ────────────────────────────────────────────────────────

def get_gemini_client(timeout: float = PROVIDER_TIMEOUT) -> Optional[genai.Client]:
    """Primary: Google Gemini via official google.genai SDK."""
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        http_opts = types.HttpOptions(timeout=timeout) if hasattr(types, 'HttpOptions') else None
        return genai.Client(api_key=key, http_options=http_opts)
    return None


def get_nim_client(timeout: float = PROVIDER_TIMEOUT) -> Optional[OpenAI]:
    """Fallback: NVIDIA NIM — OpenAI-compatible endpoint."""
    key = os.environ.get("NIM_API_KEY")
    if key:
        return OpenAI(
            api_key=key,
            base_url="https://integrate.api.nvidia.com/v1",
            timeout=timeout,
        )
    return None


client = get_nim_client()


# ─── Scenarios & Perspectives ────────────────────────────────────────────────

SCENARIOS: Dict[str, List[str]] = {
    "IT": [
        "ein Teammeeting im Software-Entwicklungsteam",
        "eine E-Mail an einen Kollegen über ein Bugfix",
        "ein Problem kurz vor dem Release",
        "ein Code-Review zwischen zwei Entwicklern",
        "ein Vorfall beim Serverausfall",
        "die Planung des nächsten Sprints im Scrum-Team",
        "ein Gespräch mit dem Product Owner über neue Anforderungen",
        "eine Fehlersuche im Datenbankprotokoll",
        "die Einführung eines neuen Sicherheitsprotokolls",
        "eine technische Dokumentation für eine API-Schnittstelle"
    ],
    "HEALTH": [
        "ein Patientengespräch im Behandlungszimmer",
        "die Übergabe zwischen zwei Schichten",
        "ein Beratungsgespräch mit der Ärztin",
        "eine Dokumentation der Pflegemaßnahme",
        "die Aufnahme eines neuen Patienten in der Notaufnahme",
        "ein Gespräch mit Angehörigen über den Behandlungsverlauf",
        "eine Teambesprechung im interdisziplinären Krankenhausteam",
        "die Vorbereitung einer diagnostischen Untersuchung"
    ],
    "MEDIZIN": [
        "ein Anamnesegespräch auf der Station",
        "eine Klinikvisite mit dem Chefarzt",
        "ein Befundgespräch mit einem Patienten",
        "eine Besprechung im OP-Saal",
        "die Auswertung eines Röntgenbildes oder Laborbefunds",
        "ein Konsilgespräch zwischen Fachärzten",
        "die Aufklärung des Patienten vor einem operativen Eingriff",
        "die Verordnung eines Therapie- und Medikationsplans",
        "die strukturierte Patientenübergabe im Schockraum",
        "ein Entlassungsgespräch mit Empfehlungen für den Hausarzt"
    ],
    "PFLEGE": [
        "eine Schichtübergabe im Seniorenheim",
        "die Wundversorgung und der Verbandswechsel bei einem Patienten",
        "ein Gespräch über den Pflegeplan mit der Pflegedienstleitung",
        "die Vitalzeichenkontrolle und Medikamentenausgabe am Morgen",
        "die Begleitung eines Patienten bei der Frühmobilisation",
        "ein einfühlsames Gespräch mit einer besorgten Angehörigen",
        "die Pflegedokumentation im digitalen Krankenhaussystem",
        "das Erkennen und Melden von Notfallsymptomen auf der Station",
        "die Vorbereitung eines Pflegebedürftigen auf die Entlassung",
        "die hygienische Versorgung und Sturzprophylaxe im Pflegealltag"
    ],
    "PHYSIO": [
        "eine Therapiesitzung im Behandlungsraum",
        "eine Übungseinheit zur Mobilisation nach einer Verletzung",
        "ein Beratungsgespräch nach einer Knie- oder Hüft-OP",
        "die Erstellung eines individuellen Trainings- und Heimübungsprogramms",
        "eine Ganganalyse und Haltungskorrektur beim Patienten",
        "die manuelle Therapie bei chronischen Rückenschmerzen",
        "eine Rücksprache mit dem behandelnden Orthopäden",
        "die Motivation eines Patienten während der Rehabilitation",
        "eine ergotherapeutische Beratung für den Arbeitsplatz"
    ],
    "PHARMA": [
        "ein Beratungsgespräch am Kundenschalter der Apotheke",
        "eine Überprüfung des Rezepts vor der Arzneimittelausgabe",
        "die Aufklärung über Wechselwirkungen und Nebenwirkungen eines Medikaments",
        "die Beratung zur korrekten Dosierung und Einnahmezeit von Antibiotika",
        "ein Telefonat mit der Arztpraxis wegen einer Rezeptunklarheit",
        "die Herstellung einer individuellen Rezeptur (Salbe oder Lösung) im Labor",
        "die Einlagerung und Temperaturüberwachung kühlpflichtiger Arzneimittel",
        "die Beratung einer Kundin zu rezeptfreien Schmerzmitteln",
        "das Bestellen von Notfallmedikamenten beim pharmazeutischen Großhandel"
    ],
    "ACADEMIC": [
        "eine Diskussion im Universitätsseminar",
        "eine E-Mail an den Professor wegen der Hausarbeit",
        "ein kurzer Vortrag vor der Forschungsgruppe",
        "ein Kolloquium über methodische Ansätze einer wissenschaftlichen Studie",
        "ein Feedbackgespräch zur Bachelor- oder Masterarbeit",
        "die Auswertung und Diskussion von empirischen Forschungsergebnissen",
        "die Vorbereitung auf eine mündliche Fachprüfung oder Klausur",
        "eine Recherche und Diskussion in der Universitätsbibliothek"
    ],
}

DEFAULT_SCENARIOS = [
    "ein Gespräch am Arbeitsplatz",
    "eine kurze Alltagssituation",
    "eine E-Mail oder Nachricht an einen Kollegen"
]

PERSPECTIVES = [
    "Ich-Perspektive",
    "dritte Person (er/sie)",
    "neutrale Berichtsform"
]


# ─── Level Configurations ───────────────────────────────────────────────────

LEVEL_CONFIG: Dict[str, Dict[str, Any]] = {
    "A1": {
        "sentences": "3-4",
        "words": "25-40",
        "target_uses": "1 Mal",
        "anchors": 2,
        "grammar": "Nur Hauptsätze im Präsens. Sehr kurze Sätze (max. 8-10 Wörter). Keine Konjunktive, keine Passivformen.",
    },
    "A2": {
        "sentences": "4-5",
        "words": "40-60",
        "target_uses": "1 Mal",
        "anchors": 2,
        "grammar": "Hauptsätze und einfache Nebensätze mit 'weil', 'dass', 'wenn'. Präsens und Perfekt.",
    },
    "B1": {
        "sentences": "5-7",
        "words": "60-90",
        "target_uses": "1-2 Mal",
        "anchors": 3,
        "grammar": "Nebensätze, Relativsätze, Präteritum bei 'sein/haben' erlaubt. Konnektoren wie 'deshalb', 'trotzdem'.",
    },
    "B2": {
        "sentences": "6-8",
        "words": "90-130",
        "target_uses": "1-2 Mal",
        "anchors": 3,
        "grammar": "Komplexere Strukturen erlaubt: Konjunktiv II, Passiv, indirekte Rede. Aber der Text bleibt klar und lesbar.",
    },
    "C1": {
        "sentences": "7-10",
        "words": "120-180",
        "target_uses": "2 Mal",
        "anchors": 3,
        "grammar": "Anspruchsvolle Syntax und idiomatische Wendungen erlaubt.",
    },
}


# ─── Prompts ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Du bist ein erfahrener DaF-Autor (Deutsch als Fremdsprache) und schreibst didaktisch wertvolle Lesetexte nach Stephen Krashens 'Comprehensible Input' Methode.
Deine Texte sind grammatikalisch einwandfrei, idiomatisch und klingen wie von einem Muttersprachler verfasst."""

FEW_SHOT_EXAMPLE = """
Beispiel für einen idealen Ausgabetext (Niveau B1, Zielwort: "die Rückmeldung"):
"Der Entwickler wartete geduldig auf das Testergebnis. Nach dem Release der Software schickte die Kundenbetreuung ihm eine kurze Nachricht. Der Kunde war sehr zufrieden mit dem neuen Update. Durch diese positive Rückmeldung konnte das ganze Team beruhigt ins Wochenende gehen."
"""


def _build_user_prompt(
    anchor_words: List[str],
    target_word_str: str,
    domain: str,
    level: str
) -> str:
    cfg = LEVEL_CONFIG.get(level, LEVEL_CONFIG["B1"])
    domain_upper = domain.upper()
    
    # Match domain scenarios
    matched_scenarios = DEFAULT_SCENARIOS
    for k, scs in SCENARIOS.items():
        if k in domain_upper:
            matched_scenarios = scs
            break
            
    scenario = random.choice(matched_scenarios)
    perspective = random.choice(PERSPECTIVES)
    
    # Limit anchor words per level config
    anchors = anchor_words[:cfg["anchors"]]
    
    if anchors:
        anchor_rule = (
            f"Wähle aus diesen bekannten Wörtern {cfg['anchors']}-3 aus, die natürlich passen: {', '.join(anchors)}"
        )
    else:
        anchor_rule = "Es gibt keine Ankerwörter."

    return f"""Schreibe einen kurzen Lesetext auf Deutsch.

Rahmen:
- Niveau: {level}, Bereich: {domain}
- Situation: {scenario}
- Erzählperspektive: {perspective}
- Länge: {cfg["sentences"]} Sätze (ca. {cfg["words"]} Wörter)

Zielwort: "{target_word_str}"
- Kommt {cfg["target_uses"]} vor, in typischer, natürlicher Verwendung (konjugiert/dekliniert, falls nötig).
- Der Kontext muss die Bedeutung des Zielworts erschließbar machen (durch die Situation, ein Beispiel oder eine Umschreibung) — OHNE Übersetzung, OHNE Erklärung in Klammern.

Ankerwörter:
- {anchor_rule}

Grammatik-Regeln:
- {cfg["grammar"]}

Wortschatz-Regeln:
- Abgesehen vom Zielwort und den gewählten Ankerwörtern: nur einfacher Wortschatz auf Niveau {level} oder darunter.
- KEINE weiteren Fachbegriffe aus dem Bereich {domain}.

Format:
- Nur Fließtext. Kein Titel, keine Überschrift, keine Aufzählung, keine Einleitung, keine Erklärungen.

{FEW_SHOT_EXAMPLE}"""


# ─── Core Generation & Fallback ──────────────────────────────────────────────

def _run_with_timeout(func, timeout: float, *args, **kwargs):
    """Executes a function with a strict timeout limit via ThreadPoolExecutor."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Operation timed out after {timeout:.1f}s")


def _call_gemini_raw(user_prompt: str, timeout: float = PROVIDER_TIMEOUT) -> str:
    """Try Google Gemini via official google.genai SDK (primary: gemini-3.5-flash or GEMINI_MODEL env)."""
    g_client = get_gemini_client(timeout=timeout)
    if not g_client:
        raise RuntimeError("GEMINI_API_KEY not configured")

    model_name = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

    try:
        response = g_client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.8,
            )
        )
        if response and response.text:
            return response.text.strip()
        raise ValueError(f"Gemini model '{model_name}' returned empty text")
    except Exception as e:
        logger.warning(f"[LLM] Gemini model '{model_name}' failed: {e}")
        raise


def _call_gemini_with_timeout(user_prompt: str, timeout: float = PROVIDER_TIMEOUT) -> str:
    return _run_with_timeout(_call_gemini_raw, timeout, user_prompt, timeout)


def _call_gemini(user_prompt: str) -> str:
    """Convenience wrapper for direct Gemini calls."""
    return _call_gemini_with_timeout(user_prompt, timeout=PROVIDER_TIMEOUT)


def _call_nim_raw(user_prompt: str, timeout: float = PROVIDER_TIMEOUT) -> str:
    """Try NVIDIA NIM (fallback: meta/llama-4-maverick)."""
    nim_client = get_nim_client(timeout=timeout)
    if not nim_client:
        raise RuntimeError("NIM_API_KEY not configured")

    for model_name in ["meta/llama-3.2-11b-vision-instruct", "meta/llama-3.2-90b-vision-instruct"]:
        try:
            response = nim_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                max_tokens=512,
            )
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"[LLM] NIM model {model_name} failed: {e}")
    raise ValueError("NIM returned an empty or invalid response")


def _call_nim_with_timeout(user_prompt: str, timeout: float = PROVIDER_TIMEOUT) -> str:
    return _run_with_timeout(_call_nim_raw, timeout, user_prompt, timeout)


def _call_nim(user_prompt: str) -> str:
    """Convenience wrapper for direct NIM calls."""
    return _call_nim_with_timeout(user_prompt, timeout=PROVIDER_TIMEOUT)


def _is_rate_limit_error(err: Exception) -> bool:
    s = str(err)
    return any(k in s for k in ("503", "429", "ResourceExhausted", "Worker local total request limit", "rate limit", "Rate limit", "quota"))


def generate_reading_text(
    anchor_words: List[str],
    target_word: Union[str, Dict[str, Any]],
    domain: str = "CORE",
    level: str = "A2",
) -> str:
    """
    Generate a German reading passage using Krashen's i+1 principle.
    Accepts target_word as a string or word dictionary (uses surface_form if available).
    Falls back from Gemini to NIM on ANY error/exception immediately.
    Enforces per-provider timeout (~25s) and overall chain timeout (<=45s).
    Raises HTTP 503 if both providers fail.
    """
    # Extract best word surface string
    if isinstance(target_word, dict):
        target_word_str = target_word.get('surface_form') or target_word.get('lemma') or 'Zielwort'
    else:
        target_word_str = str(target_word)

    user_prompt = _build_user_prompt(anchor_words, target_word_str, domain, level)
    start_time = time.time()

    # ── 1. Try Google Gemini (Primary) ───────────────────────────────────────
    gemini_err = None
    elapsed = time.time() - start_time
    remaining_chain_time = CHAIN_TIMEOUT - elapsed
    gemini_timeout = min(PROVIDER_TIMEOUT, remaining_chain_time)

    if gemini_timeout > 0:
        try:
            text = _call_gemini_with_timeout(user_prompt, timeout=gemini_timeout)
            if text and not text.startswith("ERROR"):
                logger.info(f"[LLM] Gemini ✓  domain={domain} level={level} target={target_word_str}")
                return text
            else:
                raise ValueError("Gemini returned invalid or empty text")
        except Exception as e:
            gemini_err = e
            logger.warning(f"[LLM] Gemini failed ({type(e).__name__}: {e}), immediately falling back to NIM.")
    else:
        logger.warning("[LLM] Chain timeout expired before Gemini could execute.")

    # ── 2. Fallback: NVIDIA NIM (meta/llama-4-maverick) ───────────────────
    nim_err = None
    elapsed = time.time() - start_time
    remaining_chain_time = CHAIN_TIMEOUT - elapsed
    nim_timeout = min(PROVIDER_TIMEOUT, remaining_chain_time)

    if nim_timeout > 0:
        try:
            text = _call_nim_with_timeout(user_prompt, timeout=nim_timeout)
            if text and not text.startswith("ERROR"):
                logger.info(f"[LLM] NIM fallback ✓  domain={domain} level={level} target={target_word_str}")
                return text
            else:
                raise ValueError("NIM returned invalid or empty text")
        except Exception as e:
            nim_err = e
            logger.error(f"[LLM] NIM fallback failed ({type(e).__name__}: {e}).")
    else:
        logger.warning("[LLM] Chain timeout expired before NIM could execute.")

    # ── 3. Both Providers Failed -> HTTP 503 ───────────────────────────────────
    logger.error(f"[LLM] Both LLM providers failed. Gemini: {gemini_err}, NIM: {nim_err}")
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=OVERLOAD_MESSAGE
    )


# ─── Ratio validator ─────────────────────────────────────────────────────────

def calculate_unknown_ratio(text: str, known_word_lemmas: List[str]) -> float:
    words = re.findall(r'\b\w+\b', text.lower())
    if not words:
        return 0.0
    known = set(w.lower() for w in known_word_lemmas)
    unknown = sum(1 for w in words if w not in known)
    return unknown / len(words)


# ─── Main entry point ────────────────────────────────────────────────────────

def validate_and_generate(
    anchor_lemmas: List[str],
    target_lemma: Union[str, Dict[str, Any]],
    all_known_lemmas: List[str],
    domain: str = "CORE",
    level: str = "A2",
    max_retries: int = 1,
) -> Tuple[str, bool, float]:
    """
    Generate text and validate the ~95% comprehensibility criterion.
    max_retries=1 keeps API usage low during onboarding (3 sequential calls).
    """
    last_text = ""
    last_ratio = 1.0

    for attempt in range(max_retries):
        try:
            text = generate_reading_text(anchor_lemmas, target_lemma, domain=domain, level=level)
        except HTTPException:
            # Let HTTP 503 pass through cleanly to API callers
            raise
        except Exception as e:
            logger.error(f"[LLM] Unexpected error during validate_and_generate: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=OVERLOAD_MESSAGE
            )

        if text.startswith("ERROR"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=OVERLOAD_MESSAGE
            )

        last_text = text
        ratio = calculate_unknown_ratio(text, all_known_lemmas)
        last_ratio = ratio

        if ratio <= 0.40:
            return text, True, ratio

    if last_text:
        return last_text, False, last_ratio

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=OVERLOAD_MESSAGE
    )
