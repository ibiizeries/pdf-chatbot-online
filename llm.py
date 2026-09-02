"""
llm.py
------
ส่วนตอบคำถาม (chat/generation) ใช้ Google Gemini API (เหมือนส่วน embedding)
ใช้ API key ชุดเดียวกับ gemini_embed.py รองรับหลาย key สลับอัตโนมัติเมื่อชนโควต้ารายวัน
"""

import time
import json
import streamlit as st
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from gemini_embed import _get_api_keys

CHAT_MODEL = "gemini-3.6-flash"  # รุ่นปัจจุบันที่ Google แนะนำ (แทน gemini-2.5-flash ที่เลิกใช้แล้ว)

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
def _get_clients():
    return [genai.Client(api_key=k) for k in _get_api_keys()]


def _is_daily_quota_error(msg):
    lower = msg.lower()
    return "perday" in lower.replace("_", "").replace(" ", "")


def _generate_with_retry(prompt, system_instruction, max_retries=3):
    """ลองเรียก generate_content ทีละ key ตามลำดับ สลับ key อัตโนมัติเมื่อชนโควต้ารายวัน"""
    clients = _get_clients()
    last_err = None

    for client in clients:
        delay = 15
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=CHAT_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(system_instruction=system_instruction),
                )
                return response.text
            except ClientError as e:
                msg = str(e)
                last_err = e
                if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
                    if _is_daily_quota_error(msg):
                        break  # โควต้ารายวัน สลับ key ถัดไปเลย
                    if attempt == max_retries - 1:
                        break
                    time.sleep(delay)
                    delay = min(delay * 2, 60)
                    continue
                raise RuntimeError(f"เรียก Gemini ไม่สำเร็จ: {e}") from e

    key_count = len(clients)
    raise RuntimeError(
        f"ใช้ Gemini API key ที่มีอยู่ทั้งหมด ({key_count} ตัว) แล้วแต่ยังชนโควต้าอยู่ "
        f"ลองใหม่ภายหลัง: {last_err}"
    )


def expand_query(query, n=3):
    """ใช้โมเดลแชทช่วยตีความคำถามภาษาพูด แล้วสร้างคำค้นหาทางเลือกเพิ่มเติม
    เพื่อเพิ่มโอกาสค้นเจอเนื้อหาที่เกี่ยวข้อง แม้คู่มือจะใช้คำศัพท์/หัวข้อไม่ตรงกับคำถามเป๊ะๆ
    คืนค่า list ของคำค้นหาทางเลือก ถ้าล้มเหลวคืนค่า list ว่าง (ไม่กระทบการทำงานหลัก)
    """
    prompt = f"""ผู้ใช้ถามคำถามนี้กับคู่มือทางเทคนิค: "{query}"

ช่วยสร้างคำค้นหา (คำหรือวลีสั้นๆ) ที่มีความหมายใกล้เคียงหรือเกี่ยวข้องกับคำถามนี้ {n} แบบ
เพื่อเพิ่มโอกาสค้นเจอเนื้อหาที่เกี่ยวข้องในคู่มือ แม้คู่มือจะใช้คำศัพท์หรือชื่อหัวข้อไม่ตรงกับคำถามเป๊ะๆ
ตัวอย่าง: ถ้าถาม "การตรวจสอบระบบหล่อลื่นทำอย่างไร" อาจได้คำค้นหาเช่น "การหล่อลื่น", "จุดหล่อลื่น", "รอบการหล่อลื่น"

ตอบเป็น JSON array ของ string เท่านั้น ห้ามมีคำอธิบายหรือข้อความอื่นปน เช่น ["คำ1", "คำ2", "คำ3"]"""

    try:
        text = _generate_with_retry(prompt, system_instruction=None, max_retries=1).strip()
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

    return _generate_with_retry(prompt, system_instruction=SYSTEM_PROMPT + scope_instruction)
