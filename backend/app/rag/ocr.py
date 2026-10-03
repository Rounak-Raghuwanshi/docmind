import io
import logging
import shutil
from functools import lru_cache

log = logging.getLogger(__name__)


@lru_cache
def tesseract_available() -> bool:
    available = shutil.which("tesseract") is not None
    if not available:
        log.warning("tesseract not found on PATH; scanned pages will be skipped")
    return available


def ocr_png(png_bytes: bytes) -> str:
    import pytesseract
    from PIL import Image

    with Image.open(io.BytesIO(png_bytes)) as img:
        return str(pytesseract.image_to_string(img, lang="eng"))
