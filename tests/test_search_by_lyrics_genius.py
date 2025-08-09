import os
import pytest

from app_modules.services.qobuz import QobuzDownloader


PHRASE = "y si te digo que es para toda la vida pero no como esos"


def test_cleaner_keeps_phrase_unchanged():
    """El limpiador debe normalizar la frase sin alterarla (no hay tildes/ símbolos).

    Se evita ejecutar __init__ para no realizar llamadas de red en este test.
    """
    q = QobuzDownloader.__new__(QobuzDownloader)
    cleaned = QobuzDownloader._clean_lyrics_text(q, PHRASE)
    assert cleaned == PHRASE


@pytest.mark.skipif(
    os.getenv("RUN_ONLINE_TESTS") != "1",
    reason="Prueba de integración con red (Genius/Qobuz). Establece RUN_ONLINE_TESTS=1 para ejecutarla.",
)
def test_search_by_lyrics_with_genius_api_returns_match():
    """Usa la API de Genius para buscar por letra y exige que el título en Qobuz
    coincida exactamente con el título obtenido de Genius (ni más, ni menos).

    Nota: Esta prueba realiza peticiones HTTP externas y requiere conectividad.
    """
    q = QobuzDownloader()

    # 1) Obtener la mejor coincidencia de Genius y su título exacto
    genius_hits = q._search_genius_api(PHRASE, limit=1)
    assert genius_hits, "No se obtuvieron resultados desde Genius para la frase dada"
    g_title = genius_hits[0].get("title")
    assert isinstance(g_title, str) and g_title, "El título de Genius debe existir"

    # 2) Ejecutar la búsqueda por letra que intenta mapear a Qobuz
    res = q.search_by_lyrics(PHRASE, limit=1)
    assert isinstance(res, list) and res, "Se espera al menos un resultado para la frase dada"

    item = res[0]
    # Requisitos mínimos
    assert item.get("genius_match") is True
    assert isinstance(item.get("genius_url"), str) and item["genius_url"].startswith("http")

    # 3) Debe mapear a Qobuz y el título de Qobuz debe ser exactamente igual al de Genius
    assert item.get("source") == "qobuz", "Se esperaba un mapeo a Qobuz"
    assert item.get("title") == g_title, (
        f"El título de Qobuz debe coincidir exactamente con el de Genius. "
        f"Qobuz='{item.get('title')}', Genius='{g_title}'"
    )
