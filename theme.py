"""
theme.py
--------
CSS ธีมสีส้มอบอุ่น มินิมอล คล้ายแอปแชทผู้ช่วยคู่มือ
รองรับ Light / Dark mode ผ่าน st.session_state.dark_mode
"""

LIGHT = {
    "bg": "#FFFFFF",
    "bg_secondary": "#FDFBF8",
    "sidebar_bg": "#FDFBF8",
    "text": "#2A2622",
    "text_muted": "#8B8378",
    "border": "#EFE9DF",
    "accent_from": "#FDBA47",
    "accent_to": "#FF7A30",
    "accent_solid": "#FF8A3D",
    "accent_text": "#FFFFFF",
    "nav_active_bg": "#FFF1DE",
    "nav_active_text": "#B85C1A",
    "card_bg": "#FFFFFF",
    "assistant_bubble": "#F7F4EE",
    "user_bubble_text": "#FFFFFF",
}

DARK = {
    "bg": "#211D19",
    "bg_secondary": "#1A1714",
    "sidebar_bg": "#1A1714",
    "text": "#F3EFE8",
    "text_muted": "#A79E8E",
    "border": "#3A332B",
    "accent_from": "#FDBA47",
    "accent_to": "#FF7A30",
    "accent_solid": "#FF8A3D",
    "accent_text": "#FFFFFF",
    "nav_active_bg": "#3A2A18",
    "nav_active_text": "#FFB066",
    "card_bg": "#2A251F",
    "assistant_bubble": "#2A251F",
    "user_bubble_text": "#FFFFFF",
}


def get_css(dark_mode: bool) -> str:
    c = DARK if dark_mode else LIGHT
    gradient = f"linear-gradient(135deg, {c['accent_from']}, {c['accent_to']})"
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}}

.stApp {{
    background-color: {c["bg"]};
    color: {c["text"]};
}}

#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header[data-testid="stHeader"] {{background: transparent;}}

/* Sidebar */
[data-testid="stSidebar"] {{
    background-color: {c["sidebar_bg"]};
    border-right: 1px solid {c["border"]};
}}
[data-testid="stSidebar"] > div:first-child {{ padding-top: 1rem; }}

h1, h2, h3, h4, h5, h6 {{ color: {c["text"]} !important; font-weight: 700 !important; }}
p, span, label, .stMarkdown {{ color: {c["text"]}; }}
.stCaption, [data-testid="stCaptionContainer"] {{ color: {c["text_muted"]} !important; }}

/* ปุ่มทั่วไป (nav items / secondary) */
.stButton > button {{
    border-radius: 12px;
    border: 1px solid transparent;
    background-color: transparent;
    color: {c["text"]};
    font-weight: 500;
    text-align: left;
    justify-content: flex-start;
    transition: all 0.15s ease;
}}
.stButton > button:hover {{
    background-color: {c["nav_active_bg"]};
    color: {c["nav_active_text"]};
    border-color: transparent;
}}

/* ปุ่มที่ active (เมนูที่เลือกอยู่) ใช้ type=primary แทนสถานะ active */
.stButton > button[kind="primary"] {{
    background: {c["nav_active_bg"]};
    color: {c["nav_active_text"]} !important;
    border: none;
    font-weight: 600;
}}
.stButton > button[kind="primary"]:hover {{
    background: {c["nav_active_bg"]};
    color: {c["nav_active_text"]} !important;
}}

/* ปุ่มแนบคู่มือเพิ่ม (gradient เด่น) */
.attach-btn button {{
    background: {gradient} !important;
    color: #FFFFFF !important;
    border: none !important;
    font-weight: 700 !important;
    border-radius: 14px !important;
    padding: 0.7rem 1rem !important;
    box-shadow: 0 4px 14px rgba(255, 138, 61, 0.35);
}}
.attach-btn button:hover {{
    filter: brightness(1.05);
    color: #FFFFFF !important;
}}
.attach-btn button p {{ font-weight: 700 !important; font-size: 1rem !important; }}

/* ข้อความแชทฝั่งผู้ช่วย (ใช้ st.chat_message) */
[data-testid="stChatMessage"] {{
    background-color: {c["assistant_bubble"]};
    border: 1px solid {c["border"]};
    border-radius: 16px;
    padding: 0.5rem 0.7rem;
    margin-bottom: 0.7rem;
    max-width: 78%;
}}

/* ฟองข้อความฝั่งผู้ใช้ (custom, ชิดขวา) */
.user-row {{
    display: flex;
    justify-content: flex-end;
    margin-bottom: 0.7rem;
}}
.user-bubble {{
    background: {gradient};
    color: {c["user_bubble_text"]};
    padding: 0.6rem 1rem;
    border-radius: 16px 16px 4px 16px;
    max-width: 70%;
    font-weight: 500;
    line-height: 1.5;
    white-space: pre-wrap;
    box-shadow: 0 2px 8px rgba(255, 122, 48, 0.25);
}}

/* ช่องพิมพ์แชท */
[data-testid="stChatInput"] {{
    border-radius: 18px;
    border: 1px solid {c["border"]};
    background-color: {c["card_bg"]};
}}
[data-testid="stChatInput"] textarea {{ color: {c["text"]} !important; }}

.stTextInput input, .stSelectbox div[data-baseweb="select"], [data-testid="stFileUploaderDropzone"] {{
    border-radius: 12px !important;
    border-color: {c["border"]} !important;
    background-color: {c["card_bg"]} !important;
}}

hr {{ border-color: {c["border"]}; }}

[data-testid="stExpander"] {{
    border: 1px solid {c["border"]};
    border-radius: 12px;
    background-color: {c["card_bg"]};
}}

/* หน้าต้อนรับ */
.welcome-wrap {{ text-align: center; padding: 2rem 1rem 1rem 1rem; }}
.welcome-icon {{
    width: 68px; height: 68px; border-radius: 20px;
    background: {gradient};
    display: flex; align-items: center; justify-content: center;
    font-size: 32px; margin: 0 auto 1rem auto;
    box-shadow: 0 6px 18px rgba(255, 122, 48, 0.3);
}}
.welcome-title {{ font-size: 1.7rem; font-weight: 800; color: {c["text"]}; margin-bottom: 0.4rem; }}
.welcome-sub {{ color: {c["text_muted"]}; max-width: 480px; margin: 0 auto 1.6rem auto; line-height: 1.6; }}

/* การ์ดคำถามแนะนำ */
.suggestion-card button {{
    background-color: {c["card_bg"]} !important;
    border: 1px solid {c["border"]} !important;
    border-radius: 14px !important;
    color: {c["text"]} !important;
    text-align: left !important;
    padding: 1rem !important;
    font-weight: 500 !important;
    white-space: normal !important;
    height: auto !important;
}}
.suggestion-card button:hover {{
    border-color: {c["accent_solid"]} !important;
    color: {c["text"]} !important;
    background-color: {c["nav_active_bg"]} !important;
}}

/* ป้ายบทบาท */
.role-badge {{
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 999px;
    background-color: {c["nav_active_bg"]};
    color: {c["nav_active_text"]};
    font-size: 0.78rem;
    font-weight: 700;
    margin-bottom: 0.6rem;
}}

.sidebar-section-title {{
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: {c["text_muted"]};
    margin: 1.1rem 0 0.3rem 0.3rem;
    font-weight: 700;
}}

.empty-hint {{
    color: {c["text_muted"]};
    font-size: 0.85rem;
    text-align: center;
    padding: 1rem 0.5rem;
    line-height: 1.6;
}}
</style>
"""
