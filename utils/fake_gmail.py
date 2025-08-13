# utils/fake_gmail.py
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from utils.config import get_fake_emails_path


@dataclass(frozen=True)
class FakeEmail:
    id: str
    from_: str
    subject: str
    date_epoch_ms: int
    snippet: str
    labels: List[str]
    has_attachments: bool
    body: str
    to: List[str]
    cc: List[str]
    is_unread: bool

    @property
    def date_dt(self) -> datetime:
        return datetime.fromtimestamp(self.date_epoch_ms / 1000.0, tz=timezone.utc)

    def to_gmail_like(self) -> Dict[str, Any]:
        # Forma simple y estable para el MVP/resumen
        return {
            "id": self.id,
            "snippet": self.snippet,
            "internalDate": str(self.date_epoch_ms),
            "labelIds": self.labels,
            "hasAttachments": self.has_attachments,
            "payload": {
                "headers": [
                    {"name": "From", "value": self.from_},
                    {"name": "Subject", "value": self.subject},
                    # Fecha RFC2822 aproximada, por si algo la usa:
                    {
                        "name": "Date",
                        "value": self.date_dt.astimezone().strftime("%a, %d %b %Y %H:%M:%S %z"),
                    },
                    {"name": "To", "value": ", ".join(self.to)},
                    {"name": "Cc", "value": ", ".join(self.cc)},
                ],
                # Cuerpo “llano” para el summarizer (ya con ruido/HTML según el fixture):
                "body": {"data": self.body},
            },
            # Campo directo útil si no quieres navegar payload:
            "from": self.from_,
            "subject": self.subject,
            "to": self.to,
            "cc": self.cc,
            "isUnread": self.is_unread,
            "body": self.body,
        }


# --- Carga y cache en memoria -------------------------------------------------

_CACHE: List[FakeEmail] | None = None

def _load_fixture() -> List[FakeEmail]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    path: Path = get_fake_emails_path()
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    emails: List[FakeEmail] = []
    for e in raw:
        emails.append(
            FakeEmail(
                id=str(e.get("id")),
                from_=e.get("from", ""),
                subject=e.get("subject", ""),
                date_epoch_ms=int(e.get("internalDate", e.get("dateEpochMs", 0))),
                snippet=e.get("snippet", ""),
                labels=list(e.get("labels", [])),
                has_attachments=bool(e.get("hasAttachments", False)),
                body=e.get("body", ""),
                to=list(e.get("to", [])),
                cc=list(e.get("cc", [])),
                is_unread=bool(e.get("isUnread", True)),
            )
        )

    # Ordenar descendente por fecha (más nuevo primero), como hace Gmail
    emails.sort(key=lambda x: x.date_epoch_ms, reverse=True)
    _CACHE = emails
    return _CACHE


# --- API simulada usada por el MVP --------------------------------------------

def leer_ultimo() -> Optional[Dict[str, Any]]:
    """Devuelve el último correo (más reciente) en formato 'gmail-like'."""
    data = _load_fixture()
    if not data:
        return None
    return data[0].to_gmail_like()


def remitentes_hoy(now: Optional[datetime] = None) -> List[str]:
    """
    Lista de remitentes únicos que escribieron HOY (zona local del host).
    En caso de necesitar TZ distinta, podemos parametrizar.
    """
    now = now or datetime.now().astimezone()
    data = _load_fixture()
    senders: List[str] = []
    for e in data:
        dt_local = datetime.fromtimestamp(e.date_epoch_ms / 1000.0, tz=timezone.utc).astimezone(now.tzinfo)
        if dt_local.date() == now.date():
            if e.from_ not in senders:
                senders.append(e.from_)
        else:
            # como vienen ordenados desc, si ya pasamos a ayer, cortamos
            if dt_local.date() < now.date():
                break
    return senders


def contar_no_leidos() -> int:
    """Cuenta correos marcados como no leídos en el fixture."""
    return sum(1 for e in _load_fixture() if e.is_unread)


# (Opcional para pasos siguientes) búsqueda muy simple por query en from/subject/body
def buscar(query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Búsqueda naive contains() en from/subject/body. Mantiene orden por fecha.
    """
    q = (query or "").strip().lower()
    if not q:
        return []
    out: List[Dict[str, Any]] = []
    for e in _load_fixture():
        hay = (
            q in e.from_.lower()
            or q in e.subject.lower()
            or q in e.body.lower()
        )
        if hay:
            out.append(e.to_gmail_like())
        if len(out) >= max_results:
            break
    return out
