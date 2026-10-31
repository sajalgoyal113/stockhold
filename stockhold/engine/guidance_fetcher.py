#!/usr/bin/env python3
"""guidance_fetcher.py - Management guidance & delivery track record from concall transcripts.

Pipeline (all public sources, no manual input):
1. Concall list from the Screener company page (data_fetcher.fetch_company_data -> "concalls").
2. Transcript PDFs (BSE links) downloaded and converted to text with pypdf; text is
   cached under predict/data/transcripts/<TICKER>/ (git-ignored).
3. Forward-looking guidance extracted per call: revenue growth %, revenue target (Rs Cr),
   EBITDA margin %, PAT margin %, PAT growth %, each with the fiscal year it refers to and the
   verbatim quote.
   - GEMINI_API_KEY set  -> Gemini extracts; every quote is verified against the transcript
     text (an unverifiable quote is dropped, so the model cannot invent guidance).
   - No key              -> conservative rule-based extractor (forward-looking cue + metric +
     number + future period). Lower confidence, discounted in the reliability score.
4. Track record: guidance for fiscal years that have since been reported is compared with
   Screener actuals (delivered / guided). Reliability is shrunk toward a 0.75 prior when
   there are few observations, so one good year cannot earn full credibility.
5. Current guidance (calls in the last 200 days, periods not yet reported) becomes a guided
   revenue CAGR and/or a guided PAT margin, which forward_growth_pe.calibrate_first_principles
   discounts by reliability.

CLI:
  python3 guidance_fetcher.py KAYNES DIXON            # print, do not persist
  python3 guidance_fetcher.py --portfolio --write     # all portfolio tickers -> guidance_registry.json
"""

import os
import re
import sys
import json
import time
import argparse
from datetime import datetime

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

_DATA_DIR_CANDIDATES = [
    os.path.join(os.path.dirname(_SCRIPT_DIR), "data"),
    os.path.join(os.path.dirname(os.path.dirname(_SCRIPT_DIR)), "predict", "data"),
]
DATA_DIR = next((d for d in _DATA_DIR_CANDIDATES if os.path.isdir(d)), _DATA_DIR_CANDIDATES[0])
REGISTRY_PATH = os.path.join(DATA_DIR, "guidance_registry.json")
TRANSCRIPT_DIR = os.path.join(DATA_DIR, "transcripts")

MAX_CALLS = 4                 # ~1 year of quarterly calls (fast, responsive concall parsing)
FRESH_DAYS = 200              # guidance older than this is not "current"
PRIOR_RELIABILITY = 0.75      # shrinkage prior for delivery ratio
PRIOR_WEIGHT = 2.0            # pseudo-observations behind the prior
REGEX_CONFIDENCE = 0.90       # rule-based extraction is discounted vs LLM extraction

_MEM_CACHE = {}

MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug",
                                      "sep", "oct", "nov", "dec"], start=1)}


# ----------------------------------------------------------------------------- helpers
def gemini_api_key():
    """GEMINI_API_KEY from the environment, else a Streamlit secrets file (user-level
    ~/.streamlit/secrets.toml or the project's git-ignored .streamlit/secrets.toml). Never logged."""
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key.strip()
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            return str(st.secrets["GEMINI_API_KEY"]).strip()
    except Exception:
        pass
    root = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
    for p in (os.path.expanduser("~/.streamlit/secrets.toml"),
              os.path.join(root, ".streamlit", "secrets.toml"),
              os.path.join(root, "stockhold", ".streamlit", "secrets.toml")):
        try:
            import tomllib
            with open(p, "rb") as f:
                val = tomllib.load(f).get("GEMINI_API_KEY")
            if val:
                return str(val).strip()
        except (OSError, ValueError, ImportError):
            continue
    return None


def _parse_call_date(label):
    """'Aug 2026' -> datetime(2026, 8, 15)."""
    try:
        mon, yr = str(label).strip().split()[:2]
        return datetime(int(yr), MONTHS[mon[:3].lower()], 15)
    except Exception:
        return None


def _fy_of(dt):
    """Indian fiscal year (ending March) containing dt, as a 4-digit year."""
    return dt.year + 1 if dt.month >= 4 else dt.year


def _num(s):
    return float(s.replace(",", ""))


def _session():
    try:
        from data_fetcher import _HTTP_SESSION
        return _HTTP_SESSION
    except Exception:
        import requests
        sess = requests.Session()
        sess.headers.update({"User-Agent": "Mozilla/5.0"})
        return sess


def fetch_transcript_text(ticker, call, timeout=20):
    """Download a transcript PDF and return its text (cached on disk). None on failure."""
    url = call.get("transcript")
    if not url:
        return None
    safe = re.sub(r"[^A-Za-z0-9]+", "_", call.get("date", "unknown"))
    cache_dir = os.path.join(TRANSCRIPT_DIR, ticker)
    cache_path = os.path.join(cache_dir, f"{safe}.txt")
    if os.path.isfile(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()
    try:
        import io
        import pypdf
        r = _session().get(url, timeout=timeout, headers={"Referer": "https://www.bseindia.com/"})
        if r.status_code != 200 or b"%PDF" not in r.content[:1024]:
            return None
        reader = pypdf.PdfReader(io.BytesIO(r.content))
        text = " ".join((p.extract_text() or "") for p in reader.pages)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 2000:
            return None
        try:
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError:
            pass  # read-only deployments: keep working without the disk cache
        return text
    except Exception:
        return None


# ------------------------------------------------------------------ rule-based extraction
_FUTURE = re.compile(
    r"\b(guid\w*|target\w*|we (?:expect|anticipate|aim|plan|intend|foresee|project|envisage|"
    r"are confident|are looking|are hopeful|should|would|will|believe we|see ourselves)|"
    r"expected to|should (?:be|grow|reach|achieve|deliver|cross|clock)|"
    r"will (?:be|grow|reach|achieve|deliver|cross|clock)|going forward|next (?:year|financial year|fiscal)|"
    r"outlook|aspir\w*|visibility)\b", re.I)
_PAST = re.compile(
    r"\b(stood at|was at|were at|reported|we grew|has grown|have grown|delivered|achieved|recorded|"
    r"registered|declined|compared to|as against|last year|in the quarter|this quarter|for the quarter|"
    r"during the quarter|y-?o-?y growth of)\b", re.I)
_PCT = r"(\d{1,3}(?:\.\d+)?)\s?(?:%|percent|per cent)?\s?(?:-|to|–)\s?(\d{1,3}(?:\.\d+)?)\s?(?:%|percent|per cent)|(\d{1,3}(?:\.\d+)?)\s?(?:%|percent|per cent)"
_AMT = r"(?:INR|Rs\.?|₹)?\s?(\d[\d,]*(?:\.\d+)?)\s?(?:crores?|cr\b)(?:\s?(?:-|to|–)\s?(?:INR|Rs\.?|₹)?\s?(\d[\d,]*(?:\.\d+)?)\s?(?:crores?|cr\b))?|(?:INR|Rs\.?|₹)\s?(\d[\d,]*(?:\.\d+)?)\s?(?:-|to|–)\s?(?:INR|Rs\.?|₹)?\s?(\d[\d,]*(?:\.\d+)?)\s?(?:crores?|cr\b)"
_FY = re.compile(r"\bFY\s?'?(\d{2}|20\d{2})\b|\bfinancial year\s?(20\d{2})\b|\b(20\d{2})\s?-\s?(\d{2})\b", re.I)
_EXCLUDE = re.compile(r"market share|utili[sz]ation|dividend|tax rate|interest|attrition|"
                      r"export(?:s)? share|of (?:our )?revenue (?:from|comes)|order book|order inflow|"
                      r"capex|working capital|debt|receivable|inventory|gross margin|stake|"
                      r"industry (?:is|will|growth)|market (?:is|will|size)|sector (?:is|will)", re.I)

_METRICS = [
    ("ebitda_margin", re.compile(r"ebitda margin", re.I), "pct"),
    ("pat_margin", re.compile(r"(?:pat|net profit|net) margin", re.I), "pct"),
    ("pat_growth", re.compile(r"\b(?:pat|net profit|bottom ?line|profit after tax)\b.{0,60}\bgrow", re.I), "pct"),
    ("revenue_growth", re.compile(r"\b(?:revenue|top ?line|sales|turnover)\b.{0,60}\bgrow|\bgrow\w*.{0,40}\b(?:revenue|top ?line|sales|turnover)\b", re.I), "pct"),
    ("revenue_target", re.compile(r"\b(?:revenue|top ?line|sales|turnover)\b", re.I), "amt"),
]


def _periods_in(sentence, call_fy):
    out = []
    for m in _FY.finditer(sentence):
        if m.group(1):
            v = int(m.group(1))
            out.append(v if v > 100 else 2000 + v)
        elif m.group(2):
            out.append(int(m.group(2)) + 1)  # "financial year 2026" ~ FY ending Mar 2027 is ambiguous; treat as FY27
        elif m.group(3) and m.group(4):
            out.append(2000 + int(m.group(4)))
    low = sentence.lower()
    if not out:
        if re.search(r"next (?:financial )?year|next fiscal", low):
            out.append(call_fy + 1)
        elif re.search(r"this (?:financial )?year|current (?:financial )?year|this fiscal", low):
            out.append(call_fy)
    return out


def _mid_pct(m):
    if m.group(1) and m.group(2):
        return (float(m.group(1)) + float(m.group(2))) / 2.0
    return float(m.group(3))


def _mid_amt(m):
    lo = m.group(1) or m.group(3)
    hi = m.group(2) or m.group(4)
    lo = _num(lo)
    return (lo + _num(hi)) / 2.0 if hi else lo


def extract_guidance_regex(text, call_dt):
    """Rule-based extraction. Returns items: metric, value, period_fy, quote, method."""
    call_fy = _fy_of(call_dt)
    items = []
    sents = re.split(r"(?<=[.?!])\s+", text)
    for idx, sent in enumerate(sents):
        if len(sent) > 450 or sent.rstrip().endswith("?") or _EXCLUDE.search(sent):
            continue
        # Q&A context: an answer like "We should do 30% to 35%." after a question about
        # revenue growth for FY27 inherits the question's metric and period.
        prev_q = next((p for p in reversed(sents[max(0, idx - 2):idx]) if p.rstrip().endswith("?")), "")
        if not _FUTURE.search(sent) and not (prev_q and re.search(r"\b(should|would|will|expect|pencil|guid)", prev_q, re.I)):
            continue
        if re.search(r"\b(we had guided|had guided|earlier guidance|we guided)\b", sent, re.I):
            continue  # a recollection of an old promise, not new guidance
        periods = _periods_in(sent, call_fy) or (_periods_in(prev_q, call_fy) if prev_q else [])
        future_periods = [p for p in periods if p >= call_fy]
        if _PAST.search(sent) and not future_periods:
            continue
        for metric, pat, kind in _METRICS:
            mm = pat.search(sent)
            tail = sent[mm.start(): mm.end() + 140] if mm else None
            if not mm and prev_q and pat.search(prev_q) and kind == "pct":
                tail = sent  # metric named in the question, number in the answer
            if tail is None:
                continue
            if kind == "pct":
                nm = re.search(_PCT, tail, re.I)
                if not nm:
                    continue
                val = _mid_pct(nm)
                lo, hi = (1.0, 60.0) if metric.endswith("margin") else (3.0, 100.0)
                if not (lo <= val <= hi):
                    continue
            else:
                nm = re.search(_AMT, tail, re.I)
                if not nm or not future_periods:
                    continue  # a revenue target without a target year is not usable
                val = _mid_amt(nm)
                if val < 10:
                    continue
            period = future_periods[0] if future_periods else call_fy
            items.append({"metric": metric, "value": round(val, 2), "period_fy": period,
                          "period_inferred": not future_periods,
                          "quote": sent.strip()[:400], "context": prev_q.strip()[:300] if prev_q else "",
                          "method": "regex"})
            break  # one metric per sentence
    return items


# ------------------------------------------------------------------------ LLM extraction
_LLM_PROMPT = """You extract FORWARD-LOOKING management guidance from an Indian listed company's earnings call transcript.
Call date: {call_date}. Indian fiscal years end in March (FY27 = Apr 2026 - Mar 2027).
Return ONLY a JSON list. Each element:
{{"metric": one of ["revenue_growth","revenue_target","ebitda_margin","pat_margin","pat_growth"],
  "value": number (percent for growth/margin as a number like 25 for 25%; Rs crore for revenue_target; midpoint of ranges),
  "period_fy": 4-digit fiscal year the guidance refers to (e.g. 2027),
  "quote": exact verbatim sentence from the transcript containing the guidance}}
Rules: only statements by management about the FUTURE of THIS company (not industry, not past results,
not analyst questions). Skip segment-only guidance unless it is the whole company. Skip any USD / foreign-currency
figure: never convert currencies. Include minimum/floor statements ("at least Rs 4,000 crore this year").
If none, return [].
TRANSCRIPT:
{text}"""


GEMINI_MODELS = ("gemini-3.5-flash", "gemini-3.5-flash-lite")  # fastest models that answered in tests (Oct 2026)
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def extract_guidance_llm(text, call_dt, api_key, timeout=90):
    """Gemini extraction over REST (the deprecated google.generativeai SDK can hang).
    Returns verified items, or None if every model fails (caller falls back to rules)."""
    import requests
    prompt = _LLM_PROMPT.format(call_date=call_dt.strftime("%b %Y"), text=text[:120000])
    payload = {"contents": [{"parts": [{"text": prompt}]}],
               "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
    norm_text = re.sub(r"\s+", " ", text).lower()
    for model in GEMINI_MODELS:
        try:
            r = requests.post(GEMINI_URL.format(model=model), headers={"x-goog-api-key": api_key.strip()},
                              json=payload, timeout=timeout)
            if r.status_code != 200:
                continue
            parts = r.json()["candidates"][0]["content"]["parts"]
            raw = "".join(p.get("text", "") for p in parts).strip()
            raw = raw[raw.find("["): raw.rfind("]") + 1] or "[]"
            out = []
            for it in json.loads(raw):
                q = re.sub(r"\s+", " ", str(it.get("quote", ""))).strip()
                # Anti-hallucination: the quote (first 80 chars) must exist verbatim in the transcript
                if len(q) < 20 or q[:80].lower() not in norm_text:
                    continue
                if it.get("metric") not in {m for m, _, _ in _METRICS}:
                    continue
                # Rupee revenue targets only: a model "converting" a USD figure is a fabrication
                if it["metric"] == "revenue_target" and re.search(r"\$|\bUSD\b|\bdollars?\b|\bbillion\b", q, re.I) \
                        and not re.search(r"crore|\bcr\b|INR|Rs\.?|₹", q, re.I):
                    continue
                out.append({"metric": it["metric"], "value": float(it["value"]), "period_fy": int(it["period_fy"]),
                            "period_inferred": False, "quote": q[:400], "method": "llm"})
            return out
        except Exception:
            continue
    return None


# ------------------------------------------------------------------------------ actuals
def annual_actuals(data):
    """FY -> {sales, opm, npm, pat} from the Screener P&L table (full fiscal years only)."""
    try:
        from data_fetcher import clean_num
    except Exception:
        clean_num = lambda x: float(re.sub(r"[^\d.-]", "", str(x)) or 0)
    heads = data.get("pl_headers") or []
    pl = data.get("pl_data") or {}
    sales, opm, pat = pl.get("Sales", []), pl.get("OPM %", []), pl.get("Net Profit", [])
    out = {}
    for i, h in enumerate(heads):
        m = re.match(r"([A-Za-z]{3})\s+(\d{4})", str(h).strip())
        if not m or i >= len(sales):
            continue
        fy = int(m.group(2))
        s = clean_num(sales[i])
        rec = {"sales": s}
        if i < len(opm):
            rec["opm"] = clean_num(opm[i])
        if i < len(pat):
            rec["pat"] = clean_num(pat[i])
            rec["npm"] = (rec["pat"] / s * 100) if s > 0 else None
        out[fy] = rec
    for fy in list(out):
        prev = out.get(fy - 1)
        if prev and prev["sales"] > 0:
            out[fy]["sales_growth"] = (out[fy]["sales"] / prev["sales"] - 1) * 100
        if prev and prev.get("pat", 0) > 0 and out[fy].get("pat") is not None:
            out[fy]["pat_growth"] = (out[fy]["pat"] / prev["pat"] - 1) * 100
    return out


def _actual_for(item, actuals):
    a = actuals.get(item["period_fy"])
    if not a:
        return None
    return {"revenue_growth": a.get("sales_growth"), "revenue_target": a.get("sales"),
            "ebitda_margin": a.get("opm"), "pat_margin": a.get("npm"),
            "pat_growth": a.get("pat_growth")}.get(item["metric"])


def _pat_margin_from_ebitda(ebitda_margin, data, tax_rate=0.25):
    """Guided EBITDA margin -> PAT margin using the company's latest reported cost structure:
    PAT margin = (EBITDA% - D&A% - interest% + other income%) x (1 - tax). None if rows missing."""
    pl = data.get("pl_data") or {}
    try:
        from data_fetcher import clean_num
    except Exception:
        clean_num = lambda x: float(re.sub(r"[^\d.-]", "", str(x)) or 0)
    def last(key):
        v = pl.get(key) or []
        return clean_num(v[-1]) if v else None
    sales, dep, intr, oth = last("Sales"), last("Depreciation"), last("Interest"), last("Other Income")
    if not sales or sales <= 0 or dep is None or intr is None:
        return None
    pbt_m = ebitda_margin - dep / sales - intr / sales + (oth or 0.0) / sales
    return round(max(0.0, pbt_m * (1 - tax_rate)), 4)


# ---------------------------------------------------------------------------- assembly
def build_guidance_entry(ticker, data=None, api_key=None, max_calls=MAX_CALLS, today=None, verbose=False):
    """Fetch transcripts, extract guidance, score the track record. Returns a registry entry
    (dict) or None if no transcripts are available."""
    ticker = ticker.upper()
    today = today or datetime.now()
    if data is None:
        data = _fetch_with_concalls(ticker)
    calls = [c for c in (data.get("concalls") or []) if c.get("transcript")][:max_calls]
    if not calls:
        return None
    api_key = api_key or gemini_api_key()
    by_call = collect_call_items(ticker, calls, api_key, verbose)
    return assemble_entry(ticker, data, by_call, today)


def collect_call_items(ticker, calls, api_key=None, verbose=False):
    """[(call_datetime, [items])] for calls whose transcript could be downloaded."""
    by_call = []
    for c in calls:
        cdt = _parse_call_date(c.get("date"))
        if not cdt:
            continue
        text = fetch_transcript_text(ticker, c)
        if not text:
            continue
        items = extract_guidance_llm(text, cdt, api_key) if api_key else None
        if items is None:
            items = extract_guidance_regex(text, cdt)
        for it in items:
            it["call_date"] = cdt.strftime("%Y-%m")
            it["source"] = c["transcript"]
        by_call.append((cdt, items))
        if verbose:
            print(f"   {ticker} {c.get('date')}: {len(items)} guidance items")
        time.sleep(0.4)
    return by_call


def assemble_entry(ticker, data, by_call, today=None):
    """Track record + current guidance from extracted items (any extraction method)."""
    today = today or datetime.now()
    if not by_call:
        return None
    actuals = annual_actuals(data)
    last_fy = max(actuals) if actuals else _fy_of(today) - 1

    # Track record: for each (metric, period) already reported, use the EARLIEST guidance made
    # before the period ended (the original promise), compare with the reported actual.
    promises = {}
    for cdt, items in sorted(by_call, key=lambda x: x[0]):
        for it in items:
            key = (it["metric"], it["period_fy"])
            period_end = datetime(it["period_fy"], 3, 31)
            if it["period_fy"] <= last_fy and cdt < period_end and key not in promises:
                promises[key] = it
    track = []
    for (metric, period), it in promises.items():
        actual = _actual_for(it, actuals)
        if actual is None or it["value"] <= 0:
            continue
        ratio = actual / it["value"]
        track.append({"metric": metric, "period_fy": period, "guided": it["value"],
                      "actual": round(actual, 2), "ratio": round(ratio, 3),
                      "call_date": it["call_date"], "quote": it["quote"], "method": it["method"]})
    n = len(track)
    methods = {t["method"] for t in track} | {it["method"] for _, its in by_call for it in its}
    conf = REGEX_CONFIDENCE if ("regex" in methods or not methods) else 1.0

    def _shrunk(rs):
        raw = (sum(min(1.05, max(0.0, r)) for r in rs) + PRIOR_RELIABILITY * PRIOR_WEIGHT) / (len(rs) + PRIOR_WEIGHT)
        return round(max(0.40, min(1.05, raw)) * conf, 3)
    # Growth guidance is judged ONLY on revenue/PAT delivery; beating a margin guide says
    # nothing about whether revenue promises are kept (and vice versa).
    growth_rs = [t["ratio"] for t in track if t["metric"] in ("revenue_growth", "revenue_target", "pat_growth")]
    margin_rs = [t["ratio"] for t in track if t["metric"] in ("ebitda_margin", "pat_margin")]
    reliability = _shrunk(growth_rs)
    margin_reliability = _shrunk(margin_rs)

    # Current guidance: fresh calls, periods not yet reported; latest call wins per (metric, period)
    current = {}
    for cdt, items in sorted(by_call, key=lambda x: x[0]):
        if (today - cdt).days > FRESH_DAYS:
            continue
        for it in items:
            if it["period_fy"] > last_fy:
                current[(it["metric"], it["period_fy"])] = it
    cur_items = list(current.values())

    base_sales = actuals.get(last_fy, {}).get("sales") or 0.0
    cagr_votes = []
    for it in cur_items:
        if it["metric"] == "revenue_growth":
            cagr_votes.append(it["value"])
        elif it["metric"] == "revenue_target" and base_sales > 0:
            yrs = it["period_fy"] - last_fy
            if yrs >= 1 and it["value"] > 0:
                cagr_votes.append(((it["value"] / base_sales) ** (1.0 / yrs) - 1) * 100)
    guided_rev_cagr = round(sorted(cagr_votes)[len(cagr_votes) // 2], 1) if cagr_votes else None
    if guided_rev_cagr is not None and not (-20.0 <= guided_rev_cagr <= 100.0):
        guided_rev_cagr = None  # implausible parse

    # PAT margin: explicit PAT-margin guidance, else EBITDA-margin guidance x historical PAT/EBITDA ratio
    guided_pat_margin = None
    pm = [it["value"] for it in cur_items if it["metric"] == "pat_margin"]
    em = [it["value"] for it in cur_items if it["metric"] == "ebitda_margin"]
    if pm:
        guided_pat_margin = round(sorted(pm)[len(pm) // 2] / 100.0, 4)
    elif em:
        guided_pat_margin = _pat_margin_from_ebitda(sorted(em)[len(em) // 2] / 100.0, data)

    return {
        "as_of": max(c for c, _ in by_call).strftime("%Y-%m-%d"),
        "fetched_at": today.strftime("%Y-%m-%d"),
        "method": "+".join(sorted(methods)) or "none",
        "guided_rev_cagr": guided_rev_cagr,
        "guided_pat_margin": guided_pat_margin,
        "reliability": reliability,
        "margin_reliability": margin_reliability,
        "track_record_n": len(growth_rs),
        "margin_track_record_n": len(margin_rs),
        "track_record": track,
        "current_guidance": cur_items,
        "calls_parsed": len(by_call),
        "sources": sorted({it["source"] for _, its in by_call for it in its})[:12],
        "notes": f"Auto-extracted from {len(by_call)} concall transcripts ({'+'.join(sorted(methods)) or 'no items'}); "
                 f"growth reliability {reliability} from {len(growth_rs)} revenue/PAT promises, margin reliability "
                 f"{margin_reliability} from {len(margin_rs)} (prior {PRIOR_RELIABILITY}, weight {PRIOR_WEIGHT}).",
    }


def _fetch_with_concalls(ticker, attempts=4):
    """fetch_company_data with backoff: a throttled Screener request falls back to the offline
    snapshot (no concall list), which would silently lose all guidance."""
    from data_fetcher import fetch_company_data
    try:
        import data_fetcher as _df
    except Exception:
        _df = None
    data = {}
    for i in range(attempts):
        data = fetch_company_data(ticker)
        if data.get("concalls"):
            return data
        if _df is not None and hasattr(_df, "_DATA_FETCHER_CACHE"):
            _df._DATA_FETCHER_CACHE.pop(ticker, None)  # do not keep serving the throttled fallback
        time.sleep(5 * (i + 1))
    return data


def load_registry(path=REGISTRY_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"_entries": {}}


def get_guidance(ticker, data=None, allow_network=True, max_age_days=120):
    """Registry entry if fresh, else fetch live (memory-cached; never written to disk here)."""
    t = (ticker or "").upper()
    reg = load_registry()
    entry = (reg.get("_entries") or {}).get(t) or reg.get(t)
    if entry and entry.get("fetched_at"):
        try:
            if (datetime.now() - datetime.strptime(entry["fetched_at"], "%Y-%m-%d")).days <= max_age_days:
                return entry
        except ValueError:
            pass
    elif entry and not entry.get("fetched_at"):
        return entry  # manual entry: always honoured
    if t in _MEM_CACHE:
        return _MEM_CACHE[t]
    if not allow_network or os.environ.get("STOCKS_NO_GUIDANCE_FETCH") == "1":
        return entry
    try:
        live = build_guidance_entry(t, data=data)
        if live and (live.get("guided_rev_cagr") is not None or live.get("guided_pat_margin") is not None):
            try:
                write_entries({t: live})
            except Exception:
                pass
    except Exception:
        live = None
    _MEM_CACHE[t] = live or entry
    return _MEM_CACHE[t]


def write_entries(entries, path=REGISTRY_PATH):
    reg = load_registry(path)
    reg.setdefault("_entries", {})
    reg["_entries"].update(entries)
    reg["_as_of"] = datetime.now().strftime("%Y-%m-%d")
    reg["_schema"] = ("guidance_registry v2: _entries[TICKER] = auto-extracted concall guidance "
                      "(guided_rev_cagr %, guided_pat_margin fraction, reliability, track_record, sources) "
                      "or a manual override with base_cagr/bull_cagr/exit fields + source + as_of.")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=1, ensure_ascii=False)


def import_extracted(ticker, items, data=None, method="llm-reviewed", today=None):
    """Build an entry from externally extracted items [{call:'Mon YYYY', metric, value, period_fy, quote}].
    Every quote is re-verified verbatim against the cached transcript of that call; items whose
    quote is not found are dropped. Returns (entry, n_dropped)."""
    t = ticker.upper()
    if data is None:
        data = _fetch_with_concalls(t)
    calls = {}
    for c in (data.get("concalls") or []):
        if c.get("transcript") and c.get("date") not in calls:
            calls[c.get("date")] = c
    norm = lambda x: re.sub(r"\s+", " ", str(x)).strip().lower()
    grouped, dropped = {}, 0
    for it in items:
        call = calls.get(it.get("call"))
        cdt = _parse_call_date(it.get("call"))
        text = fetch_transcript_text(t, call) if call else None
        if not (call and cdt and text) or norm(it.get("quote"))[:200] not in norm(text):
            dropped += 1
            continue
        grouped.setdefault(cdt, []).append({
            "metric": it["metric"], "value": float(it["value"]), "period_fy": int(it["period_fy"]),
            "period_inferred": False, "quote": str(it["quote"])[:400], "method": method,
            "call_date": cdt.strftime("%Y-%m"), "source": call.get("transcript")})
    by_call = sorted(grouped.items())
    # Calls that were parsed but had no guidance still count as parsed calls
    entry = assemble_entry(t, data, by_call, today) if by_call else None
    if entry is None:
        # Reviewed and found no company-level numeric guidance: record that explicitly so the
        # engine does not fall back to the noisier rule-based extractor for this ticker.
        today = today or datetime.now()
        entry = {"as_of": today.strftime("%Y-%m-%d"), "fetched_at": today.strftime("%Y-%m-%d"),
                 "method": method, "guided_rev_cagr": None, "guided_pat_margin": None,
                 "reliability": None, "track_record_n": 0, "track_record": [], "current_guidance": [],
                 "calls_parsed": len([c for c in calls.values() if c.get("transcript")][:MAX_CALLS]),
                 "sources": [], "notes": "Transcripts reviewed: no quantitative company-level guidance found."}
    return entry, dropped


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Fetch management guidance & track record from concall transcripts")
    ap.add_argument("tickers", nargs="*")
    ap.add_argument("--portfolio", action="store_true", help="All tickers in build_portfolio_report.STOCKS_DATA")
    ap.add_argument("--write", action="store_true", help="Persist to predict/data/guidance_registry.json")
    ap.add_argument("--import-extracted", metavar="DIR", help="Import reviewed <TICKER>.json item files instead of extracting")
    args = ap.parse_args()
    if args.import_extracted:
        results = {}
        for fn in sorted(os.listdir(args.import_extracted)):
            if not fn.endswith(".json"):
                continue
            t = fn[:-5].upper()
            items = json.load(open(os.path.join(args.import_extracted, fn)))
            e, dropped = import_extracted(t, items)
            print(f"[*] {t}: {len(items)} items, {dropped} dropped (quote not verified)")
            if e:
                results[t] = e
                print(f"   guided revenue CAGR: {e['guided_rev_cagr']}  guided PAT margin: {e['guided_pat_margin']}  "
                      f"reliability: {e['reliability']} (n={e['track_record_n']})")
                for tr in e["track_record"]:
                    print(f"     promise {tr['metric']} FY{tr['period_fy'] % 100}: guided {tr['guided']} -> actual {tr['actual']} (x{tr['ratio']})")
        if args.write and results:
            write_entries(results)
            print(f"[+] wrote {len(results)} entries to {REGISTRY_PATH}")
        sys.exit(0)
    tickers = [t.upper() for t in args.tickers]
    if args.portfolio:
        from build_portfolio_report import STOCKS_DATA
        tickers += [s["ticker"] for s in STOCKS_DATA]
    results = {}
    for t in dict.fromkeys(tickers):
        print(f"[*] {t}")
        try:
            e = build_guidance_entry(t, verbose=True)
        except Exception as ex:
            print(f"   failed: {ex}")
            continue
        if not e:
            print("   no transcripts available")
            continue
        results[t] = e
        print(f"   guided revenue CAGR: {e['guided_rev_cagr']}  guided PAT margin: {e['guided_pat_margin']}  "
              f"reliability: {e['reliability']} (n={e['track_record_n']})")
        for tr in e["track_record"]:
            print(f"     promise {tr['metric']} FY{tr['period_fy'] % 100}: guided {tr['guided']} -> actual {tr['actual']} (x{tr['ratio']})")
    if args.write and results:
        write_entries(results)
        print(f"[+] wrote {len(results)} entries to {REGISTRY_PATH}")
