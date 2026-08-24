"""
app.py
------
เว็บแอปหลัก มี 2 หน้า:
- 💬 แชทถามตอบ: ทุกคนที่ล็อกอินเข้าได้
- 📚 จัดการคลังไฟล์: Admin เท่านั้น (อัพโหลด/ลบ PDF)
"""

import streamlit as st
from auth import login_gate, logout_button
from ingest_utils import extract_pages_from_bytes, chunk_text
from llm import embed_text, generate_answer
import db

st.set_page_config(page_title="AI Assistant - คู่มือองค์กร", page_icon="📄", layout="wide")

if not login_gate():
    st.stop()

st.sidebar.success(f"เข้าสู่ระบบในบทบาท: **{st.session_state.role}**")
logout_button()

is_admin = st.session_state.role == "admin"
pages = ["💬 แชทถามตอบ", "📚 คลังไฟล์"]
page = st.sidebar.radio("เมนู", pages)


# ---------------- หน้าแชท ----------------
def chat_page():
    st.title("📄 ผู้ช่วยตอบคำถามจากคู่มือ (ตอบเป็นภาษาไทย)")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    query = st.chat_input("พิมพ์คำถามเกี่ยวกับคู่มือได้เลย...")
    if query:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("กำลังค้นหาและสรุปคำตอบ..."):
                query_embedding = embed_text(query, task_type="retrieval_query")
                retrieved = db.match_documents(query_embedding, match_count=5)

                if not retrieved:
                    answer = "ยังไม่มีเอกสารในคลัง หรือไม่พบข้อมูลที่เกี่ยวข้องเลยครับ"
                else:
                    answer = generate_answer(query, retrieved)
                    with st.expander("🔍 ดูเนื้อหาอ้างอิงที่ใช้ตอบ"):
                        for chunk in retrieved:
                            meta = chunk["metadata"]
                            st.markdown(f"**{meta.get('source')} หน้า {meta.get('page')}** (ความเกี่ยวข้อง {chunk['similarity']:.2f})")
                            st.text(chunk["content"][:500])
                            st.divider()

                st.markdown(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})


# ---------------- หน้าคลังไฟล์ ----------------
def library_page():
    st.title("📚 คลังไฟล์ PDF")

    if is_admin:
        st.subheader("อัพโหลดไฟล์ใหม่")
        uploaded_files = st.file_uploader(
            "เลือกไฟล์ PDF (อัพโหลดได้หลายไฟล์พร้อมกัน)",
            type=["pdf"],
            accept_multiple_files=True,
        )
        if uploaded_files and st.button("เริ่มประมวลผลและเพิ่มเข้าคลัง"):
            success_count = 0
            for f in uploaded_files:
                try:
                    process_and_add_file(f)
                    success_count += 1
                except Exception as e:
                    st.error(f"❌ {f.name}: {e}")
            if success_count:
                st.success(f"เพิ่มไฟล์เข้าคลังสำเร็จ {success_count} ไฟล์")
                st.rerun()

        st.divider()

    st.subheader("ไฟล์ทั้งหมดในคลัง")
    files = db.list_files()
    if not files:
        st.info("ยังไม่มีไฟล์ในคลัง")
        return

    for f in files:
        col1, col2, col3, col4 = st.columns([4, 2, 2, 1])
        col1.write(f"📄 {f['filename']}")
        col2.write(f"{f.get('page_count', '-')} หน้า")
        col3.write(f"{f.get('chunk_count', '-')} ชิ้น")
        if is_admin:
            if col4.button("ลบ", key=f"del_{f['filename']}"):
                db.delete_file(f["filename"])
                st.success(f"ลบ {f['filename']} แล้ว")
                st.rerun()


def process_and_add_file(uploaded_file):
    file_bytes = uploaded_file.read()
    filename = uploaded_file.name

    progress = st.progress(0, text=f"กำลังอ่าน {filename}...")
    pages, page_count = extract_pages_from_bytes(file_bytes)

    if not pages:
        st.warning(f"{filename}: ดึงข้อความไม่ได้ (อาจเป็นไฟล์สแกน/รูปภาพ ต้องทำ OCR ก่อน) — ข้ามไฟล์นี้")
        return

    # เก็บไฟล์ต้นฉบับไว้ใน Storage
    db.upload_pdf_file(filename, file_bytes)

    rows = []
    total_chunks = sum(len(chunk_text(text)) for _, text in pages)
    done = 0

    for page_num, text in pages:
        for chunk in chunk_text(text):
            embedding = embed_text(chunk, task_type="retrieval_document")
            rows.append({
                "content": chunk,
                "metadata": {"source": filename, "page": page_num},
                "embedding": embedding,
            })
            done += 1
            progress.progress(done / total_chunks, text=f"กำลังทำ index {filename} ({done}/{total_chunks})")

    db.insert_chunks(rows)
    db.register_pdf_file(filename, filename, page_count, len(rows))
    progress.empty()


# ---------------- routing ----------------
if page == "💬 แชทถามตอบ":
    chat_page()
else:
    library_page()
