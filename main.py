# from voz_agente_gmail.interfaces.voice_input import escuchar_comando
# from voz_agente_gmail.core.intent_detector import detectar_intencion
# from voz_agente_gmail.core.action_router import ejecutar_accion
# from voz_agente_gmail.interfaces.voice_output import responder_en_voz

# def ejecutar_agente_voz(contexto_usuario=None):
#     comando = escuchar_comando()
#     intencion = detectar_intencion(comando, contexto_usuario)
#     respuesta = ejecutar_accion(intencion, comando, contexto_usuario)
#     responder_en_voz(respuesta)

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from interfaces.gmail_routes import gmail_bp
from interfaces.comando_api import comando_bp  # 🎯 Director de orquesta
from interfaces.auth_routes import auth_bp     # 🔐 Login/Logout Gmail

app = Flask(__name__)
app.secret_key = "clave_secreta_123"  # Requerido para sesiones OAuth
CORS(app)

# Registrar Blueprints
app.register_blueprint(gmail_bp)
app.register_blueprint(comando_bp)
app.register_blueprint(auth_bp)

# Servir la interfaz visual (HTML)
@app.route("/")
def home():
    return send_from_directory('frontend', 'index_bloques.html')

# (Opcional) Servir archivos estáticos si los necesitas más adelante
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("frontend", filename)

if __name__ == "__main__":
    app.run(debug=True)