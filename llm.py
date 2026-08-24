"""
llm.py
------
รวมฟังก์ชันเรียก Google Gemini API สำหรับ:
- embed_text: แปลงข้อความเป็นเวกเตอร์ (ใช้ทั้งตอน ingest และตอนค้นหา)
- generate_answer: ให้ Gemini สรุปตอบคำถามเป็นภาษาไทย จากเนื้อหาที่ค้นมาได้
"""

import streamlit as st
import google.generativeai as genai

genai.configure(api_key=st.secrets["gemini"]["api_key"])

EMBEDDING_MODEL = "models/text-embedding-004"   # 768 มิติ, รองรับหลายภาษารวมไทย, ฟรี
CHAT_MODEL = "gemini-2.0-flash"                 # เร็ว, ฟรี (โควต้าเยอะพอสำหรับใช้งานภายใน), รองรับไทยดี

SYSTEM_PROMPT = """คุณคือผู้ช่วยตอบคำถามจากคู่มือ/เอกสารขององค์กร
กติกาสำคัญ:
1. ตอบเป็นภาษาไทยเสมอ ไม่ว่าเนื้อหาต้นฉบับที่ให้มาจะเป็นภาษาอะไรก็ตาม (อังกฤษ จีน ญี่ปุ่น ฯลฯ) ให้แปล/สรุปเป็นไทย
2. ใช้ข้อมูลจาก "เนื้อหาอ้างอิง" ที่ให้มาเท่านั้น ห้ามเดาหรือแต่งเติมข้อมูลที่ไม่มีในเนื้อหา
3. ถ้าเนื้อหาอ้างอิงไม่มีคำตอบ ให้บอกตรงๆ ว่าไม่พบข้อมูลในเอกสาร อย่าแต่งคำตอบขึ้นมาเอง
4. ท้ายคำตอบให้ระบุแหล่งที่มาสั้นๆ เช่น (อ้างอิง: ชื่อไฟล์.pdf หน้า 12)
"""


def embed_text(text, task_type="retrieval_document"):
    """แปลงข้อความ 1 ชิ้นเป็นเวกเตอร์ 768 มิติ
    task_type: 'retrieval_document' ตอน ingest เก็บเข้าคลัง, 'retrieval_query' ตอนค้นหาจากคำถาม
    """
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type=task_type,
    )
    return result["embedding"]


def generate_answer(query, retrieved_chunks):
    """retrieved_chunks: list of dict {content, metadata} ที่ค้นมาได้จาก Supabase"""
    context_blocks = []
    for chunk in retrieved_chunks:
        meta = chunk["metadata"]
        context_blocks.append(
            f"[แหล่งที่มา: {meta.get('source')} หน้า {meta.get('page')}]\n{chunk['content']}"
        )
    context = "\n\n---\n\n".join(context_blocks)

    prompt = f"""{SYSTEM_PROMPT}

เนื้อหาอ้างอิง:
{context}

คำถาม: {query}

ตอบเป็นภาษาไทย:"""

    model = genai.GenerativeModel(CHAT_MODEL)
    response = model.generate_content(prompt)
    return response.text
