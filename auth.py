"""
auth.py
-------
ระบบ login แบบง่าย มี 2 บทบาท: admin และ user
รหัสผ่านตั้งไว้ใน Streamlit secrets (.streamlit/secrets.toml) ไม่เก็บในโค้ด
"""

import streamlit as st
from theme import get_css


def login_gate():
    """แสดงหน้า login ถ้ายังไม่ล็อกอิน คืนค่า True ถ้าล็อกอินแล้ว (และตั้ง st.session_state.role)"""
    if st.session_state.get("logged_in"):
        return True

    st.markdown(get_css(), unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.write("")
        st.write("")
        st.markdown("### 📄 เข้าสู่ระบบ")
        st.caption("ผู้ช่วยตอบคำถามจากคู่มือองค์กร")
        with st.form("login_form"):
            username = st.selectbox("บทบาท", ["user", "admin"])
            password = st.text_input("รหัสผ่าน", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ", use_container_width=True, type="primary")

        if submitted:
            admin_pw = st.secrets["auth"]["admin_password"]
            user_pw = st.secrets["auth"]["user_password"]

            if username == "admin" and password == admin_pw:
                st.session_state.logged_in = True
                st.session_state.role = "admin"
                st.rerun()
            elif username == "user" and password == user_pw:
                st.session_state.logged_in = True
                st.session_state.role = "user"
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")

    return False
