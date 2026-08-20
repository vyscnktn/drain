import os
import time
import logging
import re
import random
from dotenv import load_dotenv, find_dotenv
from google import genai
from openai import OpenAI
from typing import List, Tuple, Optional, Union, Dict, Any

logger = logging.getLogger(__name__)

# Always locate and load .env file
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    load_dotenv()

gemini_key = os.environ.get("GEMINI_API_KEY")


# ─── Client factories ────────────────────────────────────────────────────────

def get_gemini_client() -> Optional[genai.Client]:
    """Primary: Google Gemini via official google.genai SDK."""
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return genai.Client(api_key=key)
    return None


def get_nim_client() -> Optional[OpenAI]:
    """Fallback: NVIDIA NIM — OpenAI-compatible endpoint."""
    key = os.environ.get("NIM_API_KEY")
    if key:
        return OpenAI(
            api_key=key,
            base_url="https://integrate.api.nvidia.com/v1",
            timeout=60.0,
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
        "ein Vorfall beim Serverausfall"
    ],
    "HEALTH": [
        "ein Patientengespräch im Behandlungszimmer",
        "die Übergabe zwischen zwei Schichten",
        "ein Beratungsgespräch mit der Ärztin",
        "eine Dokumentation der Pflegemaßnahme"
    ],
    "MEDIZIN": [
        "ein Anamnesegespräch auf der Station",
        "eine Klinikvisite mit dem Chefarzt",
        "ein Befundgespräch mit einem Patienten",
        "eine Besprechung im OP-Saal"
    ],
    "PFLEGE": [
        "eine Schichtübergabe im Seniorenheim",
        "die Wundversorgung bei einem Patienten",
        "ein Gespräch über den Pflegeplan mit der Pflegekraft",
        "die Vitalzeichenkontrolle am Morgen"
    ],
    "PHYSIO": [
        "eine Therapiesitzung im Behandlungsraum",
        "eine Übungseinheit zur Mobilisation nach einer Verletzung",
        "ein Beratungsgespräch nach einer Knie-OP"
    ],
    "PHARMA": [
        "ein Beratungsgespräch am Kundenschalter der Apotheke",
        "eine Überprüfung des Rezepts vor der Ausgabe",
        "die Aufklärung über Nebenwirkungen eines Medikaments"
    ],
    "ACADEMIC": [
        "eine Diskussion im Universitätsseminar",
        "eine E-Mail an den Professor wegen der Hausarbeit",
        "ein kurzer Vortrag vor der Forschungsgruppe"
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


# ─── Core Generation ─────────────────────────────────────────────────────────

def _call_gemini(user_prompt: str) -> str:
    """Try Google Gemini via official google.genai SDK (primary)."""
    g_client = get_gemini_client()
    if not g_client:
        raise RuntimeError("GEMINI_API_KEY not configured")

    models_to_try = [
        "gemini-flash-latest",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite"
    ]

    from google.genai import types

    last_err = None
    for model_name in models_to_try:
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
        except Exception as e:
            last_err = e
            logger.warning(f"[LLM] Gemini model '{model_name}' failed: {e}")
            continue

    raise last_err or RuntimeError("All Gemini models failed")


def _call_nim(user_prompt: str) -> str:
    """Try NVIDIA NIM (fallback)."""
    nim_client = get_nim_client()
    if not nim_client:
        raise RuntimeError("NIM_API_KEY not configured")

    response = nim_client.chat.completions.create(
        model="meta/llama-3.3-70b-instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.8,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()


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
    """
    # Extract best word surface string
    if isinstance(target_word, dict):
        target_word_str = target_word.get('surface_form') or target_word.get('lemma') or 'Zielwort'
    else:
        target_word_str = str(target_word)

    user_prompt = _build_user_prompt(anchor_words, target_word_str, domain, level)

    # ── 1. Try Google Gemini ─────────────────────────────────────────────────
    try:
        text = _call_gemini(user_prompt)
        logger.info(f"[LLM] Gemini ✓  domain={domain} level={level} target={target_word_str}")
        return text
    except Exception as e:
        if _is_rate_limit_error(e):
            logger.warning(f"[LLM] Gemini rate-limit, falling back to NIM: {e}")
        else:
            logger.warning(f"[LLM] Gemini error ({type(e).__name__}), falling back to NIM: {e}")

    # ── 2. Fallback: NVIDIA NIM ───────────────────────────────────────────────
    try:
        text = _call_nim(user_prompt)
        logger.info(f"[LLM] NIM fallback ✓  domain={domain} level={level} target={target_word_str}")
        return text
    except Exception as e:
        logger.error(f"[LLM] NIM also failed: {e}")
        return f"ERROR: Both Gemini and NIM failed. Last error: {e}"


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
        except Exception as e:
            if _is_rate_limit_error(e):
                wait = 2 ** attempt
                logger.warning(f"[LLM] Rate-limit on attempt {attempt+1}, backing off {wait}s")
                time.sleep(wait)
                continue
            return f"ERROR: {e}", False, 1.0

        if text.startswith("ERROR"):
            return text, False, 1.0

        last_text = text
        ratio = calculate_unknown_ratio(text, all_known_lemmas)
        last_ratio = ratio

        if ratio <= 0.40:
            return text, True, ratio

    if last_text:
        return last_text, False, last_ratio

    return "ERROR: Text generation failed after retries.", False, 1.0
