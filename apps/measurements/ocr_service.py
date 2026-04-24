from __future__ import annotations

import logging
import re
from io import BytesIO
from typing import Optional

from django.conf import settings
from PIL import Image
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Placeholder replaced by "Tipo A" or "Tipo B" for Gemini.
_PROMPT_TEMPLATE = """Eres un experto en lectura de medidores de agua. Extrae la lectura del medidor en la imagen.

[CONFIGURACIÓN ACTIVA]: [AQUÍ_VA_LA_VARIABLE_DEL_TIPO]

Si la configuración es 'Tipo A':
- 5 dígitos enteros (rodillos) y 4 decimales leídos en esferas (o equivalente).
- Orden de salida, de izquierda a derecha: los 5 enteros, luego los 4 “decimales” (9 caracteres en total).
- Usa 'X' si un dígito es ilegible.
- Ejemplo: 00546 y esferas 1,2,0,6 → 005461206 (se muestra 00546,1206 con coma solo para humanos; tú no pongas comas)

Si la configuración es 'Tipo B':
- Físicamente: una fila con 5 rodillos NEGROS (enteros) + 3 rodillos ROJOS (primeros decimales) y una ESFERA roja (el cuarto decimal). Suele haber una coma impresa en el cuerpo entre el 5.º y el 6.º dígito: NO la copies en la salida.
- Lógicamente la lectura completa es exactamente 9 caracteres con la MISMA regla 5+4 que el Tipo A: posiciones 1-5 = parte entera, 6-9 = cuatro decimales.
- Incluye el dígito de la esfera aunque esté un poco tapada (si no alcanza a verlo, use X en esa posición).
- Ejemplo: 00000 (negros) + 064 (rojos) + 6 (esfera) → 000000646 (vista con coma: 00000,0646)

Regla de ORO: Devuelve ÚNICAMENTE la cadena (solo 0-9 o X), sin comas, espacios, texto ni explicación. Longitud exacta: 9."""

CIRCLE_DIAMETER_RATIO = 0.76

_OCR_NON_DIGIT = re.compile(r'[^0-9Xx]')


def _normalize_gemini_ocr_nine_chars(text: str) -> str:
    """Mantiene solo dígitos (y X), recorta o rellena a 9 para estabilidad del cliente."""
    s = (text or '').strip()
    d = _OCR_NON_DIGIT.sub('', s).upper()
    if not d:
        return s
    if len(d) > 9:
        d = d[:9]
    elif len(d) < 9:
        d = d.zfill(9)
    return d


def _normalize_reading_type(meter_reading_type: Optional[str]) -> str:
    t = (meter_reading_type or 'A').strip().upper()
    return t if t in ('A', 'B') else 'A'


def build_prompt(meter_reading_type: Optional[str]) -> str:
    """Build Gemini prompt; meter_reading_type is 'A' or 'B'."""
    t = _normalize_reading_type(meter_reading_type)
    label = 'Tipo A' if t == 'A' else 'Tipo B'
    return _PROMPT_TEMPLATE.replace('[AQUÍ_VA_LA_VARIABLE_DEL_TIPO]', label)


def _get_model():
    """Configure and return a Gemini GenerativeModel."""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel('gemini-2.5-flash')


def crop_to_circle_zone(image_bytes: bytes) -> bytes:
    """
    Crop a square from the center of the image matching the overlay circle
    (76 % of image width). Returns JPEG bytes.
    """
    img = Image.open(BytesIO(image_bytes))
    w, h = img.size

    side = int(w * CIRCLE_DIAMETER_RATIO)
    x = (w - side) // 2
    y = (h - side) // 2

    x = max(0, min(x, w - 1))
    y = max(0, min(y, h - 1))
    right = min(x + side, w)
    bottom = min(y + side, h)

    cropped = img.crop((x, y, right, bottom))

    buf = BytesIO()
    cropped.save(buf, format='JPEG', quality=90)
    buf.seek(0)
    logger.info('Circle crop: %dx%d → %dx%d', w, h, right - x, bottom - y)
    return buf.read()


def analyze_image(image_bytes: bytes, meter_reading_type: Optional[str] = None) -> str:
    """
    Send image bytes to Gemini and return the recognized reading text.
    """
    model = _get_model()
    prompt = build_prompt(meter_reading_type)

    response = model.generate_content([
        prompt,
        {'mime_type': 'image/jpeg', 'data': image_bytes},
    ])

    text = (response.text or '').strip()
    logger.info('Gemini response: "%s" (%d bytes image)', text, len(image_bytes))

    if not text:
        raise ValueError('Gemini devolvió respuesta vacía')
    normalized = _normalize_gemini_ocr_nine_chars(text)
    if normalized != text:
        logger.info('Gemini OCR normalizado: "%s" -> "%s"', text, normalized)
    return normalized


def recognize_from_bytes(image_bytes: bytes, meter_reading_type: Optional[str] = None) -> str:
    """
    Full pipeline: crop + OCR.  Returns the recognized reading string.
    """
    cropped = crop_to_circle_zone(image_bytes)
    return analyze_image(cropped, meter_reading_type=meter_reading_type)
