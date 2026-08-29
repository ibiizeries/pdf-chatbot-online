"""
llm.py
------
รวมฟังก์ชันเรียก Google Gemini API สำหรับ:
- embed_text: แปลงข้อความเป็นเวกเตอร์ (ใช้ทั้งตอน ingest และตอนค้นหา)
- generate_answer: ให้ Gemini สรุปตอบคำถามเป็นภาษาไทย จากเนื้อหาที่ค้นมาได้

หมายเหตุ: ใช้ SDK ตัวใหม่ "google-genai" (ตัวเก่า "google-generativeai" และโมเดล
"text-embedding-004" ถูก Google เลิกใช้แล้ว)
"""

import time
import json
import streamlit as st
from google import genai
from google.genai import types
from google.genai.errors import ClientError

EMBEDDING_MODEL = "gemini-embedding-001"  # รุ่นปัจจุบัน (แทน text-embedding-004 ที่เลิกใช้แล้ว), รองรับไทย
EMBEDDING_DIM = 768                        # ต้องตรงกับ vector(768) ใน supabase_setup.sql
CHAT_MODEL = "gemini-3.6-flash"            # เร็ว, ฟรี (โควต้าเยอะพอสำหรับใช้งานภายใน), รองรับไทยดี

SYSTEM_PROMPT = """คุณคือผู้ช่วยตอบคำถามจากคู่มือ/เอกสารขององค์กร
กติกาสำคัญ:
1. ตอบเป็นภาษาไทยเสมอ ไม่ว่าเนื้อหาต้นฉบับที่ให้มาจะเป็นภาษาอะไรก็ตาม (อังกฤษ จีน ญี่ปุ่น ฯลฯ) ให้แปลเป็นไทย
2. แปลแบบตรงตามต้นฉบับ (verbatim) ห้ามสรุปย่อ ห้ามตัดทอนรายละเอียด ห้ามเลือกเอาแค่บางประเด็นมาเล่า
   - ถ้าต้นฉบับมีขั้นตอน ให้แปลครบทุกขั้นตอนตามลำดับเดิม
   - ถ้าต้นฉบับมีตัวเลข/ค่าพารามิเตอร์/ชื่อชิ้นส่วนเฉพาะ ให้คงไว้ครบถ้วนแม่นยำ ห้ามปัดหรือประมาณ
   - ถ้าต้นฉบับมีรายการ (list) ให้แปลออกมาเป็นรายการครบทุกข้อ ไม่รวบเป็นประโยคสรุป
   - คงโครงสร้างของต้นฉบับไว้ (หัวข้อ ลำดับข้อ) ให้มากที่สุด เพียงแค่แปลงเป็นภาษาไทย ไม่ใช่การเรียบเรียงใหม่
3. ใช้ข้อมูลจาก "เนื้อหาอ้างอิง" ที่ให้มาเท่านั้น ห้ามเดาหรือแต่งเติมข้อมูลที่ไม่มีในเนื้อหา
4. ถ้าเนื้อหาอ้างอิงไม่มีคำตอบ ให้บอกตรงๆ ว่าไม่พบข้อมูลในเอกสาร อย่าแต่งคำตอบขึ้นมาเอง
5. ท้ายคำตอบให้ระบุแหล่งที่มาสั้นๆ เช่น (อ้างอิง: ชื่อไฟล์.pdf หน้า 12)
"""


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
    """แปลงข้อความ 1 ชิ้นเป็นเวกเตอร์ 768 มิติ (ใช้ตอนค้นหาจากคำถาม ซึ่งมีแค่ 1 ครั้งต่อคำถาม)
    task_type: 'RETRIEVAL_DOCUMENT' ตอน ingest เก็บเข้าคลัง, 'RETRIEVAL_QUERY' ตอนค้นหาจากคำถาม
    """
    client = get_client()
    return _embed_with_retry(client, [text], task_type)[0]


def embed_texts_batch(texts, task_type="RETRIEVAL_DOCUMENT"):
    """แปลงข้อความหลายชิ้นพร้อมกันในคำขอเดียว (ลดจำนวน request ลงมาก เทียบกับส่งทีละชิ้น)
    ใช้ตอน ingest ไฟล์ PDF ที่มีชิ้นเนื้อหาเยอะๆ
    """
    client = get_client()
    return _embed_with_retry(client, texts, task_type)


def expand_query(query, n=3):
    """ใช้ Gemini ช่วยตีความคำถามภาษาพูด แล้วสร้างคำค้นหาทางเลือกเพิ่มเติม
    เพื่อเพิ่มโอกาสค้นเจอเนื้อหาที่เกี่ยวข้อง แม้คู่มือจะใช้คำศัพท์/หัวข้อไม่ตรงกับคำถามเป๊ะๆ
    เช่น ถามว่า "ตรวจสอบระบบหล่อลื่นทำอย่างไร" แต่คู่มือใช้หัวข้อว่า "8.3 การหล่อลื่น"
    คืนค่า list ของคำค้นหาทางเลือก (ไม่รวมคำถามต้นฉบับ) ถ้าล้มเหลวคืนค่า list ว่าง (ไม่กระทบการทำงานหลัก)
    """
    client = get_client()
    prompt = f"""ผู้ใช้ถามคำถามนี้กับคู่มือทางเทคนิค: "{query}"

ช่วยสร้างคำค้นหา (คำหรือวลีสั้นๆ) ที่มีความหมายใกล้เคียงหรือเกี่ยวข้องกับคำถามนี้ {n} แบบ
เพื่อเพิ่มโอกาสค้นเจอเนื้อหาที่เกี่ยวข้องในคู่มือ แม้คู่มือจะใช้คำศัพท์หรือชื่อหัวข้อไม่ตรงกับคำถามเป๊ะๆ
ตัวอย่าง: ถ้าถาม "การตรวจสอบระบบหล่อลื่นทำอย่างไร" อาจได้คำค้นหาเช่น "การหล่อลื่น", "จุดหล่อลื่น", "รอบการหล่อลื่น"

ตอบเป็น JSON array ของ string เท่านั้น ห้ามมีคำอธิบายหรือข้อความอื่นปน เช่น ["คำ1", "คำ2", "คำ3"]"""

    try:
        response = client.models.generate_content(model=CHAT_MODEL, contents=prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if "\n" in text:
                text = text.split("\n", 1)[1]
        alternatives = json.loads(text)
        if isinstance(alternatives, list):
            return [str(a).strip() for a in alternatives if str(a).strip()][:n]
    except Exception:
        pass
    return []


def generate_answer(query, retrieved_chunks, scope_filename=None):
    """retrieved_chunks: list of dict {content, metadata} ที่ค้นมาได้จาก Supabase
    scope_filename: ถ้าระบุ จะเน้นย้ำให้ AI ตอบจากคู่มือไฟล์นี้เท่านั้น ห้ามใช้ข้อมูลจากไฟล์อื่นปนมาตอบ
    """
    client = get_client()

    context_blocks = []
    for chunk in retrieved_chunks:
        meta = chunk["metadata"]
        context_blocks.append(
            f"[แหล่งที่มา: {meta.get('source')} หน้า {meta.get('page')}]\n{chunk['content']}"
        )
    context = "\n\n---\n\n".join(context_blocks)

    scope_instruction = ""
    if scope_filename:
        scope_instruction = (
            f"\n5. ผู้ใช้เลือกถามเฉพาะคู่มือ '{scope_filename}' เท่านั้น "
            f"เนื้อหาอ้างอิงที่ให้มาด้านล่างทั้งหมดมาจากไฟล์นี้อยู่แล้ว "
            f"ห้ามอ้างอิงหรือปนข้อมูลจากคู่มือ/ไฟล์อื่นเข้ามาตอบเด็ดขาด "
            f"ถ้าคำถามนี้ไม่มีคำตอบอยู่ในคู่มือ '{scope_filename}' ให้บอกตรงๆ ว่าไม่พบในคู่มือเล่มนี้ "
            f"(ต่อให้รู้คำตอบจากคู่มือเล่มอื่นก็ห้ามตอบ)"
        )

    prompt = f"""เนื้อหาอ้างอิง:
{context}

คำถาม: {query}

ตอบเป็นภาษาไทย โดยแปลเนื้อหาที่เกี่ยวข้องแบบตรงตามต้นฉบับ ครบถ้วน ไม่สรุปย่อ:"""

    response = _generate_with_retry(client, prompt, extra_system_instruction=scope_instruction)
    return response.text


def _generate_with_retry(client, prompt, extra_system_instruction="", max_retries=5):
    """เรียก generate_content พร้อม retry เมื่อชน rate limit และโชว์ข้อความ error จริงถ้าพังด้วยสาเหตุอื่น"""
    system_instruction = SYSTEM_PROMPT + extra_system_instruction
    delay = 20
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model=CHAT_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=system_instruction),
            )
        except ClientError as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                if attempt == max_retries - 1:
                    raise RuntimeError(f"เกินโควต้าการใช้งานโมเดลแชท ลองใหม่อีกครั้งภายหลัง: {e}") from e
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            # error อื่นที่ไม่ใช่ rate limit (เช่น ชื่อโมเดลผิด, API key ผิด) โยนข้อความจริงออกไปเลย
            raise RuntimeError(f"เรียก Gemini ไม่สำเร็จ: {e}") from e
