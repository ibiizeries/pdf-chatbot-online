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
from llm import embed_text, embed_texts_batch, generate_answer
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

    files = db.list_files()
    filenames = [f["filename"] for f in files]
    options = ["📚 ทุกคู่มือในคลัง"] + filenames
    selected = st.selectbox("เลือกขอบเขตที่จะถาม", options)
    scope_filename = None if selected == options[0] else selected

    if scope_filename:
        st.caption(f"🔒 กำลังถามเฉพาะคู่มือ **{scope_filename}** เท่านั้น คำตอบจะไม่ปนข้อมูลจากไฟล์อื่น")
    else:
        st.caption("กำลังค้นจากคู่มือทุกไฟล์ในคลัง")

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
                try:
                    query_embedding = embed_text(query, task_type="RETRIEVAL_QUERY")
                    retrieved = db.match_documents(query_embedding, match_count=5, source_filter=scope_filename)

                    if not retrieved:
                        if scope_filename:
                            answer = f"ไม่พบข้อมูลที่เกี่ยวข้องในคู่มือ '{scope_filename}' ครับ ลองเปลี่ยนคำถาม หรือสลับไปเลือก '📚 ทุกคู่มือในคลัง' ดู"
                        else:
                            answer = "ยังไม่มีเอกสารในคลัง หรือไม่พบข้อมูลที่เกี่ยวข้องเลยครับ"
                    else:
                        answer = generate_answer(query, retrieved, scope_filename=scope_filename)
                        with st.expander("🔍 ดูเนื้อหาอ้างอิงที่ใช้ตอบ"):
                            for chunk in retrieved:
                                meta = chunk["metadata"]
                                st.markdown(f"**{meta.get('source')} หน้า {meta.get('page')}** (ความเกี่ยวข้อง {chunk['similarity']:.2f})")
                                st.text(chunk["content"][:500])
                                st.divider()
                except Exception as e:
                    answer = f"เกิดข้อผิดพลาด: {e}"
                    st.error(answer)
                else:
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

    # รวมทุกชิ้นเนื้อหาจากทุกหน้าไว้ก่อน แล้วค่อย embed เป็นชุดๆ (ลดจำนวน request ไปหา Gemini มาก)
    all_chunks = []  # list of (page_num, chunk_text)
    for page_num, text in pages:
        for chunk in chunk_text(text):
            all_chunks.append((page_num, chunk))

    total_chunks = len(all_chunks)
    BATCH_SIZE = 20  # ส่ง 20 ชิ้นต่อ 1 request แทนที่จะส่งทีละชิ้น (314 ชิ้น -> ~16 request แทน 314 request)
    done = 0
    total_rows = 0

    for i in range(0, total_chunks, BATCH_SIZE):
        batch = all_chunks[i:i + BATCH_SIZE]
        texts = [c for _, c in batch]
        embeddings = embed_texts_batch(texts, task_type="RETRIEVAL_DOCUMENT")

        rows = [
            {
                "content": chunk,
                "metadata": {"source": filename, "page": page_num},
                "embedding": embedding,
            }
            for (page_num, chunk), embedding in zip(batch, embeddings)
        ]
        db.insert_chunks(rows)  # บันทึกทันทีทีละ batch กันข้อมูลหายถ้าไฟล์หลังๆ error
        total_rows += len(rows)

        done += len(batch)
        progress.progress(done / total_chunks, text=f"กำลังทำ index {filename} ({done}/{total_chunks})")

    db.register_pdf_file(filename, filename, page_count, total_rows)
    progress.empty()


# ---------------- routing ----------------
if page == "💬 แชทถามตอบ":
    chat_page()
else:
    library_page()
