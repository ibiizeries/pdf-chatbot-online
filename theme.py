"""
theme.py
--------
CSS สำหรับปรับหน้าตาแอปให้มินิมอลแบบ Claude — สี, ฟอนต์, sidebar, ปุ่ม, กล่องแชท
รองรับ Light / Dark mode ผ่าน st.session_state.dark_mode
"""

LIGHT = {
    "bg": "#FAF9F5",
    "bg_secondary": "#F0EEE6",
    "sidebar_bg": "#F0EEE6",
    "text": "#1F1E1D",
    "text_muted": "#6B6A66",
    "border": "#E5E2D9",
    "accent": "#CC785C",
    "accent_hover": "#B96548",
    "accent_text": "#FFFFFF",
    "card_bg": "#FFFFFF",
    "user_bubble": "#EDE9DE",
    "assistant_bubble": "#FFFFFF",
    "nav_active_bg": "#E5E2D9",
}

DARK = {
    "bg": "#262624",
    "bg_secondary": "#1F1E1C",
    "sidebar_bg": "#1F1E1C",
    "text": "#F5F4EF",
    "text_muted": "#A8A6A0",
    "border": "#3A3935",
    "accent": "#CC785C",
    "accent_hover": "#DA8A6E",
    "accent_text": "#FFFFFF",
    "card_bg": "#2D2C2A",
    "user_bubble": "#33322F",
    "assistant_bubble": "#2D2C2A",
    "nav_active_bg": "#33322F",
}


def get_css(dark_mode: bool) -> str:
    c = DARK if dark_mode else LIGHT
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}}

/* พื้นหลังหลัก */
.stApp {{
    background-color: {c["bg"]};
    color: {c["text"]};
}}

/* ซ่อนเมนู/ฟุตเตอร์เริ่มต้นของ Streamlit ให้ดูมินิมอลขึ้น */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header[data-testid="stHeader"] {{background: transparent;}}

/* Sidebar */
[data-testid="stSidebar"] {{
    background-color: {c["sidebar_bg"]};
    border-right: 1px solid {c["border"]};
}}
[data-testid="stSidebar"] > div:first-child {{
    padding-top: 1.2rem;
}}

/* หัวข้อ / ข้อความ */
h1, h2, h3, h4, h5, h6 {{
    color: {c["text"]} !important;
    font-weight: 600 !important;
}}
p, span, label, .stMarkdown {{
    color: {c["text"]};
}}
.stCaption, [data-testid="stCaptionContainer"] {{
    color: {c["text_muted"]} !important;
}}

/* ปุ่มทั่วไป */
.stButton > button {{
    border-radius: 10px;
    border: 1px solid {c["border"]};
    background-color: {c["card_bg"]};
    color: {c["text"]};
    font-weight: 500;
    transition: all 0.15s ease;
}}
.stButton > button:hover {{
    border-color: {c["accent"]};
    color: {c["accent"]};
}}

/* ปุ่มหลัก (primary) เช่น New Chat */
.stButton > button[kind="primary"] {{
    background-color: {c["accent"]};
    color: {c["accent_text"]};
    border: none;
}}
.stButton > button[kind="primary"]:hover {{
    background-color: {c["accent_hover"]};
    color: {c["accent_text"]};
}}

/* กล่องแชท */
[data-testid="stChatMessage"] {{
    background-color: {c["assistant_bubble"]};
    border: 1px solid {c["border"]};
    border-radius: 14px;
    padding: 0.4rem 0.6rem;
    margin-bottom: 0.6rem;
}}

/* ช่องพิมพ์แชท */
[data-testid="stChatInput"] {{
    border-radius: 14px;
    border: 1px solid {c["border"]};
    background-color: {c["card_bg"]};
}}
[data-testid="stChatInput"] textarea {{
    color: {c["text"]} !important;
}}

/* input, selectbox, file uploader */
.stTextInput input, .stSelectbox div[data-baseweb="select"], [data-testid="stFileUploaderDropzone"] {{
    border-radius: 10px !important;
    border-color: {c["border"]} !important;
    background-color: {c["card_bg"]} !important;
}}

/* เส้นคั่น */
hr {{
    border-color: {c["border"]};
}}

/* การ์ด/กล่อง expander */
[data-testid="stExpander"] {{
    border: 1px solid {c["border"]};
    border-radius: 10px;
    background-color: {c["card_bg"]};
}}

/* แถบ nav ในไซด์บาร์ */
.nav-item {{
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.55rem 0.8rem;
    border-radius: 10px;
    margin-bottom: 0.25rem;
    font-weight: 500;
    cursor: pointer;
}}
.nav-item-active {{
    background-color: {c["nav_active_bg"]};
}}

/* ป้ายบทบาท */
.role-badge {{
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 999px;
    background-color: {c["nav_active_bg"]};
    color: {c["text"]};
    font-size: 0.8rem;
    font-weight: 600;
    margin-bottom: 0.6rem;
}}

/* หัวข้อประวัติแชท */
.chat-history-title {{
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: {c["text_muted"]};
    margin: 1rem 0 0.4rem 0.2rem;
}}
</style>
"""
