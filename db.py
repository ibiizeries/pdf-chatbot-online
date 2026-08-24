"""
db.py
-----
รวมฟังก์ชันเชื่อมต่อ Supabase สำหรับ:
- อัพโหลด/ลบไฟล์ PDF ต้นฉบับใน Storage bucket
- เพิ่ม/ลบชิ้นเนื้อหา (chunk + embedding) ในตาราง documents
- ค้นหาชิ้นเนื้อหาที่เกี่ยวข้องกับคำถาม (match_documents)
- ดึงรายชื่อไฟล์ทั้งหมดในคลัง (สำหรับหน้าจัดการคลัง)
"""

import streamlit as st
from supabase import create_client

BUCKET_NAME = "pdfs"


@st.cache_resource
def get_client():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["service_key"]  # ใช้ service_role key เพราะแอปนี้จัดการเขียน/ลบข้อมูลเอง
    client = create_client(url, key)
    ensure_bucket_exists(client)
    return client


def ensure_bucket_exists(client):
    """สร้าง bucket 'pdfs' อัตโนมัติถ้ายังไม่มี กันปัญหาลืมสร้างเองผ่านหน้าเว็บ Supabase"""
    try:
        existing = [b.name for b in client.storage.list_buckets()]
        if BUCKET_NAME not in existing:
            client.storage.create_bucket(BUCKET_NAME, options={"public": False})
    except Exception as e:
        # ถ้าสร้างไม่สำเร็จ (เช่น key ไม่มีสิทธิ์) จะไปเจอ error ตอน upload อีกที ซึ่งจะเห็นข้อความชัดเจนกว่า
        st.warning(f"เช็ค/สร้าง storage bucket ไม่สำเร็จ: {e}")


def list_files():
    """คืนรายชื่อไฟล์ทั้งหมดในคลัง เรียงตามวันที่อัพโหลดล่าสุดก่อน"""
    client = get_client()
    result = client.table("pdf_files").select("*").order("uploaded_at", desc=True).execute()
    return result.data


def upload_pdf_file(filename, file_bytes):
    """อัพโหลดไฟล์ PDF ต้นฉบับเก็บไว้ใน Storage bucket"""
    client = get_client()
    storage_path = f"{filename}"
    try:
        client.storage.from_(BUCKET_NAME).upload(
            storage_path,
            file_bytes,
            file_options={"content-type": "application/pdf", "upsert": "true"},
        )
    except Exception as e:
        # โยน error พร้อมข้อความจริงออกมาให้เห็นในแอป แทนที่จะให้ Streamlit redact ทิ้ง
        raise RuntimeError(f"อัพโหลดไฟล์ '{filename}' ไม่สำเร็จ: {e}") from e
    return storage_path


def register_pdf_file(filename, storage_path, page_count, chunk_count):
    client = get_client()
    client.table("pdf_files").upsert({
        "filename": filename,
        "storage_path": storage_path,
        "page_count": page_count,
        "chunk_count": chunk_count,
    }, on_conflict="filename").execute()


def insert_chunks(rows):
    """rows: list of dict {content, metadata, embedding}"""
    client = get_client()
    # แทรกเป็นชุดๆ ละ 100 แถว กัน request ใหญ่เกินไป
    batch_size = 100
    for i in range(0, len(rows), batch_size):
        client.table("documents").insert(rows[i:i + batch_size]).execute()


def delete_file(filename):
    """ลบไฟล์ออกจากคลังทั้งหมด: ไฟล์ใน storage, ชิ้นเนื้อหาใน documents, และรายการใน pdf_files"""
    client = get_client()
    client.storage.from_(BUCKET_NAME).remove([filename])
    client.table("documents").delete().eq("metadata->>source", filename).execute()
    client.table("pdf_files").delete().eq("filename", filename).execute()


def match_documents(query_embedding, match_count=5, source_filter=None):
    """ค้นหาชิ้นเนื้อหาที่เกี่ยวข้องที่สุด
    source_filter: ถ้าระบุชื่อไฟล์ จะค้นเฉพาะในไฟล์นั้นไฟล์เดียว (ไม่ปนไฟล์อื่น)
    """
    client = get_client()
    # ถ้าต้องกรองเฉพาะไฟล์ ให้ดึงผลมาเยอะกว่าปกติก่อน แล้วค่อยกรอง+ตัดเหลือ match_count
    fetch_count = match_count * 6 if source_filter else match_count
    result = client.rpc("match_documents", {
        "query_embedding": query_embedding,
        "match_count": fetch_count,
    }).execute()
    data = result.data

    if source_filter:
        data = [row for row in data if row["metadata"].get("source") == source_filter]
        data = data[:match_count]

    return data
