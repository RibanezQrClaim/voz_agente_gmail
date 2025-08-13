# main.py

import os
import sys

# --- Carga .env ANTES de importar módulos del proyecto ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Debug rápido: confirma que el .env se cargó
print(f"LLM_MODE={os.getenv('LLM_MODE')}  MODEL={os.getenv('LLM_LOCAL_MODEL_PATH')}")

# Asegura que los imports relativos funcionen al ejecutar desde la raíz
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS

# Blueprints del proyecto (importar después de load_dotenv)
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
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "127.0.0.1")
    print(f"🚀 Server starting on http://{host}:{port}")
    # Evita el doble proceso del reloader que confunde los logs en Windows
    app.run(debug=True, host=host, port=port, use_reloader=False, threaded=True)

