from unittest.mock import patch
from pathlib import Path
from sn_lib.ocr import ocr_pdf

def test_ocr_pdf_concatenates_pages(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    with patch("sn_lib.ocr._render_pages", return_value=["img1", "img2"]), \
         patch("sn_lib.ocr._tesseract", side_effect=["hello", "world"]):
        out = ocr_pdf(pdf)
    assert "hello" in out and "world" in out
