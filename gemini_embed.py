"""
gemini_embed.py
----------------
Embedding ผ่าน Google Gemini API (โมเดล gemini-embedding-001, 768 มิติ)
แยกออกมาจาก llm.py (ซึ่งตอนนี้ใช้ Groq สำหรับส่วนตอบคำถามแทน)

รองรับ "หลาย API key" สลับอัตโนมัติ: ถ้า key แรกชนโควต้ารายวัน (RESOURCE_EXHAUSTED)
ระบบจะลอง key ถัดไปทันทีโดยไม่ต้องรอ (ปลอดภัยเพราะยังเป็นโมเดลเดียวกันเป๊ะ 768 มิติเท่ากัน
ไม่เหมือนการสลับไป embedding provider เจ้าอื่นที่จะทำให้เวกเตอร์เข้ากันไม่ได้กับของเดิม)

วิธีใส่หลาย key ใน secrets.toml:
    [gemini]
    api_keys = ["key-หลัก-ฟรี", "key-สำรอง-อาจเป็น key ที่เปิด billing แล้วก็ได้"]
(หรือใส่แบบเดิม api_key = "..." ตัวเดียวก็ยังใช้ได้ ระบบรองรับทั้งสองแบบ)
"""

import time
import streamlit as st
from google import genai
from google.genai import types
from google.genai.errors import ClientError

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768  # ต้องตรงกับ vector(768) ใน supabase_setup.sql


def _normalize_to_list(value):
    """แปลงค่าที่อ่านจาก secrets ให้เป็น list of string เสมอ ไม่ว่าผู้ใช้จะใส่มาเป็น
    string เดี่ยว หรือ list ก็ตาม (กันเผลอใส่ผิดฟอร์แมต เช่น api_key = ["a", "b"])
    """
    if isinstance(value, str):
        return [value]
    try:
        return list(value)
    except TypeError:
        return [value]


def _get_api_keys():
    """อ่านรายชื่อ API key จาก secrets รองรับทั้งแบบ list (api_keys) และแบบเดี่ยว (api_key)
    และรองรับกรณีใส่ list ผิดช่องด้วย (เผื่อพลาด)
    """
    gemini_secrets = st.secrets["gemini"]
    raw = None
    if "api_keys" in gemini_secrets:
        raw = gemini_secrets["api_keys"]
    elif "api_key" in gemini_secrets:
        raw = gemini_secrets["api_key"]

    if raw is None:
        raise RuntimeError("ยังไม่ได้ตั้งค่า Gemini API key ใน Secrets (ใส่ [gemini] api_key หรือ api_keys)")

    keys = [str(k).strip() for k in _normalize_to_list(raw) if k and str(k).strip()]
    if not keys:
        raise RuntimeError("ยังไม่ได้ตั้งค่า Gemini API key ใน Secrets (ใส่ [gemini] api_key หรือ api_keys)")
    return keys


@st.cache_resource
def _get_clients():
    return [genai.Client(api_key=k) for k in _get_api_keys()]


def _is_daily_quota_error(msg):
    """เช็คว่า error นี้เป็นโควต้า 'รายวัน' (รอ retry ไม่มีประโยชน์ ต้องสลับ key แทน)
    ต่างจากโควต้า 'ต่อนาที' ที่รอสักครู่แล้วลองใหม่กับ key เดิมได้
    """
    lower = msg.lower()
    return "perday" in lower.replace("_", "").replace(" ", "")


def _embed_with_retry(texts, task_type, max_retries=3):
    """ลอง embed ทีละ key ตามลำดับ ถ้า key ไหนชนโควต้ารายวัน สลับ key ถัดไปทันที
    ถ้าชนโควต้าต่อนาที รอ (backoff) แล้วลองซ้ำกับ key เดิมก่อน
    """
    clients = _get_clients()
    last_err = None

    for client in clients:
        delay = 15
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
                msg = str(e)
                last_err = e
                if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
                    if _is_daily_quota_error(msg):
                        break  # โควต้ารายวัน ไม่ต้องรอ ไปลอง key ถัดไปเลย
                    if attempt == max_retries - 1:
                        break  # โควต้าต่อนาที แต่ retry กับ key นี้ครบแล้ว ไปลอง key ถัดไป
                    time.sleep(delay)
                    delay = min(delay * 2, 60)
                    continue
                raise  # error อื่นที่ไม่ใช่ quota ไม่ต้องลอง key อื่น โยนออกไปเลย

    key_count = len(clients)
    raise RuntimeError(
        f"ใช้ Gemini API key ที่มีอยู่ทั้งหมด ({key_count} ตัว) แล้วแต่ยังชนโควต้าอยู่ "
        f"ลองใหม่ภายหลัง หรือเพิ่ม key สำรองใน Secrets: {last_err}"
    )


def embed_text(text, task_type="RETRIEVAL_DOCUMENT"):
    """แปลงข้อความ 1 ชิ้นเป็นเวกเตอร์ 768 มิติ (ใช้ตอนค้นหาจากคำถาม ซึ่งมีแค่ 1 ครั้งต่อคำถาม)"""
    return _embed_with_retry([text], task_type)[0]


def embed_texts_batch(texts, task_type="RETRIEVAL_DOCUMENT"):
    """แปลงข้อความหลายชิ้นพร้อมกันในคำขอเดียว (ลดจำนวน request ลงมาก ประหยัดโควต้ารายวัน)
    ใช้ตอน ingest ไฟล์ PDF ที่มีชิ้นเนื้อหาเยอะๆ
    """
    return _embed_with_retry(texts, task_type)
