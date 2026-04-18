"""
Análisis de imagen con Gemini en segundo plano tras crear la medición.
"""
from __future__ import annotations

import logging
import threading

from django.db import close_old_connections, transaction

logger = logging.getLogger(__name__)


def _compare_operator_vs_ai(operator_reading, ai_text: str) -> bool | None:
    """True si coinciden (solo dígitos, sin ceros a la izquierda). None si no aplica."""
    if operator_reading is None or not ai_text:
        return None
    def digits(s: str) -> str:
        return ''.join(c for c in str(s) if c.isdigit())
    o = digits(str(operator_reading).replace('.', ''))
    a = digits(ai_text)
    if not o or not a:
        return None
    if 'X' in ai_text.upper() or 'X' in str(operator_reading).upper():
        return o.upper().replace('X', '') == a.upper().replace('X', '')
    try:
        return int(o) == int(a)
    except ValueError:
        return o == a


def _apply_ai_result(measurement_id: int) -> None:
    from django.apps import apps
    Measurement = apps.get_model('measurements', 'Measurement')

    from . import ocr_service

    try:
        m = Measurement.objects.select_related('apartment').get(pk=measurement_id)
    except Measurement.DoesNotExist:
        return

    if not m.photo:
        Measurement.objects.filter(pk=measurement_id).update(
            ai_analysis_status='skipped',
        )
        return

    layout = getattr(m.apartment, 'reading_layout', None) or 'A'
    layout = 'B' if str(layout).upper() == 'B' else 'A'

    Measurement.objects.filter(pk=measurement_id).update(ai_analysis_status='processing')

    try:
        m.photo.open('rb')
        raw = m.photo.read()
        m.photo.close()
    except Exception as e:
        logger.exception('No se pudo leer la foto: %s', e)
        Measurement.objects.filter(pk=measurement_id).update(ai_analysis_status='failed')
        return

    try:
        cropped = ocr_service.crop_to_circle_zone(raw)
        ai_text = ocr_service.analyze_image(cropped, meter_reading_type=layout)
        ai_text = (ai_text or '').strip()
    except Exception as e:
        logger.exception('Gemini falló para medición %s: %s', measurement_id, e)
        Measurement.objects.filter(pk=measurement_id).update(ai_analysis_status='failed')
        return

    agree = _compare_operator_vs_ai(m.reading_value, ai_text)

    from decimal import Decimal

    updates = {
        'ocr_value': ai_text[:50],
        'ai_analysis_status': 'complete',
        'ai_agrees_with_operator': agree,
    }
    if m.reading_value is None and ai_text:
        # Sin lectura manual: usar la estimación de IA como lectura principal
        try:
            digits = ''.join(c for c in ai_text if c.isdigit())
            if digits:
                updates['reading_value'] = Decimal(int(digits))
        except Exception:
            logger.warning('No se pudo derivar reading_value de IA: %s', ai_text)

    Measurement.objects.filter(pk=measurement_id).update(**updates)


def schedule_measurement_ai_analysis(measurement_id: int) -> None:
    """Ejecuta el análisis en un hilo daemon (sin Celery)."""

    def _run():
        close_old_connections()
        try:
            _apply_ai_result(measurement_id)
        except Exception:
            logger.exception('ai_processing thread error for measurement %s', measurement_id)
            try:
                from django.apps import apps
                Measurement = apps.get_model('measurements', 'Measurement')
                Measurement.objects.filter(pk=measurement_id).update(ai_analysis_status='failed')
            except Exception:
                pass
        finally:
            close_old_connections()

    threading.Thread(target=_run, daemon=True).start()


def hook_after_measurement_create(measurement_id: int, has_photo: bool) -> None:
    if not has_photo:
        return
    transaction.on_commit(lambda: schedule_measurement_ai_analysis(measurement_id))
