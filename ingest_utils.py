"""
ingest_utils.py
----------------
ฟังก์ชันช่วยแตกข้อความจาก PDF และแบ่งเป็นชิ้นเล็กๆ (chunk)
ใช้ทั้งใน app.py ตอน Admin อัพโหลดไฟล์ผ่านหน้าเว็บ
"""

import fitz  # PyMuPDF

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


def extract_pages_from_bytes(file_bytes):
    """คืนค่า list ของ (page_number, text) จาก PDF ที่อยู่ในรูป bytes (จากการอัพโหลด)"""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            pages.append((i + 1, text))
    page_count = doc.page_count
    doc.close()
    return pages, page_count


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == length:
            break
        start = end - overlap
    return chunks
