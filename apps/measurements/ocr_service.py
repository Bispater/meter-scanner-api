from __future__ import annotations

import logging
from io import BytesIO
from typing import Optional

from django.conf import settings
from PIL import Image
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Placeholder replaced by "Tipo A" or "Tipo B" for Gemini.
_PROMPT_TEMPLATE = """Eres un experto en lectura de medidores de agua. Tu tarea es extraer la lectura exacta de 9 dígitos del medidor en la imagen, ignorando rayones o tinta negra. Si la tinta cubre un número, debes interpolar lógicamente su valor basándote en la posición física de los rodillos o agujas visibles.

Instrucciones según el tipo de medidor:

[CONFIGURACIÓN ACTIVA]: [AQUÍ_VA_LA_VARIABLE_DEL_TIPO]

Si la configuración es 'Tipo A':
El medidor tiene un contador superior de 5 rodillos (números enteros) y 4 esferas inferiores pequeñas (decimales).

Lee los 5 rodillos superiores (de izquierda a derecha).

Lee las 4 esferas inferiores (de izquierda a derecha, o en el orden que marquen los multiplicadores x0.1, x0.01, etc.).

Formato requerido: 9 dígitos seguidos. Ejemplo: Si arriba dice 00546 y abajo las agujas marcan 1, 2, 0, 6, debes devolver exactamente: 005461206.

Si la configuración es 'Tipo B':
El medidor tiene un contador superior de 8 rodillos (5 enteros en negro, una coma/separador, y 3 decimales en rojo) y 1 esfera inferior pequeña.

Lee los 8 rodillos superiores de izquierda a derecha.

Lee la única esfera inferior.

Formato requerido: 9 dígitos seguidos. Ejemplo: Si arriba dice 00546,120 y abajo marca 6, debes devolver exactamente: 005461206.

Regla de ORO: Devuelve ÚNICA Y EXCLUSIVAMENTE una cadena de 9 caracteres numéricos. Sin espacios, sin comas, sin puntos, sin texto adicional. Si por culpa de la tinta es humanamente imposible adivinar un número en particular, reemplaza ese único dígito con la letra 'X' (ej: 005461X06), pero mantén siempre la longitud de 9 caracteres."""

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
