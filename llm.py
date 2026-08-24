"""
llm.py
------
รวมฟังก์ชันเรียก Google Gemini API สำหรับ:
- embed_text: แปลงข้อความเป็นเวกเตอร์ (ใช้ทั้งตอน ingest และตอนค้นหา)
- generate_answer: ให้ Gemini สรุปตอบคำถามเป็นภาษาไทย จากเนื้อหาที่ค้นมาได้

หมายเหตุ: ใช้ SDK ตัวใหม่ "google-genai" (ตัวเก่า "google-generativeai" และโมเดล
"text-embedding-004" ถูก Google เลิกใช้แล้ว)
"""

import streamlit as st
from google import genai
from google.genai import types

EMBEDDING_MODEL = "gemini-embedding-001"  # รุ่นปัจจุบัน (แทน text-embedding-004 ที่เลิกใช้แล้ว), รองรับไทย
EMBEDDING_DIM = 768                        # ต้องตรงกับ vector(768) ใน supabase_setup.sql
CHAT_MODEL = "gemini-2.5-flash"            # เร็ว, ฟรี (โควต้าเยอะพอสำหรับใช้งานภายใน), รองรับไทยดี

SYSTEM_PROMPT = """คุณคือผู้ช่วยตอบคำถามจากคู่มือ/เอกสารขององค์กร
กติกาสำคัญ:
1. ตอบเป็นภาษาไทยเสมอ ไม่ว่าเนื้อหาต้นฉบับที่ให้มาจะเป็นภาษาอะไรก็ตาม (อังกฤษ จีน ญี่ปุ่น ฯลฯ) ให้แปล/สรุปเป็นไทย
2. ใช้ข้อมูลจาก "เนื้อหาอ้างอิง" ที่ให้มาเท่านั้น ห้ามเดาหรือแต่งเติมข้อมูลที่ไม่มีในเนื้อหา
3. ถ้าเนื้อหาอ้างอิงไม่มีคำตอบ ให้บอกตรงๆ ว่าไม่พบข้อมูลในเอกสาร อย่าแต่งคำตอบขึ้นมาเอง
4. ท้ายคำตอบให้ระบุแหล่งที่มาสั้นๆ เช่น (อ้างอิง: ชื่อไฟล์.pdf หน้า 12)
"""


@st.cache_resource
def get_client():
    return genai.Client(api_key=st.secrets["gemini"]["api_key"])


def embed_text(text, task_type="RETRIEVAL_DOCUMENT"):
    """แปลงข้อความ 1 ชิ้นเป็นเวกเตอร์ 768 มิติ
    task_type: 'RETRIEVAL_DOCUMENT' ตอน ingest เก็บเข้าคลัง, 'RETRIEVAL_QUERY' ตอนค้นหาจากคำถาม
    """
    client = get_client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    return result.embeddings[0].values


def generate_answer(query, retrieved_chunks):
    """retrieved_chunks: list of dict {content, metadata} ที่ค้นมาได้จาก Supabase"""
    client = get_client()

    context_blocks = []
    for chunk in retrieved_chunks:
        meta = chunk["metadata"]
        context_blocks.append(
            f"[แหล่งที่มา: {meta.get('source')} หน้า {meta.get('page')}]\n{chunk['content']}"
        )
    context = "\n\n---\n\n".join(context_blocks)

    prompt = f"""เนื้อหาอ้างอิง:
{context}

คำถาม: {query}

ตอบเป็นภาษาไทย:"""

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )
    return response.text
