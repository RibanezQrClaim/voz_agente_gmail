# utils/config.py
from __future__ import annotations
import os
from pathlib import Path

# Raíz del proyecto: .../voz_agente_gmail/
PROJECT_ROOT = Path(__file__).resolve().parents[1]

def get_fake_emails_path() -> Path:
    """
    Ruta al fixture de correos fake.
    Prioriza variable de entorno FAKE_EMAILS_FILE.
    Fallback: tests/fixtures/emails_home.json (ruta relativa al proyecto).
    """
    env_path = os.getenv("FAKE_EMAILS_FILE")
    return Path(env_path) if env_path else PROJECT_ROOT / "tests" / "fixtures" / "emails_home.json"

def get_fake_contacts_path() -> Path:
    """
    Ruta al fixture de contactos (para pasos siguientes).
    """
    env_path = os.getenv("FAKE_CONTACTS_FILE")
    return Path(env_path) if env_path else PROJECT_ROOT / "tests" / "fixtures" / "contacts_retail.json"
