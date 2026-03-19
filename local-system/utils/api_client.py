# local-system/utils/api_client.py
"""
Cliente HTTP hacia el backend Vercel.
Encapsula todas las llamadas REST para mantener el resto del sistema desacoplado.
"""

import logging
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import BACKEND_URL, API_KEY

logger = logging.getLogger(__name__)

# Timeout por defecto (segundos)
DEFAULT_TIMEOUT = (3.0, 10.0)  # (connect, read)


def _build_session() -> requests.Session:
    """Configura sesión con reintentos automáticos en errores de red."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://",  adapter)
    return session


class ApiClient:
    """
    Abstracción sobre la API REST del backend.

    La API Key se envía en el header X-API-Key; nunca se loggea.
    """

    def __init__(self) -> None:
        self._base = BACKEND_URL.rstrip("/")
        self._session = _build_session()
        self._headers = {
            "Content-Type": "application/json",
            "X-API-Key": API_KEY,
        }

    # ── Usuarios ──────────────────────────────────────────────

    def get_usuarios(self) -> List[Dict[str, Any]]:
        """Descarga todos los usuarios con sus embeddings."""
        return self._get("/api/usuarios") or []

    def register_user(self, nombre: str, email: str, encoding: List[float]) -> Optional[Dict]:
        """Registra un nuevo usuario con su embedding facial."""
        return self._post("/api/register", {
            "nombre":   nombre,
            "email":    email,
            "encoding": encoding,
        })

    # ── Logs ──────────────────────────────────────────────────

    def post_log(
        self,
        usuario_id: Optional[int],
        estado: str,
        metodo: str,
        detalle: str,
        confianza: float = 0.0,
    ) -> Optional[Dict]:
        return self._post("/api/logs", {
            "usuario_id": usuario_id,
            "estado":     estado,
            "metodo":     metodo,
            "detalle":    detalle,
            "confianza":  round(confianza, 4),
        })

    def get_logs(self, limit: int = 50) -> List[Dict]:
        return self._get(f"/api/logs?limit={limit}") or []

    # ── Alertas ───────────────────────────────────────────────

    def post_alerta(
        self,
        tipo: str,
        descripcion: str,
        usuario_id: Optional[int] = None,
    ) -> Optional[Dict]:
        return self._post("/api/alertas", {
            "tipo":        tipo,
            "descripcion": descripcion,
            "usuario_id":  usuario_id,
        })

    # ── HTTP helpers ──────────────────────────────────────────

    def _get(self, path: str) -> Any:
        url = self._base + path
        try:
            resp = self._session.get(url, headers=self._headers, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.error("GET %s falló: %s", path, exc)
            return None

    def _post(self, path: str, payload: Dict) -> Optional[Dict]:
        url = self._base + path
        try:
            resp = self._session.post(url, json=payload, headers=self._headers, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.error("POST %s falló: %s", path, exc)
            return None
