from utils.dates import get_rfc3339_today
from core.llm.llm_client import resumir_texto_llm
import base64

EXCLUIR_CATEGORIAS = "-category:promotions -category:social -category:updates"


def remitentes_hoy(service):
    """Devuelve un string con los remitentes únicos que enviaron correos hoy, uno por línea"""
    today_rfc3339 = get_rfc3339_today()
    query = f"after:{today_rfc3339} is:inbox {EXCLUIR_CATEGORIAS}"
    results = service.users().messages().list(userId='me', q=query, maxResults=50).execute()
    messages = results.get('messages', [])

    remitentes = set()
    for msg in messages:
        detalle = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From']).execute()
        headers = detalle.get('payload', {}).get('headers', [])
        for h in headers:
            if h['name'] == 'From':
                remitentes.add(h['value'])

    if not remitentes:
        return "No recibiste correos hoy."

    def limpiar_remitente(r):
        if "<" in r:
            return r.split("<")[0].strip()
        return r.strip()

    nombres_limpios = [limpiar_remitente(r) for r in remitentes]
    nombres_limpios.sort()

    return "\n".join(nombres_limpios)


def resumen_correos_hoy(service, cantidad=5):
    """Devuelve un resumen LLM conjunto de los correos de hoy, limitado a 300 caracteres."""
    today_rfc3339 = get_rfc3339_today()
    query = f"after:{today_rfc3339} is:inbox {EXCLUIR_CATEGORIAS}"
    results = service.users().messages().list(userId='me', q=query, maxResults=cantidad).execute()
    messages = results.get('messages', [])

    if not messages:
        return "No tienes correos nuevos hoy."

    bloques = []
    for i, msg in enumerate(reversed(messages), start=1):  # orden cronológico
        detalle = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = detalle['payload'].get('headers', [])
        remitente = next((h['value'] for h in headers if h['name'] == 'From'), '(Desconocido)')
        asunto = next((h['value'] for h in headers if h['name'] == 'Subject'), '(Sin asunto)')

        cuerpo = ""
        if 'parts' in detalle['payload']:
            for part in detalle['payload']['parts']:
                if part.get('mimeType') == 'text/plain' and 'data' in part['body']:
                    cuerpo = base64.urlsafe_b64decode(part['body']['data']).decode("utf-8", errors="ignore")
                    break

        if not cuerpo:
            cuerpo = detalle.get('snippet', '')

        bloques.append(f"Correo {i}:\nDe: {remitente}\nAsunto: {asunto}\n{cuerpo.strip()}")

    texto_completo = "\n\n".join(bloques)
    resumen_final = resumir_texto_llm(texto_completo)

    return resumen_final[:300] + ("..." if len(resumen_final) > 300 else "")


def contar_correos_no_leidos(service):
    """Cuenta la cantidad de correos no leídos en la bandeja de entrada."""
    query = f"is:unread in:inbox {EXCLUIR_CATEGORIAS}"
    results = service.users().messages().list(userId='me', q=query).execute()
    mensajes = results.get('messages', [])
    return len(mensajes) if mensajes else 0


def leer_ultimo_correo(service):
    """
    Devuelve el último correo recibido, sin importar la fecha.
    """
    try:
        resultado = service.users().messages().list(
            userId='me',
            maxResults=1,
            q="",  # sin filtro de fecha
        ).execute()

        mensajes = resultado.get('messages', [])
        if not mensajes:
            return "No tienes correos nuevos."

        mensaje_id = mensajes[0]['id']
        mensaje = service.users().messages().get(userId='me', id=mensaje_id, format='metadata').execute()

        headers = mensaje.get("payload", {}).get("headers", [])
        remitente = next((h["value"] for h in headers if h["name"] == "From"), "Remitente desconocido")
        asunto = next((h["value"] for h in headers if h["name"] == "Subject"), "(Sin asunto)")

        return f"📩 De: {remitente}\n📌 Asunto: {asunto}"

    except Exception as e:
        print("❌ Error al leer el último correo:", e)
        return "No se pudo obtener el último correo."
