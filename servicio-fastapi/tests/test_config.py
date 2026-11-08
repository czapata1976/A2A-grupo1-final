from __future__ import annotations

from pathlib import Path

import pytest

from app.config import ConfiguracionInvalida, cargar_settings


def test_rechaza_sin_claves(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("API_KEYS", raising=False)
    with pytest.raises(ConfiguracionInvalida):
        cargar_settings(env_file=tmp_path / "no-existe.env")


def test_rechaza_clave_de_ejemplo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("API_KEYS", "clave-ficticia-de-ejemplo-0000")
    with pytest.raises(ConfiguracionInvalida):
        cargar_settings(env_file=tmp_path / "no-existe.env")


def test_rechaza_servidor_invalido(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("API_KEYS", "clave-suficientemente-larga")
    monkeypatch.setenv("A2A_SERVIDORES", "ftp://127.0.0.1:2025")
    with pytest.raises(ConfiguracionInvalida):
        cargar_settings(env_file=tmp_path / "no-existe.env")


def test_rechaza_cors_abierto(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("API_KEYS", "clave-suficientemente-larga")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(ConfiguracionInvalida):
        cargar_settings(env_file=tmp_path / "no-existe.env")


def test_configuracion_valida(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("API_KEYS", "clave-suficientemente-larga")
    monkeypatch.setenv("A2A_SERVIDORES", "http://127.0.0.1:2025,http://127.0.0.1:2026")
    monkeypatch.setenv("CORS_ORIGINS", "")
    monkeypatch.setenv("AUDIT_LOG", "")
    settings = cargar_settings(env_file=tmp_path / "no-existe.env")
    assert settings.claves_api == ("clave-suficientemente-larga",)
    assert settings.servidores_a2a == ("http://127.0.0.1:2025", "http://127.0.0.1:2026")
    assert settings.ruta_auditoria is None
