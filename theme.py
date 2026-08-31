"""
theme.py
--------
CSS ธีมสีส้มอบอุ่น มินิมอล คล้ายแอปแชทผู้ช่วยคู่มือ (โทนเดียว ไม่มีสลับ dark mode)
"""

C = {
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


def get_css(*_args, **_kwargs) -> str:
    """รับ argument ทิ้งได้เผื่อโค้ดเก่ายังส่ง dark_mode เข้ามา (ตอนนี้มีธีมเดียว)"""
    c = C
    gradient = f"linear-gradient(135deg, {c['accent_from']}, {c['accent_to']})"
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}}

.stApp {{ background-color: {c["bg"]}; color: {c["text"]}; }}

#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header[data-testid="stHeader"] {{background: transparent;}}

[data-testid="stSidebar"] {{
    background-color: {c["sidebar_bg"]};
    border-right: 1px solid {c["border"]};
}}
[data-testid="stSidebar"] > div:first-child {{ padding-top: 1rem; }}

h1, h2, h3, h4, h5, h6 {{ color: {c["text"]} !important; font-weight: 700 !important; }}
p, span, label, .stMarkdown {{ color: {c["text"]}; }}
.stCaption, [data-testid="stCaptionContainer"] {{ color: {c["text_muted"]} !important; }}

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

/* ปุ่มแนบคู่มือเพิ่ม */
.attach-btn button {{
    background: {gradient} !important;
    color: #FFFFFF !important;
    border: none !important;
    font-weight: 700 !important;
    border-radius: 14px !important;
    padding: 0.7rem 1rem !important;
    box-shadow: 0 4px 14px rgba(255, 138, 61, 0.35);
    justify-content: center !important;
    text-align: center !important;
}}
.attach-btn button:hover {{ filter: brightness(1.05); color: #FFFFFF !important; }}
.attach-btn button p {{ font-weight: 700 !important; font-size: 1rem !important; }}

/* ปุ่มล้างแชท (เล็ก, โทนเทา) */
.clear-btn button {{
    color: {c["text_muted"]} !important;
    border: 1px solid {c["border"]} !important;
    border-radius: 10px !important;
    font-size: 0.82rem !important;
    justify-content: center !important;
    padding: 0.3rem 0.6rem !important;
}}
.clear-btn button:hover {{
    color: #C0392B !important;
    border-color: #C0392B !important;
    background-color: #FDEDEB !important;
}}

/* ปุ่มลบไฟล์ในคลัง (เล็ก ไม่ตกบรรทัด) */
.file-del-btn button {{
    white-space: nowrap !important;
    padding: 0.25rem 0.6rem !important;
    font-size: 0.8rem !important;
    justify-content: center !important;
    color: {c["text_muted"]} !important;
    border: 1px solid {c["border"]} !important;
    min-width: 0 !important;
}}
.file-del-btn button p {{ white-space: nowrap !important; margin: 0 !important; }}
.file-del-btn button:hover {{
    color: #C0392B !important;
    border-color: #C0392B !important;
    background-color: #FDEDEB !important;
}}

[data-testid="stChatMessage"] {{
    background-color: {c["assistant_bubble"]};
    border: 1px solid {c["border"]};
    border-radius: 16px;
    padding: 0.5rem 0.7rem;
    margin-bottom: 0.7rem;
    max-width: 78%;
}}

.user-row {{ display: flex; justify-content: flex-end; margin-bottom: 0.7rem; }}
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
.welcome-wrap {{ text-align: center; padding: 2rem 1rem 1.4rem 1rem; }}
.welcome-icon {{
    width: 68px; height: 68px; border-radius: 20px;
    background: {gradient};
    display: flex; align-items: center; justify-content: center;
    font-size: 32px; margin: 0 auto 1rem auto;
    box-shadow: 0 6px 18px rgba(255, 122, 48, 0.3);
}}
.welcome-title {{ font-size: 1.7rem; font-weight: 800; color: {c["text"]}; margin-bottom: 0.4rem; }}
.welcome-sub {{ color: {c["text_muted"]}; max-width: 480px; margin: 0 auto 1.8rem auto; line-height: 1.6; }}

/* การ์ดคำถามแนะนำ — แก้บั๊กข้อความล้นกรอบ + ให้ดูเป็นการ์ดจริงๆ */
div[data-testid="column"]:has(.suggestion-card) {{ padding: 0.4rem !important; }}
.suggestion-card {{ height: 100%; }}
.suggestion-card button {{
    background-color: {c["card_bg"]} !important;
    border: 1.5px solid {c["border"]} !important;
    border-radius: 16px !important;
    color: {c["text"]} !important;
    text-align: left !important;
    justify-content: flex-start !important;
    align-items: flex-start !important;
    padding: 1.1rem 1.2rem !important;
    font-weight: 500 !important;
    width: 100% !important;
    min-height: 76px !important;
    height: auto !important;
    white-space: normal !important;
    word-break: break-word !important;
    overflow-wrap: break-word !important;
    line-height: 1.55 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}}
.suggestion-card button * {{
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    word-break: break-word !important;
    overflow-wrap: break-word !important;
    margin: 0 !important;
    text-align: left !important;
}}
.suggestion-card button:hover {{
    border-color: {c["accent_solid"]} !important;
    background-color: {c["nav_active_bg"]} !important;
    color: {c["text"]} !important;
    box-shadow: 0 4px 10px rgba(255, 138, 61, 0.15);
}}

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
