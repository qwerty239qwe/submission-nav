from __future__ import annotations
from pathlib import Path

def _render_pages(pdf_path: Path) -> list:
    import fitz
    doc = fitz.open(str(pdf_path))
    imgs = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        imgs.append(pix.tobytes("png"))
    return imgs

def _tesseract(img_bytes) -> str:
    import io, pytesseract
    from PIL import Image
    if isinstance(img_bytes, (bytes, bytearray)):
        img = Image.open(io.BytesIO(img_bytes))
    else:
        img = img_bytes
    return pytesseract.image_to_string(img)

def ocr_pdf(path: str | Path) -> str:
    pages = _render_pages(Path(path))
    return "\n\n".join(_tesseract(p) for p in pages)
