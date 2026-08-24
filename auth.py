"""
auth.py
-------
ระบบ login แบบง่าย มี 2 บทบาท: admin และ user
รหัสผ่านตั้งไว้ใน Streamlit secrets (.streamlit/secrets.toml) ไม่เก็บในโค้ด
"""

import streamlit as st


def login_gate():
    """แสดงหน้า login ถ้ายังไม่ล็อกอิน คืนค่า True ถ้าล็อกอินแล้ว (และตั้ง st.session_state.role)"""
    if st.session_state.get("logged_in"):
        return True

    st.title("🔐 เข้าสู่ระบบ")
    with st.form("login_form"):
        username = st.selectbox("บทบาท", ["user", "admin"])
        password = st.text_input("รหัสผ่าน", type="password")
        submitted = st.form_submit_button("เข้าสู่ระบบ")

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


def logout_button():
    if st.sidebar.button("ออกจากระบบ"):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.rerun()
