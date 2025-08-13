# utils/summarizer.py
from typing import List, Dict, Any, Optional
import os, re, base64, html

# --- Config desde entorno ---
SUMMARY_MAX_CHARS = int(os.getenv("SUMMARY_MAX_CHARS", "350"))
GMAIL_MAX_RESULTS = int(os.getenv("GMAIL_MAX_RESULTS", "10"))
SUMMARY_INPUT_CHARS = int(os.getenv("SUMMARY_INPUT_CHARS", "400"))
LLM_MODE = os.getenv("LLM_MODE", "off").lower()

# LLM local (opcional). Si falla la importación, usamos None y haremos fallback extractivo.
try:
    from core.llm.llm_client import parafrasear_una_oracion
except Exception:
    def parafrasear_una_oracion(texto: str, max_chars: int = 220) -> Optional[str]:
        return None

# --- Campos de Gmail para bajar latencia ---
MESSAGE_FIELDS_LIST = "messages(id),nextPageToken"
MESSAGE_FIELDS_GET_FULL = (
    "id,internalDate,labelIds,snippet,"
    "payload(mimeType,body/data,parts,headers(name,value))"
)

# Excluir categorías no primarias
EXCLUDED_LABELS = {
    "CATEGORY_SOCIAL", "CATEGORY_PROMOTIONS", "CATEGORY_UPDATES",
    "CATEGORY_FORUMS", "SPAM", "TRASH",
}

# ---------- Helpers de Gmail ----------

def _primary_query(base_query: Optional[str] = None) -> str:
    parts = [
        "category:primary", "-category:social", "-category:promotions",
        "-category:updates", "-category:forums", "-in:spam", "-in:trash",
    ]
    if base_query:
        parts.append(f"({base_query})")
    return " ".join(parts)

def _list_primary_message_ids(service, max_results: int, base_query: Optional[str]) -> List[str]:
    q = _primary_query(base_query)
    resp = (
        service.users()
        .messages()
        .list(
            userId="me",
            q=q,
            labelIds=["INBOX"],
            maxResults=max_results,
            includeSpamTrash=False,
            fields=MESSAGE_FIELDS_LIST,
        )
        .execute()
        or {}
    )
    return [m["id"] for m in resp.get("messages", []) or []]

def _get_message_full(service, msg_id: str) -> Dict[str, Any]:
    return (
        service.users()
        .messages()
        .get(
            userId="me",
            id=msg_id,
            format="full",
            fields=MESSAGE_FIELDS_GET_FULL,
        )
        .execute()
        or {}
    )

def _b64url_to_bytes(data: str) -> bytes:
    data += "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data)

def _strip_html(s: str) -> str:
    s = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", s)
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    s = html.unescape(s)
    return s

def _walk_payload(part: Dict[str, Any]) -> tuple[str, str]:
    if not part:
        return "", ""
    plain_acc, html_acc = "", ""
    mime = (part.get("mimeType") or "").lower()
    body = part.get("body") or {}
    data = body.get("data")
    if data:
        text = _b64url_to_bytes(data).decode(errors="ignore")
        if mime.startswith("text/plain"):
            plain_acc += text
        elif mime.startswith("text/html"):
            html_acc += text
    for sp in (part.get("parts") or []):
        p_plain, p_html = _walk_payload(sp)
        plain_acc += p_plain
        html_acc += p_html
    return plain_acc, html_acc

def _extract_text_from_payload(payload: Dict[str, Any]) -> str:
    plain, html_raw = _walk_payload(payload)
    if plain.strip():
        return plain.strip()
    if html_raw.strip():
        return _strip_html(html_raw).strip()
    return ""

# ---------- Limpieza básica de texto ----------

RE_QUOTED = re.compile(r"(?im)^(>+|el\s+.+\sescribió:|on\s+.+\swrote:).*$")
RE_SIG = re.compile(r"(?m)^--\s*$.*", re.DOTALL)
RE_DISCLAIMER = re.compile(r"(?is)(este mensaje.*confidencial|this message.*confidential).*$")
RE_URL = re.compile(r"https?://\S+")
RE_WS = re.compile(r"[ \t]+")
RE_LINES = re.compile(r"\n{2,}")

def _clean(text: str) -> str:
    if not text:
        return ""
    t = text[:SUMMARY_INPUT_CHARS]
    t = RE_DISCLAIMER.sub("", t)
    t = "\n".join(l for l in t.splitlines() if not RE_QUOTED.match(l.strip()))
    t = RE_SIG.sub("", t)
    t = RE_URL.sub("", t)
    t = RE_WS.sub(" ", t)
    t = RE_LINES.sub("\n", t)
    return t.strip()

def _too_similar(src: str, out: str) -> bool:
    if not src or not out:
        return False
    s = set(re.findall(r"\w+", src.lower()))
    o = set(re.findall(r"\w+", out.lower()))
    if not s or not o:
        return out.lower() in src.lower()
    overlap = len(s & o) / max(1, len(o))
    return (out.lower() in src.lower()) or (overlap > 0.85)

# ---------- Post-proceso para forzar UNA oración ----------

ABBR = {"sr.", "sra.", "dr.", "dra.", "ing.", "lic.", "ee.uu.", "p.ej.", "etc."}

def _tidy_sentence(s: str) -> str:
    if not s:
        return s
    s = " ".join(s.split())                    # colapsar espacios
    s = s.replace(" ,", ",").replace(" .", ".")
    s = s.strip(" \"'–—-")
    # Capitalizar primera letra si es minúscula
    if s and s[0].islower():
        s = s[0].upper() + s[1:]
    # Asegurar punto final si termina en letra/dígito
    if s and s[-1].isalnum():
        s += "."
    return s

def _first_meaningful_sentence(s: str) -> str:
    """Toma la primera oración razonable evitando cortar abreviaturas o numeraciones."""
    if not s:
        return s
    buf = []
    for i, ch in enumerate(s):
        buf.append(ch)
        if ch in ".!?":
            frag = "".join(buf).strip()
            tail = s[i+1:i+3].strip().lower()
            # Evitar cortar si parece abreviatura
            last = frag.lower().split()[-1] if frag.split() else ""
            if last in ABBR:
                continue
            # Evitar punto de listas '1.' '2.' seguidos de dígito
            if ch == "." and tail[:1].isdigit():
                continue
            return frag
    return s.strip()

def _enforce_one_sentence(s: str, budget: int) -> str:
    if not s:
        return s
    s1 = _first_meaningful_sentence(s)
    s1 = _tidy_sentence(s1)
    return s1[:budget] if len(s1) > budget else s1

# ---------- Composición del item ----------

def _compose_item(meta: Dict[str, Any], clean_body: str) -> Optional[str]:
    if not meta:
        return None
    headers = {h["name"].lower(): h["value"] for h in (meta.get("payload", {}) or {}).get("headers", [])}
    frm = (headers.get("from") or "").strip()
    subject = (headers.get("subject") or "").strip()
    snippet = (meta.get("snippet") or "").strip()
    base_text = clean_body if clean_body else snippet

    hdr = f"De: {frm} | Asunto: {subject} — "
    budget = max(60, SUMMARY_MAX_CHARS - len(hdr))  # espacio real para el resumen

    summary: Optional[str] = None

    if LLM_MODE == "local" and base_text:
        summary = parafrasear_una_oracion(base_text, max_chars=budget)
        if summary:
            # limpiar posibles ecos del prompt
            summary = re.sub(r"^#+\s*resumen.*?:\s*", "", summary, flags=re.IGNORECASE)
            summary = re.sub(r"^(resumen\s*:)\s*", "", summary, flags=re.IGNORECASE)
            summary = _enforce_one_sentence(summary, budget)
        if summary and _too_similar(base_text, summary):
            summary = None

    if not summary:
        # Fallback extractivo → toma primera oración "decente"
        text = (base_text or "").strip()
        if not text:
            summary = "(Sin contenido)"
        else:
            summary = _enforce_one_sentence(text, budget)

    out = (hdr + (summary or "")).strip()
    return out if len(out) <= SUMMARY_MAX_CHARS else out[:SUMMARY_MAX_CHARS - 1] + "…"

# ---------- Endpoint: resumen de correos de hoy ----------

def resumen_correos_hoy(service, cantidad: int = 10) -> str:
    n = max(1, min(int(cantidad), GMAIL_MAX_RESULTS))
    ids = _list_primary_message_ids(service, n, base_query="newer_than:1d")
    if not ids:
        return "No has recibido correos hoy."

    items: List[str] = []
    for mid in ids:
        meta = _get_message_full(service, mid)
        if not meta:
            continue
        if set(meta.get("labelIds", []) or []) & EXCLUDED_LABELS:
            continue
        body = _extract_text_from_payload(meta.get("payload") or {})
        clean = _clean(body)
        formatted = _compose_item(meta, clean)
        if formatted:
            items.append(formatted)

    if not items:
        return "No has recibido correos hoy."
    return "\n-----\n".join(items)
