"""
app.py
------
เว็บแอปหลัก ดีไซน์แชทบอทมินิมอลโทนส้ม:
- Sidebar: ปุ่มแนบคู่มือเพิ่ม (admin), รายชื่อคู่มือ (ใช้เป็นทั้งเมนูและตัวกรองขอบเขตคำถาม),
  จัดการคลังไฟล์ (admin), สลับธีม, ออกจากระบบ
- หน้าแชท: ถ้ายังไม่มีข้อความ โชว์หน้าต้อนรับ + การ์ดคำถามแนะนำ
  ถ้ามีข้อความ โชว์แชท ผู้ใช้ชิดขวา / ผู้ช่วยชิดซ้าย
Streamlit มีปุ่มหุบ/ขยาย sidebar ในตัวอยู่แล้ว (ลูกศรมุมบนซ้ายของ sidebar)
"""

import html
import streamlit as st
from auth import login_gate
from ingest_utils import extract_pages_from_bytes, chunk_text
from llm import embed_text, embed_texts_batch, generate_answer
from theme import get_css
import db

st.set_page_config(page_title="ผู้ช่วยคู่มือ AI", page_icon="📖", layout="wide")

if not login_gate():
    st.stop()

GENERAL_SCOPE = "__general__"

SUGGESTIONS = [
    ("🛠️", "วิธีบำรุงรักษาเบื้องต้นมีอะไรบ้าง"),
    ("⚙️", "ค่าพารามิเตอร์มาตรฐานที่ต้องตั้งคืออะไร"),
    ("🔍", "ขั้นตอนการติดตั้งอุปกรณ์ทำอย่างไร"),
    ("❓", "ถ้าเครื่องมีปัญหา ต้องแก้เบื้องต้นยังไง"),
]

# ---------------- state เริ่มต้น ----------------
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "current_scope" not in st.session_state:
    st.session_state.current_scope = GENERAL_SCOPE
if "chat_store" not in st.session_state:
    st.session_state.chat_store = {GENERAL_SCOPE: []}  # {scope_key: [messages]}
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

st.markdown(get_css(st.session_state.dark_mode), unsafe_allow_html=True)

is_admin = st.session_state.role == "admin"


# ---------------- dialog อัพโหลดไฟล์ (admin) ----------------
@st.dialog("แนบคู่มือเพิ่ม")
def upload_dialog():
    uploaded_files = st.file_uploader(
        "เลือกไฟล์ PDF (อัพโหลดได้หลายไฟล์พร้อมกัน)",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    st.caption("รองรับไฟล์ PDF")
    if uploaded_files and st.button("เริ่มประมวลผลและเพิ่มเข้าคลัง", type="primary", use_container_width=True):
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


# ---------------- Sidebar ----------------
def render_sidebar(files):
    with st.sidebar:
        st.markdown("## 📖 คู่มือของฉัน")

        if is_admin:
            st.markdown('<div class="attach-btn">', unsafe_allow_html=True)
            if st.button("＋  แนบคู่มือเพิ่ม", use_container_width=True, key="attach_btn"):
                upload_dialog()
            st.markdown('</div>', unsafe_allow_html=True)
            st.caption("รองรับไฟล์ PDF")

        st.markdown('<div class="sidebar-section-title">บทสนทนา</div>', unsafe_allow_html=True)

        # เมนู "คำถามทั่วไป" (คุยได้ทุกคู่มือ) ปักหมุดไว้บนสุดเสมอ
        active = st.session_state.current_scope == GENERAL_SCOPE
        if st.button("💬  คำถามทั่วไป", use_container_width=True, key="nav_general",
                     type="primary" if active else "secondary"):
            st.session_state.current_scope = GENERAL_SCOPE
            st.rerun()

        # รายชื่อคู่มือแต่ละเล่ม = ขอบเขตคำถามเฉพาะเล่มนั้น
        if files:
            for f in files:
                key = f["filename"]
                active = st.session_state.current_scope == key
                label = f"📄  {key}"
                if st.button(label, use_container_width=True, key=f"nav_{key}",
                             type="primary" if active else "secondary"):
                    st.session_state.current_scope = key
                    if key not in st.session_state.chat_store:
                        st.session_state.chat_store[key] = []
                    st.rerun()
        else:
            st.markdown('<div class="empty-hint">ยังไม่มีคู่มือ<br>แนบไฟล์เพื่อเริ่มต้น</div>', unsafe_allow_html=True)

        # จัดการคลังไฟล์ (ลบ) สำหรับ admin
        if is_admin and files:
            with st.expander("🗂️ จัดการคลังไฟล์"):
                for f in files:
                    c1, c2 = st.columns([4, 1])
                    c1.caption(f"{f['filename']} · {f.get('page_count', '-')} หน้า")
                    if c2.button("ลบ", key=f"del_{f['filename']}"):
                        db.delete_file(f["filename"])
                        st.session_state.chat_store.pop(f["filename"], None)
                        if st.session_state.current_scope == f["filename"]:
                            st.session_state.current_scope = GENERAL_SCOPE
                        st.success(f"ลบ {f['filename']} แล้ว")
                        st.rerun()

        st.write("")
        st.markdown("---")
        st.markdown(f"<span class='role-badge'>บทบาท: {st.session_state.role}</span>", unsafe_allow_html=True)

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


# ---------------- ตอบคำถาม ----------------
def answer_query(query, scope_filename, messages):
    messages.append({"role": "user", "content": query})
    try:
        query_embedding = embed_text(query, task_type="RETRIEVAL_QUERY")
        retrieved = db.match_documents(query_embedding, match_count=5, source_filter=scope_filename)

        if not retrieved:
            if scope_filename:
                answer = f"ไม่พบข้อมูลที่เกี่ยวข้องในคู่มือ '{scope_filename}' ครับ ลองเปลี่ยนคำถาม หรือสลับไปเลือก '💬 คำถามทั่วไป' ดู"
            else:
                answer = "ยังไม่มีเอกสารในคลัง หรือไม่พบข้อมูลที่เกี่ยวข้องเลยครับ"
            sources = []
        else:
            answer = generate_answer(query, retrieved, scope_filename=scope_filename)
            sources = retrieved
    except Exception as e:
        answer = f"เกิดข้อผิดพลาด: {e}"
        sources = []

    messages.append({"role": "assistant", "content": answer, "sources": sources})


# ---------------- หน้าแชท ----------------
def chat_page(files):
    scope = st.session_state.current_scope
    scope_filename = None if scope == GENERAL_SCOPE else scope
    if scope not in st.session_state.chat_store:
        st.session_state.chat_store[scope] = []
    messages = st.session_state.chat_store[scope]

    header = "คำถามทั่วไป (ทุกคู่มือ)" if scope_filename is None else scope_filename
    st.markdown(f"#### {'💬' if scope_filename is None else '📄'} {header}")

    if not messages:
        st.markdown(f"""
        <div class="welcome-wrap">
            <div class="welcome-icon">📖</div>
            <div class="welcome-title">สวัสดี ผมคือผู้ช่วยคู่มือ</div>
            <div class="welcome-sub">ถามอะไรก็ได้เกี่ยวกับคู่มือที่แนบไว้ ผมจะแปลและอธิบายให้ตรงตามต้นฉบับ เป็นภาษาไทยเสมอ</div>
        </div>
        """, unsafe_allow_html=True)

        cols = st.columns(2)
        for i, (icon, text) in enumerate(SUGGESTIONS):
            with cols[i % 2]:
                st.markdown('<div class="suggestion-card">', unsafe_allow_html=True)
                if st.button(f"{icon}  {text}", key=f"sugg_{i}", use_container_width=True):
                    st.session_state.pending_query = text
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        for msg in messages:
            if msg["role"] == "user":
                safe = html.escape(msg["content"])
                st.markdown(f'<div class="user-row"><div class="user-bubble">{safe}</div></div>', unsafe_allow_html=True)
            else:
                with st.chat_message("assistant", avatar="📖"):
                    st.markdown(msg["content"])
                    if msg.get("sources"):
                        with st.expander("🔍 ดูเนื้อหาอ้างอิงที่ใช้ตอบ"):
                            for chunk in msg["sources"]:
                                meta = chunk["metadata"]
                                st.markdown(f"**{meta.get('source')} หน้า {meta.get('page')}** (ความเกี่ยวข้อง {chunk['similarity']:.2f})")
                                st.text(chunk["content"][:500])
                                st.divider()

    # ประมวลผลคำถามจากการ์ดแนะนำ (ถ้ามี)
    if st.session_state.pending_query:
        q = st.session_state.pending_query
        st.session_state.pending_query = None
        with st.spinner("กำลังค้นหาและแปลเนื้อหาให้..."):
            answer_query(q, scope_filename, messages)
        st.rerun()

    query = st.chat_input("พิมพ์คำถามเกี่ยวกับคู่มือได้เลย...")
    if query:
        with st.spinner("กำลังค้นหาและแปลเนื้อหาให้..."):
            answer_query(query, scope_filename, messages)
        st.rerun()


# ---------------- routing ----------------
files = db.list_files()
render_sidebar(files)
chat_page(files)
