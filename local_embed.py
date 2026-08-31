"""
local_embed.py
---------------
Embedding แบบ local รันในตัวแอปเอง ไม่เรียก API ภายนอก จึงไม่มีโควต้าให้ชนอีกเลย
ใช้ไลบรารี fastembed (ONNX รันบน CPU, เบา ไม่ต้องใช้ GPU) กับโมเดล
intfloat/multilingual-e5-small (384 มิติ) รองรับหลายภาษารวมถึงไทย
"""

import streamlit as st
from fastembed import TextEmbedding
from fastembed.common.model_description import PoolingType, ModelSource

MODEL_NAME = "intfloat/multilingual-e5-small"
EMBEDDING_DIM = 384  # ต้องตรงกับ vector(384) ใน supabase_setup.sql


def _ensure_model_registered():
    """ลงทะเบียนโมเดล multilingual-e5-small กับ fastembed (ไม่ได้อยู่ในลิสต์ default)
    เรียกซ้ำได้ปลอดภัย ถ้าเคยลงทะเบียนแล้วจะข้ามไปเงียบๆ
    """
    try:
        TextEmbedding.add_custom_model(
            model=MODEL_NAME,
            pooling=PoolingType.MEAN,
            normalization=True,
            sources=ModelSource(hf=MODEL_NAME),
            dim=EMBEDDING_DIM,
            model_file="onnx/model.onnx",
        )
    except Exception:
        pass  # เคยลงทะเบียนไปแล้วในเซสชันนี้


@st.cache_resource
def get_model():
    """โหลดโมเดลครั้งเดียวแล้ว cache ไว้ (ดาวน์โหลดไฟล์โมเดล ~0.1-0.3GB ตอนแรกที่เรียกใช้)"""
    _ensure_model_registered()
    return TextEmbedding(model_name=MODEL_NAME)


def embed_text(text, task_type="RETRIEVAL_DOCUMENT"):
    """แปลงข้อความ 1 ชิ้นเป็นเวกเตอร์ 384 มิติ"""
    return embed_texts_batch([text], task_type)[0]


def embed_texts_batch(texts, task_type="RETRIEVAL_DOCUMENT"):
    """แปลงข้อความหลายชิ้นพร้อมกัน (รันในเครื่อง ไม่มีโควต้า ไม่มี rate limit)
    task_type: 'RETRIEVAL_DOCUMENT' ตอน ingest เก็บเข้าคลัง, 'RETRIEVAL_QUERY' ตอนค้นหาจากคำถาม
    (โมเดล e5 ต้องมี prefix "passage: " / "query: " กำกับตามชนิดงาน ตามที่ถูกเทรนมา)
    """
    model = get_model()
    prefix = "query: " if task_type == "RETRIEVAL_QUERY" else "passage: "
    prefixed = [f"{prefix}{t}" for t in texts]
    embeddings = list(model.embed(prefixed))
    return [e.tolist() for e in embeddings]
