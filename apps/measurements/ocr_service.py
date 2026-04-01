import logging
from io import BytesIO

from django.conf import settings
from PIL import Image
import google.generativeai as genai

logger = logging.getLogger(__name__)

PROMPT = (
    'Eres un sistema automatizado experto en lectura de medidores de agua. '
    'Tu única tarea es extraer el número del consumo de agua actual. '
    'Reglas: '
    '1. Busca los números principales en los rodillos o diales centrales. '
    '2. Ignora por completo cualquier número de serie impreso en la carcasa. '
    '3. Ignora marcas de rotulador o marcador negro escritas sobre el cristal. '
    '4. Devuelve ÚNICAMENTE los dígitos de la lectura (incluyendo ceros a la '
    'izquierda si los hay). No agregues texto, ni explicaciones, ni unidades como m3.'
)

CIRCLE_DIAMETER_RATIO = 0.76


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


def analyze_image(image_bytes: bytes) -> str:
    """
    Send image bytes to Gemini and return the recognized reading text.
    """
    model = _get_model()

    response = model.generate_content([
        PROMPT,
        {'mime_type': 'image/jpeg', 'data': image_bytes},
    ])

    text = (response.text or '').strip()
    logger.info('Gemini response: "%s" (%d bytes image)', text, len(image_bytes))

    if not text:
        raise ValueError('Gemini devolvió respuesta vacía')
    return text


def recognize_from_bytes(image_bytes: bytes) -> str:
    """
    Full pipeline: crop + OCR.  Returns the recognized reading string.
    """
    cropped = crop_to_circle_zone(image_bytes)
    return analyze_image(cropped)
