"""
core/ai_engine.py
=================
All Gemini API calls for AI-powered features.
Migrated from Amazon Bedrock to Google Gemini API.

Models used:
    Fast  : gemini-3.5-flash  (free, simple tasks)
    Smart : gemini-3.1-pro    (free tier, analysis)
    Best  : gemini-3.1-pro    (deep portfolio work)
"""

import google.generativeai as genai
from google.generativeai.types import (
    HarmCategory, HarmBlockThreshold
)
import json
import time
import logging
from utils.logger import get_logger

log = get_logger(__name__)


# ── MODEL CONSTANTS ──────────────────────────────────────────

MODEL_FAST  = "gemini-3.5-flash"
MODEL_SMART = "gemini-3.1-pro"
MODEL_BEST  = "gemini-3.1-pro"


# ── API KEY MANAGEMENT ───────────────────────────────────────

_gemini_configured: bool = False

def _get_api_key() -> str | None:
    """
    Load Gemini API key from database app_config.
    Key stored under: "gemini_api_key"
    Encrypted using core.encryption (same as NewsAPI key).
    Returns None if not configured.
    """
    try:
        from core.database import get_config
        from core.encryption import decrypt
        encrypted = get_config("gemini_api_key")
        if encrypted:
            return decrypt(encrypted)
    except Exception as e:
        log.warning("Could not load Gemini API key: %s", e)
    return None

def _ensure_configured() -> bool:
    """
    Configure genai with API key if not already done.
    Returns True if configured successfully, False otherwise.
    """
    global _gemini_configured
    if _gemini_configured:
        return True
    key = _get_api_key()
    if not key:
        log.warning("Gemini API key not configured.")
        return False
    genai.configure(api_key=key)
    _gemini_configured = True
    log.info("Gemini API configured successfully.")
    return True

def store_gemini_api_key(api_key: str) -> None:
    """
    Encrypt and store Gemini API key in database.
    Called from ui/ai_settings_panel.py when user saves key.
    """
    from core.database import set_config
    from core.encryption import encrypt
    set_config("gemini_api_key", encrypt(api_key))
    global _gemini_configured
    _gemini_configured = False  # Force re-init with new key
    log.info("Gemini API key saved successfully.")

def get_gemini_api_key_status() -> str:
    """
    Returns human readable status of API key configuration.
    Used by ui/ai_settings_panel.py to show status.
    """
    key = _get_api_key()
    if not key:
        return "not_configured"
    if len(key) < 10:
        return "invalid"
    return "configured"


# ── SAFETY SETTINGS HELPER ───────────────────────────────────

def _safety_settings() -> dict:
    """
    Returns safety settings that allow financial content.
    Gemini sometimes blocks trading/stock content as 
    dangerous — these settings prevent that.
    """
    return {
        HarmCategory.HARM_CATEGORY_HARASSMENT:
            HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH:
            HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT:
            HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT:
            HarmBlockThreshold.BLOCK_NONE,
    }


# ── CORE CALL FUNCTION ───────────────────────────────────────

def call_gemini(
    prompt: str,
    system: str = "",
    max_tokens: int = 1000,
    model: str = MODEL_SMART,
    temperature: float = 0.3,
) -> str:
    """
    Core function for all Gemini API calls.
    Replaces the old call_claude() function.
    call_claude() is kept as an alias for compatibility.

    Parameters
    ----------
    prompt      : User message / question
    system      : System instruction for the model
    max_tokens  : Maximum output tokens (default 1000)
    model       : Model ID string (use MODEL_* constants)
    temperature : 0.0-1.0, lower = more factual (default 0.3)

    Returns
    -------
    Response text string.

    Raises
    ------
    AIEngineError on failure after retries.
    """
    if not _ensure_configured():
        raise AIEngineError(
            "Gemini API key not configured. "
            "Go to AI Settings panel to add your key."
        )

    last_error = None
    for attempt in range(3):
        try:
            gemini_model = genai.GenerativeModel(
                model_name=model,
                system_instruction=system if system else None,
            )
            response = gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                ),
                safety_settings=_safety_settings(),
            )
            
            # Handle blocked responses
            if not response.candidates:
                raise AIEngineError(
                    "Gemini returned no candidates. "
                    "Response may have been blocked."
                )
            
            # Handle empty text
            text = response.text
            if not text or not text.strip():
                raise AIEngineError(
                    "Gemini returned empty response."
                )
            
            log.debug(
                "Gemini call successful. Model: %s, "
                "Tokens approx: %d",
                model, len(prompt.split()) + len(text.split())
            )
            return text

        except AIEngineError:
            raise
        except Exception as exc:
            last_error = exc
            log.warning(
                "Gemini attempt %d/3 failed: %s",
                attempt + 1, exc
            )
            if attempt < 2:
                time.sleep(2 ** attempt)  # 1s, 2s backoff

    raise AIEngineError(
        f"Gemini API failed after 3 attempts: {last_error}"
    )

# Alias for backward compatibility with existing code
def call_claude(prompt, system="", max_tokens=1000,
                model=MODEL_SMART) -> str:
    """Alias for call_gemini() — backward compatibility."""
    return call_gemini(prompt, system, max_tokens, model)


# ── MODEL INFO ───────────────────────────────────────────────

def get_model_info() -> dict:
    """Returns metadata about each model tier for UI display."""
    return {
        "fast": {
            "id": MODEL_FAST,
            "name": "Gemini 3.5 Flash",
            "tier": "Fast",
            "use_case": "Simple parsing, sentiment analysis",
            "cost": "Free tier — 15 req/min",
            "color": "WARN",
        },
        "smart": {
            "id": MODEL_SMART,
            "name": "Gemini 3.1 Pro",
            "tier": "Smart",
            "use_case": "Technical analysis, GTT suggestions",
            "cost": "Free tier — 2 req/min",
            "color": "SUCCESS",
        },
        "best": {
            "id": MODEL_BEST,
            "name": "Gemini 3.1 Pro",
            "tier": "Best",
            "use_case": "Deep portfolio analysis",
            "cost": "Free tier — 2 req/min",
            "color": "ACCENT_LIGHT",
        },
    }

def estimate_cost(function_name: str) -> str:
    """Returns cost estimate string for UI display."""
    estimates = {
        "analyze_stock":            ("Gemini 3.1 Pro",   "Free"),
        "suggest_exit_strategy":    ("Gemini 3.1 Pro",   "Free"),
        "analyze_sentiment":        ("Gemini 3.5 Flash", "Free"),
        "generate_portfolio_report":("Gemini 3.1 Pro",   "Free"),
        "parse_natural_language":   ("Gemini 3.5 Flash", "Free"),
    }
    model, cost = estimates.get(
        function_name, ("Gemini 3.1 Pro", "Free")
    )
    return f"{model} · {cost}"


# ── GET MODEL FOR FUNCTION ────────────────────────────────────

def get_model_for_function(
    function_name: str,
    state=None
) -> str:
    """
    Returns actual model ID for a given function.
    Checks AppState override first, falls back to defaults.
    """
    MODEL_MAP = {
        "fast":  MODEL_FAST,
        "smart": MODEL_SMART,
        "best":  MODEL_BEST,
    }
    DEFAULT_TIERS = {
        "analyze_stock":  "smart",
        "suggest_exit":   "smart",
        "sentiment":      "fast",
        "portfolio":      "best",
        "nlp_parse":      "fast",
    }
    if state is not None:
        attr = f"ai_model_{function_name}"
        tier = getattr(state, attr, None)
        if tier and tier in MODEL_MAP:
            return MODEL_MAP[tier]
    tier = DEFAULT_TIERS.get(function_name, "smart")
    return MODEL_MAP[tier]


# ── AI FUNCTIONS (keep all signatures identical) ─────────────

def analyze_stock(
    stock_code: str,
    indicators: dict,
    client_name: str = "",
    state=None,
) -> str:
    """
    Full technical analysis for a stock.
    Uses MODEL_SMART (Gemini 3.1 Pro).
    """
    model = get_model_for_function("analyze_stock", state)
    
    system = """You are a senior technical analyst for Indian 
equity markets (NSE/BSE). Analyze the provided technical 
indicators and give a clear, structured analysis. Be specific 
with price levels. Use Indian market context. 
Keep response under 400 words. Use plain text only, 
no markdown symbols like ** or ##."""

    prompt = f"""Analyze this stock for GTT exit strategy planning:

Stock: {stock_code}
Exchange: NSE

PRICE CONTEXT:
Current Price: ₹{indicators.get('Current_price', 'N/A')}
52W High: ₹{indicators.get('High_52w', 'N/A')}
52W Low: ₹{indicators.get('Low_52w', 'N/A')}
% from 52W High: {indicators.get('Price_from_52w_high', 'N/A')}%
Support Level: ₹{indicators.get('Support_level', 'N/A')}
Resistance Level: ₹{indicators.get('Resistance_level', 'N/A')}

MOMENTUM:
RSI (14): {indicators.get('RSI_14', 'N/A')}
MACD Line: {indicators.get('MACD_line', 'N/A')}
MACD Signal: {indicators.get('MACD_signal', 'N/A')}
MACD Histogram: {indicators.get('MACD_hist', 'N/A')}

TREND:
EMA 20: ₹{indicators.get('EMA_20', 'N/A')}
EMA 50: ₹{indicators.get('EMA_50', 'N/A')}
SMA 200: ₹{indicators.get('SMA_200', 'N/A')}

VOLATILITY:
ATR (14): ₹{indicators.get('ATR_14', 'N/A')}
Bollinger Upper: ₹{indicators.get('BB_upper', 'N/A')}
Bollinger Lower: ₹{indicators.get('BB_lower', 'N/A')}
BB Width: {indicators.get('BB_width', 'N/A')}%

VOLUME:
Volume SMA 20: {indicators.get('Volume_SMA_20', 'N/A')}
Volume Ratio: {indicators.get('Volume_ratio', 'N/A')}

Please provide:
1. Overall market structure (Bullish / Bearish / Sideways)
2. Key support and resistance levels to watch
3. RSI and momentum interpretation
4. Volatility assessment
5. Recommended action: Hold / Scale-out / Accumulate
6. Key risk factors to monitor"""

    try:
        result = call_gemini(prompt, system,
                             max_tokens=600, model=model)
        log.info("Stock analysis complete for %s", stock_code)
        return result
    except AIEngineError as e:
        log.error("analyze_stock failed: %s", e)
        raise

def suggest_exit_strategy(
    stock_code: str,
    indicators: dict,
    free_qty: int,
    math_suggestion: dict,
    state=None,
) -> str:
    """
    Explain the suggested GTT exit strategy in plain language.
    Uses MODEL_SMART (Gemini 3.1 Pro).
    """
    model = get_model_for_function("suggest_exit", state)

    system = """You are an expert in GTT order strategies for 
Indian equity markets. Explain exit strategy suggestions in 
clear, simple language a retail investor understands. 
Under 300 words. Plain text only, no markdown."""

    prompt = f"""Explain this GTT staggered exit strategy:

Stock: {stock_code}
Current Price: ₹{indicators.get('Current_price', 'N/A')}
Free Quantity: {free_qty} shares
RSI: {indicators.get('RSI_14', 'N/A')}
ATR: ₹{indicators.get('ATR_14', 'N/A')}
Support: ₹{indicators.get('Support_level', 'N/A')}
Resistance: ₹{indicators.get('Resistance_level', 'N/A')}

Suggested GTT Plan:
  Base Trigger Price: ₹{math_suggestion.get('base_trigger')}
  Price Gap per Batch: ₹{math_suggestion.get('price_gap')}
  Batch Size: {math_suggestion.get('batch_size')} shares
  Number of Batches: {math_suggestion.get('num_batches')}
  Price Range: ₹{math_suggestion.get('price_range_low')} 
               to ₹{math_suggestion.get('price_range_high')}

Explain:
1. Why these specific price levels were chosen
2. What market conditions support this exit plan
3. What would invalidate this strategy
4. One-line risk warning for the investor"""

    try:
        result = call_gemini(prompt, system,
                             max_tokens=400, model=model)
        log.info("Exit strategy explanation done for %s",
                 stock_code)
        return result
    except AIEngineError as e:
        log.error("suggest_exit_strategy failed: %s", e)
        raise

def analyze_sentiment(
    stock_code: str,
    headlines: list[str],
    state=None,
) -> dict:
    """
    Analyze news sentiment for a stock.
    Uses MODEL_FAST (Gemini 3.5 Flash) — simple task.
    Returns dict with score, label, summary, etc.
    """
    model = get_model_for_function("sentiment", state)

    system = """You are a financial news analyst specializing 
in Indian equity markets. Analyze headlines and return ONLY 
valid JSON. No markdown, no explanation, just the JSON object."""

    headlines_text = "\n".join(
        f"{i+1}. {h}" for i, h in enumerate(headlines)
    )

    prompt = f"""Analyze sentiment for {stock_code} stock 
based on these headlines:

{headlines_text}

Return ONLY this JSON structure (no markdown, no backticks):
{{
    "score": <integer 1-10, where 10 is most bullish>,
    "label": "<Bullish or Neutral or Bearish>",
    "summary": "<2-3 sentence summary of overall sentiment>",
    "key_positives": ["<positive point 1>", "<positive point 2>"],
    "key_risks": ["<risk point 1>", "<risk point 2>"],
    "recommendation": "<one sentence recommendation>"
}}"""

    _DEFAULT = {
        "score": 5,
        "label": "Neutral",
        "summary": "Unable to analyze sentiment at this time.",
        "key_positives": ["Analysis unavailable"],
        "key_risks": ["Analysis unavailable"],
        "recommendation": "Consult a financial advisor.",
    }

    try:
        raw = call_gemini(prompt, system,
                          max_tokens=400, model=model,
                          temperature=0.1)
        # Strip any accidental markdown fences
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()
        result = json.loads(clean)
        log.info("Sentiment analysis done for %s", stock_code)
        return result
    except (json.JSONDecodeError, Exception) as e:
        log.error("analyze_sentiment failed: %s", e)
        return _DEFAULT

def generate_portfolio_report(
    holdings: list[dict],
    analyses: list[dict],
    state=None,
) -> str:
    """
    Generate overall portfolio health summary.
    Uses MODEL_BEST (Gemini 3.1 Pro).
    """
    model = get_model_for_function("portfolio", state)

    system = """You are a senior portfolio manager for Indian 
retail investors. Generate clear, actionable portfolio 
assessments. Under 500 words. Plain text only."""

    holdings_summary = "\n".join([
        f"  {h.get('stock_code')}: "
        f"{h.get('free_qty')} shares"
        for h in holdings
    ])

    analyses_summary = "\n".join([
        f"  {a.get('stock_code')}: "
        f"RSI={a.get('RSI_14','N/A')}, "
        f"Sentiment={a.get('sentiment_label','N/A')}"
        for a in analyses
    ])

    prompt = f"""Generate a portfolio health report:

HOLDINGS:
{holdings_summary}

STOCK ANALYSES:
{analyses_summary}

Provide:
1. Overall portfolio health assessment
2. Concentration risk — any stock too dominant?
3. Stocks needing immediate attention (high RSI, bad sentiment)
4. Stocks with no exit strategy configured yet
5. Top 3 recommended actions this week
6. Overall market exposure rating (Conservative/Moderate/Aggressive)"""

    try:
        result = call_gemini(prompt, system,
                             max_tokens=700, model=model)
        log.info("Portfolio report generated for %d holdings",
                 len(holdings))
        return result
    except AIEngineError as e:
        log.error("generate_portfolio_report failed: %s", e)
        raise

def parse_natural_language_config(
    user_text: str,
    stock_code: str,
    current_price: float,
    free_qty: int,
    state=None,
) -> dict:
    """
    Parse plain English GTT instructions into config values.
    Uses MODEL_FAST (Gemini 3.5 Flash) — simple extraction.
    
    Example input:
    "Sell my Reliance in 20 batches starting at 2900 
     going up by 25 rupees"
    
    Returns dict with extracted config values.
    """
    model = get_model_for_function("nlp_parse", state)

    system = """Extract GTT order parameters from text. 
Return ONLY valid JSON. No markdown, no explanation."""

    prompt = f"""Extract GTT order parameters from this text:

User said: "{user_text}"

Context:
  Stock: {stock_code}
  Current Price: ₹{current_price}
  Available Shares: {free_qty}

Return ONLY this JSON (use null for values not mentioned):
{{
    "total_shares": <integer or null>,
    "batch_size": <integer or null>,
    "base_trigger": <float or null>,
    "price_gap": <float or null>,
    "limit_offset": <float or null>,
    "confidence": "<high or medium or low>",
    "interpretation": "<one sentence: what you understood>"
}}"""

    _DEFAULT = {
        "total_shares": None,
        "batch_size": None,
        "base_trigger": None,
        "price_gap": None,
        "limit_offset": None,
        "confidence": "low",
        "interpretation": "Could not parse instruction clearly.",
    }

    try:
        raw = call_gemini(prompt, system,
                          max_tokens=200, model=model,
                          temperature=0.1)
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()
        result = json.loads(clean)
        log.info("NLP parse complete. Confidence: %s",
                 result.get("confidence"))
        return result
    except Exception as e:
        log.error("parse_natural_language_config failed: %s", e)
        return _DEFAULT

def test_connection() -> tuple[bool, str]:
    """
    Test Gemini API connectivity.
    Called from AI Settings panel Test button.
    Returns (success: bool, message: str)
    """
    try:
        response = call_gemini(
            prompt="Reply with exactly: OK",
            model=MODEL_FAST,
            max_tokens=10,
            temperature=0.0,
        )
        if "OK" in response.upper():
            return True, "Connected — Gemini 3.5 Flash responding"
        return True, f"Connected — Response: {response[:50]}"
    except AIEngineError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"


# ── EXCEPTION CLASS ──────────────────────────────────────────

class AIEngineError(Exception):
    """Raised for all Gemini API errors."""
