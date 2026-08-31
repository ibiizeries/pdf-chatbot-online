"""
llm.py
------
ส่วนตอบคำถาม (chat/generation) ใช้ Groq API แทน Google Gemini
เหตุผล: โควต้าฟรีของ Groq กว้างกว่ามาก (14,400 request/วัน, 30,000 token/นาที)
เหมาะกับตอนใช้งานจริงที่มีคนถามพร้อมกันหลายคน
(ส่วน embedding ย้ายไปรันแบบ local ทั้งหมดแล้ว ดูที่ local_embed.py)

โมเดลที่ใช้: openai/gpt-oss-120b (โมเดลที่ Groq แนะนำปัจจุบัน หลังเลิกใช้ llama-3.3-70b-versatile
ตั้งแต่กลางปี 2026) ให้คุณภาพดี รองรับหลายภาษารวมไทย
"""

import time
import json
import streamlit as st
from groq import Groq

CHAT_MODEL = "openai/gpt-oss-120b"  # ถ้าอยากได้เร็วขึ้น (แลกคุณภาพนิดหน่อย) เปลี่ยนเป็น "openai/gpt-oss-20b" ได้

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
    return Groq(api_key=st.secrets["groq"]["api_key"])


def _chat_with_retry(messages, max_retries=5):
    """เรียก chat completion พร้อม retry เมื่อชน rate limit (429) และโชว์ข้อความ error จริงถ้าพังด้วยสาเหตุอื่น"""
    client = get_client()
    delay = 15
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception as e:
            msg = str(e)
            if "429" in msg or "rate_limit" in msg.lower():
                if attempt == max_retries - 1:
                    raise RuntimeError(f"เกินโควต้าการใช้งานโมเดลแชท ลองใหม่อีกครั้งภายหลัง: {e}") from e
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise RuntimeError(f"เรียก Groq ไม่สำเร็จ: {e}") from e
    raise RuntimeError("เกินโควต้าซ้ำหลายครั้ง ลองใหม่อีกครั้งภายหลัง")


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
        text = _chat_with_retry([{"role": "user", "content": prompt}], max_retries=2).strip()
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

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + scope_instruction},
        {"role": "user", "content": prompt},
    ]
    return _chat_with_retry(messages)
