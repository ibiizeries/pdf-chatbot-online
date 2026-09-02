"""
gemini_embed.py
----------------
Embedding ผ่าน Google Gemini API (โมเดล gemini-embedding-001, 768 มิติ)
แยกออกมาจาก llm.py (ซึ่งตอนนี้ใช้ Groq สำหรับส่วนตอบคำถามแทน)
มี retry อัตโนมัติเมื่อชน rate limit (429)
"""

import time
import streamlit as st
from google import genai
from google.genai import types
from google.genai.errors import ClientError

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768  # ต้องตรงกับ vector(768) ใน supabase_setup.sql


@st.cache_resource
def get_client():
    return genai.Client(api_key=st.secrets["gemini"]["api_key"])


def _embed_with_retry(client, texts, task_type, max_retries=5):
    """เรียก embed_content พร้อม retry แบบ exponential backoff เมื่อชน rate limit (429)"""
    delay = 20
    for attempt in range(max_retries):
        try:
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=EMBEDDING_DIM,
                ),
            )
            return [e.values for e in result.embeddings]
        except ClientError as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                if attempt == max_retries - 1:
                    raise
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise
    raise RuntimeError("เกินโควต้าซ้ำหลายครั้ง ลองใหม่อีกครั้งภายหลัง")


def embed_text(text, task_type="RETRIEVAL_DOCUMENT"):
    """แปลงข้อความ 1 ชิ้นเป็นเวกเตอร์ 768 มิติ (ใช้ตอนค้นหาจากคำถาม ซึ่งมีแค่ 1 ครั้งต่อคำถาม)"""
    client = get_client()
    return _embed_with_retry(client, [text], task_type)[0]


def embed_texts_batch(texts, task_type="RETRIEVAL_DOCUMENT"):
    """แปลงข้อความหลายชิ้นพร้อมกันในคำขอเดียว (ลดจำนวน request ลงมาก ประหยัดโควต้ารายวัน)
    ใช้ตอน ingest ไฟล์ PDF ที่มีชิ้นเนื้อหาเยอะๆ
    """
    client = get_client()
    return _embed_with_retry(client, texts, task_type)
