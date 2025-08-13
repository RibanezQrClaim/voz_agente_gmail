from googleapiclient.discovery import build
from datetime import datetime
import email.utils

def contar_correos_no_leidos(service):
    """
    Cuenta la cantidad de correos no leídos en la bandeja de entrada.
    """
    results = service.users().messages().list(userId='me', q="is:unread").execute()
    cantidad = len(results.get('messages', []))
    if cantidad == 0:
        return "No tienes correos sin leer."
    elif cantidad == 1:
        return "Tienes 1 correo sin leer."
    else:
        return f"Tienes {cantidad} correos sin leer."

def remitentes_hoy(service):
    """
    Devuelve una lista única de remitentes que escribieron hoy.
    """
    hoy = datetime.utcnow().date()
    query = f"after:{hoy.strftime('%Y/%m/%d')}"
    results = service.users().messages().list(userId='me', q=query, maxResults=50).execute()
    mensajes = results.get('messages', [])

    remitentes = set()
    for msg in mensajes:
        detalle = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='metadata',
            metadataHeaders=['From']
        ).execute()
        headers = detalle.get('payload', {}).get('headers', [])
        for h in headers:
            if h['name'] == 'From':
                nombre, correo = email.utils.parseaddr(h['value'])
                remitentes.add(nombre or correo)

    if not remitentes:
        return "Hoy no has recibido correos nuevos."

    lista = sorted(remitentes)
    if len(lista) == 1:
        return f"Hoy te escribió {lista[0]}."
    else:
        nombres = ", ".join(lista[:-1]) + " y " + lista[-1]
        return f"Hoy te escribieron {nombres}."

def resumen_correos_hoy(service):
    """
    Genera un resumen con los asuntos de los correos recibidos hoy.
    """
    hoy = datetime.utcnow().date()
    query = f"after:{hoy.strftime('%Y/%m/%d')}"
    results = service.users().messages().list(userId='me', q=query, maxResults=10).execute()
    mensajes = results.get('messages', [])

    resumen = []
    for msg in mensajes:
        detalle = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject']).execute()
        headers = detalle.get('payload', {}).get('headers', [])
        for h in headers:
            if h['name'] == 'Subject':
                resumen.append(h['value'])

    if not resumen:
        return "No has recibido correos hoy."
    elif len(resumen) == 1:
        return f"Hoy recibiste 1 correo: '{resumen[0]}'."
    else:
        texto = "; ".join(f"'{s}'" for s in resumen)
        return f"Hoy recibiste {len(resumen)} correos. Los asuntos son: {texto}."
