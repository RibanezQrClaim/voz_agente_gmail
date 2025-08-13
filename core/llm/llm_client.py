# core/llm/llm_client.py
# Cliente LLM local (Qwen2.5-3B-Instruct GGUF vía llama-cpp)
# Resumen en UNA oración y clasificación simple de intención

from typing import Optional, Any, TYPE_CHECKING
import os
import os.path as osp
import re

if TYPE_CHECKING:
    from llama_cpp import Llama as LlamaType  # type: ignore
else:
    LlamaType = Any

try:
    from llama_cpp import Llama
except Exception:
    Llama = None  # type: ignore

# --- Config ---
MODEL_PATH = os.getenv(
    "LLM_LOCAL_MODEL_PATH",
    osp.join("models", "Qwen2.5-3B-Instruct-Q4_K_M.gguf"),
)
CTX       = int(os.getenv("LLM_LOCAL_CTX", "2048"))
THREADS   = int(os.getenv("LLM_LOCAL_THREADS", "6"))
MAX_TOK   = int(os.getenv("LLM_LOCAL_MAX_TOKENS", "96"))
TEMP_SUM  = float(os.getenv("LLM_LOCAL_TEMP_SUMMARY", "0.4"))
TEMP_INT  = float(os.getenv("LLM_LOCAL_TEMP_INTENT", "0.0"))

SUMMARY_INPUT_CHARS = int(os.getenv("SUMMARY_INPUT_CHARS", "400"))  # reducido para forzar síntesis
SUMMARY_MAX_CHARS   = int(os.getenv("SUMMARY_MAX_CHARS", "350"))    # cambiado de 280 a 350

_STOP = ["</s>", "Usuario:", "Asistente:", "\n\n"]

_LLM: Optional[LlamaType] = None

# --- Carga única del modelo ---
def _get_llm() -> Optional[LlamaType]:
    global _LLM
    if _LLM is None and Llama is not None:
        print(f"🦙 Cargando modelo local: {MODEL_PATH} (ctx={CTX}, threads={THREADS})")
        _LLM = Llama(
            model_path=MODEL_PATH,
            n_ctx=CTX,
            n_threads=THREADS,
            verbose=False,
        )
    return _LLM

# --- Ejecutor ---
def _complete(prompt: str, max_tokens: int, temperature: float) -> Optional[str]:
    llm = _get_llm()
    if not llm:
        return None
    try:
        if hasattr(llm, "create_completion"):
            out = llm.create_completion(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.95,
                stop=_STOP,
            )
        else:
            out = llm(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.95,
                stop=_STOP,
                echo=False,
            )
        return (out["choices"][0]["text"] or "").strip()
    except Exception as e:
        print("❌ LLM error:", e)
        return None

# --- Utilidad: detectar si copió literal ---
def _too_similar(src: str, out: str) -> bool:
    if not src or not out:
        return False
    s = set(re.findall(r"\w+", src.lower()))
    o = set(re.findall(r"\w+", out.lower()))
    if not s or not o:
        return out.lower() in src.lower()
    overlap = len(s & o) / max(1, len(o))
    return (out.lower() in src.lower()) or (overlap > 0.93)

# --- Parafraseo / resumen ---
def parafrasear_una_oracion(texto: str, max_chars: int = 220) -> Optional[str]:
    if not texto or not texto.strip():
        return None
    max_chars = min(350, SUMMARY_MAX_CHARS)
    max_tokens = max(150, max_chars // 1)
    t = texto.strip()[:SUMMARY_INPUT_CHARS]
    
    # Prompt ajustado
    prompt = (
        f"### Instrucción\n"
        f"Resume en **UNA sola oración** clara y ejecutiva en ESPAÑOL (máximo {max_chars} caracteres). "
        f"**No** copies frases literales: usa sinónimos y sintetiza. "
        f"Ignora saludos, firmas, enlaces, disclaimers y detalles logísticos triviales. "
        f"Quédate con **máximo dos ideas clave**. "
        f"Si el texto está en otro idioma, tradúcelo al español.\n\n"
        f"### Texto\n{t}\n\n"
        f"### Resumen (solo una oración):"
    )

    out = _complete(prompt, max_tokens=max(120, max_chars // 1), temperature=TEMP_SUM)
    if not out:
        return None
    out = out.strip().replace("\n", " ").strip('" ')

    # Limpieza del eco del encabezado del prompt
    out = re.sub(r"^#+\s*resumen.*?:\s*", "", out, flags=re.IGNORECASE)
    out = re.sub(r"^(resumen\s*:)\s*", "", out, flags=re.IGNORECASE)

    if _too_similar(t, out):
        retry = prompt + "\n(Usa palabras distintas y estructura nueva, resume de forma distinta.)"
        out2 = _complete(retry, max_tokens=max(120, max_chars // 1), temperature=TEMP_SUM + 0.1)
        if out2:
            out2 = out2.strip().replace("\n", " ").strip('" ')
            if not _too_similar(t, out2):
                out = out2

    return out[:max_chars] if out else None

# --- Resumen compat ---
def resumir_texto_llm(texto: str) -> str:
    if not texto:
        return "(Sin contenido)"
    max_chars = min(350, SUMMARY_MAX_CHARS)  # ajustado a 350
    max_tokens = max(150, max_chars // 1)
    s = parafrasear_una_oracion(texto, max_chars=min(350, SUMMARY_MAX_CHARS))
    if not s:
        return (texto[:350] + "…") if len(texto) > 350 else texto
    return s

# --- Clasificación de intención ---
_OPCIONES = "leer_ultimo, resumir, sin_leer, importantes, saludos, desconocido"

def interpretar_comando(texto: str) -> str:
    if not texto:
        return "desconocido"
    prompt = (
        "Clasifica el siguiente comando en EXACTAMENTE una de estas opciones "
        f"(sin explicar nada más): { _OPCIONES }.\n\n"
        f'Comando: "{texto.strip()}"\n'
        "Respuesta (una palabra de la lista):"
    )
    rsp = _complete(prompt, max_tokens=5, temperature=TEMP_INT)
    etiqueta = (rsp or "").strip().lower()
    valid = {s.strip() for s in _OPCIONES.split(",")}
    return etiqueta if etiqueta in valid else "desconocido"
