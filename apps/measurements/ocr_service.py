from __future__ import annotations

import logging
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
- 5 dígitos enteros (rodillos superiores) + 4 dígitos de esferas/decimales inferiores.
- Formato de salida: exactamente 9 caracteres (solo dígitos 0-9 o 'X' si un dígito es ilegible).
- Ejemplo: rodillos 00546 y esferas 1,2,0,6 → 005461206

Si la configuración es 'Tipo B':
- 8 dígitos enteros en los rodillos negros, de izquierda a derecha.
- 1 dígito adicional correspondiente SOLO a la esfera roja/agua (decimal visual), lectura del puntero.
- NO incluyas otros dígitos decimales adicionales: solo ese último dígito de la esfera.
- Formato de salida: exactamente 9 caracteres (los 8 primeros son enteros, el 9.º es la esfera). Usa X si un dígito rodillo es ilegible.
- Ejemplo: rodillos 00041907 y esfera que marca 9 → 000419079

Regla de ORO: Devuelve ÚNICAMENTE la cadena de dígitos (y X si aplica), sin espacios, comas, texto ni explicación. Longitud exacta: 9 tanto para Tipo A como para Tipo B."""

CIRCLE_DIAMETER_RATIO = 0.76


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
    return text


def recognize_from_bytes(image_bytes: bytes, meter_reading_type: Optional[str] = None) -> str:
    """
    Full pipeline: crop + OCR.  Returns the recognized reading string.
    """
    cropped = crop_to_circle_zone(image_bytes)
    return analyze_image(cropped, meter_reading_type=meter_reading_type)
