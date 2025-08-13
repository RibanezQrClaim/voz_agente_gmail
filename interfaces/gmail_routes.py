# interfaces/gmail_routes.py
from __future__ import annotations
import os
from flask import Blueprint, request, jsonify

gmail_bp = Blueprint("gmail", __name__)

USE_FAKE = os.getenv("USE_FAKE_GMAIL", "false").lower() == "true"

if USE_FAKE:
    # Backend simulado
    from utils.fake_gmail import leer_ultimo, remitentes_hoy, contar_no_leidos, buscar
else:
    # Backend real (Gmail API)
    from core.gmail.leer import leer_ultimo, remitentes_hoy, contar_no_leidos
    from core.gmail.buscar import buscar


@gmail_bp.get("/gmail/ultimo")
def http_ultimo():
    msg = leer_ultimo()
    if not msg:
        return jsonify({"data": None}), 200
    return jsonify({"data": msg}), 200


@gmail_bp.get("/gmail/remitentes_hoy")
def http_remitentes_hoy():
    senders = remitentes_hoy()
    return jsonify({"data": senders}), 200


@gmail_bp.get("/gmail/no_leidos")
def http_no_leidos():
    n = contar_no_leidos()
    return jsonify({"data": n}), 200


@gmail_bp.post("/gmail/buscar")
def http_buscar():
    payload = request.get_json(silent=True) or {}
    query = (payload.get("query") or "").strip()
    max_results = int(payload.get("max", 20))
    if not query:
        return jsonify({"error": {"code": "BAD_REQUEST", "message": "Falta 'query'."}}), 400
    results = buscar(query, max_results=max_results)
    return jsonify({"data": results}), 200

