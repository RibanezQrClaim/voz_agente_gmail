from flask import Blueprint, jsonify
from core.gmail.leer import remitentes_hoy
from core.gmail.auth import get_authenticated_service

gmail_bp = Blueprint('gmail', __name__)

@gmail_bp.route('/api/gmail/quien-escribio-hoy', methods=['GET'])
def endpoint_quien_escribio_hoy():
    service = get_authenticated_service()
    lista = remitentes_hoy(service)

    nombres = lista.split("\n")
    if not nombres or nombres == ["No recibiste correos hoy."]:
        return jsonify({"respuesta": "No recibiste correos hoy."})

    respuesta = "Hoy te escribieron:\n" + "\n".join(f"- {n}" for n in nombres)
    return jsonify({"respuesta": respuesta})
