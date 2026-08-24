"""
app.py
------
เว็บแอปหลัก ดีไซน์แบบมินิมอลคล้าย Claude มี 2 หน้า:
- 🏠 Home (แชทถามตอบ): ทุกคนที่ล็อกอินเข้าได้ มีปุ่ม New Chat + ประวัติแชทในเซสชัน
- 📁 คลังไฟล์: Admin จัดการอัพโหลด/ลบ PDF, User ดูได้อย่างเดียว
มีปุ่มสลับ Light / Dark mode ในไซด์บาร์
"""

import uuid
import streamlit as st
from auth import login_gate
from ingest_utils import extract_pages_from_bytes, chunk_text
from llm import embed_text, embed_texts_batch, generate_answer
from theme import get_css
import db

st.set_page_config(page_title="AI Assistant - คู่มือองค์กร", page_icon="📄", layout="wide")

if not login_gate():
    st.stop()

# ---------------- state เริ่มต้น ----------------
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {}  # {id: {"title": str, "messages": [...]}}
if "current_chat_id" not in st.session_state:
    new_id = str(uuid.uuid4())
    st.session_state.chat_sessions[new_id] = {"title": "แชทใหม่", "messages": []}
    st.session_state.current_chat_id = new_id

st.markdown(get_css(st.session_state.dark_mode), unsafe_allow_html=True)

is_admin = st.session_state.role == "admin"


# ---------------- Sidebar ----------------
def render_sidebar():
    with st.sidebar:
        st.markdown("### 📄 คู่มือ AI")
        st.markdown(f"<span class='role-badge'>บทบาท: {st.session_state.role}</span>", unsafe_allow_html=True)

        if st.button("＋ New Chat", use_container_width=True, type="primary"):
            new_id = str(uuid.uuid4())
            st.session_state.chat_sessions[new_id] = {"title": "แชทใหม่", "messages": []}
            st.session_state.current_chat_id = new_id
            st.session_state.current_page = "home"
            st.rerun()

        st.write("")

        # --- Nav: Home / คลังไฟล์ ---
        if st.button("🏠  Home", use_container_width=True,
                      type="primary" if st.session_state.current_page == "home" else "secondary"):
            st.session_state.current_page = "home"
            st.rerun()
        if st.button("📁  คลังไฟล์", use_container_width=True,
                      type="primary" if st.session_state.current_page == "library" else "secondary"):
            st.session_state.current_page = "library"
            st.rerun()

        # --- ประวัติแชท (เฉพาะตอนอยู่หน้า Home) ---
        if st.session_state.current_page == "home":
            st.markdown("<div class='chat-history-title'>ประวัติแชท (เซสชันนี้)</div>", unsafe_allow_html=True)
            # เรียงจากล่าสุดไปเก่าสุด
            for chat_id in reversed(list(st.session_state.chat_sessions.keys())):
                session = st.session_state.chat_sessions[chat_id]
                label = session["title"][:28] + ("…" if len(session["title"]) > 28 else "")
                is_active = chat_id == st.session_state.current_chat_id
                if st.button(label, key=f"hist_{chat_id}", use_container_width=True,
                             type="primary" if is_active else "secondary"):
                    st.session_state.current_chat_id = chat_id
                    st.rerun()

        st.write("")
        st.markdown("---")

        # --- ธีม + ออกจากระบบ ---
        col1, col2 = st.columns(2)
        with col1:
            icon = "🌙" if not st.session_state.dark_mode else "☀️"
            if st.button(f"{icon} โหมด", use_container_width=True):
                st.session_state.dark_mode = not st.session_state.dark_mode
                st.rerun()
        with col2:
            if st.button("ออกจากระบบ", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.role = None
                st.rerun()


# ---------------- หน้า Home (แชท) ----------------
def home_page():
    st.title("ผู้ช่วยตอบคำถามจากคู่มือ")
    st.caption("ตอบเป็นภาษาไทยเสมอ แปลตรงตามต้นฉบับ ไม่สรุปย่อ")

    files = db.list_files()
    filenames = [f["filename"] for f in files]
    options = ["📚 ทุกคู่มือในคลัง"] + filenames
    selected = st.selectbox("เลือกขอบเขตที่จะถาม", options, label_visibility="collapsed")
    scope_filename = None if selected == options[0] else selected

    if scope_filename:
        st.caption(f"🔒 กำลังถามเฉพาะคู่มือ **{scope_filename}** เท่านั้น คำตอบจะไม่ปนข้อมูลจากไฟล์อื่น")
    else:
        st.caption("กำลังค้นจากคู่มือทุกไฟล์ในคลัง")

    session = st.session_state.chat_sessions[st.session_state.current_chat_id]
    messages = session["messages"]

    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    query = st.chat_input("พิมพ์คำถามเกี่ยวกับคู่มือได้เลย...")
    if query:
        messages.append({"role": "user", "content": query})
        if session["title"] == "แชทใหม่":
            session["title"] = query
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("กำลังค้นหาและแปลเนื้อหาให้..."):
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

        messages.append({"role": "assistant", "content": answer})


# ---------------- หน้าคลังไฟล์ ----------------
def library_page():
    st.title("คลังไฟล์ PDF")

    if is_admin:
        st.subheader("อัพโหลดไฟล์ใหม่")
        uploaded_files = st.file_uploader(
            "เลือกไฟล์ PDF (อัพโหลดได้หลายไฟล์พร้อมกัน)",
            type=["pdf"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
        if uploaded_files and st.button("เริ่มประมวลผลและเพิ่มเข้าคลัง", type="primary"):
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

    db.upload_pdf_file(filename, file_bytes)

    all_chunks = []
    for page_num, text in pages:
        for chunk in chunk_text(text):
            all_chunks.append((page_num, chunk))

    total_chunks = len(all_chunks)
    BATCH_SIZE = 20
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
        db.insert_chunks(rows)
        total_rows += len(rows)

        done += len(batch)
        progress.progress(done / total_chunks, text=f"กำลังทำ index {filename} ({done}/{total_chunks})")

    db.register_pdf_file(filename, filename, page_count, total_rows)
    progress.empty()


# ---------------- routing ----------------
render_sidebar()

if st.session_state.current_page == "home":
    home_page()
else:
    library_page()
