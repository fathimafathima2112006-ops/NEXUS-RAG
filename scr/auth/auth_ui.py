import streamlit as st

from src.auth.security import (
    validate_identifier, hash_password, verify_password
)
from src.auth.otp import issue_otp, verify_reset_otp
from src.database import db

db.init_db()

def sign_in(identifier, password):
    kind, normalized = validate_identifier(identifier)
    if not kind:
        return None
    user = db.get_user(normalized)
    if user and verify_password(
        password, user["password_hash"], user["password_salt"]
    ):
        return user
    return None

def render_auth():
    st.markdown("""
    <style>
    .stApp {
      background:
        radial-gradient(circle at 20% 0%, #35206d 0, transparent 35%),
        radial-gradient(circle at 90% 20%, #102e67 0, transparent 35%),
        #050812;
    }
    .auth {
      max-width: 620px;
      margin: 5vh auto;
      padding: 34px;
      border: 1px solid rgba(255,255,255,.12);
      border-radius: 28px;
      background: rgba(13,18,32,.88);
      box-shadow: 0 30px 80px rgba(0,0,0,.35);
    }
    .logo { text-align:center; font-size:4rem; }
    .title {
      text-align:center;
      font-size:2.4rem;
      font-weight:900;
      color:#c9c3f0;
    }
    .sub { text-align:center; color:#94a3b8; margin-bottom:25px; }
    </style>
    <div class="auth">
      <div class="logo">🧠</div>
      <div class="title">NEXUS RAG</div>
      <div class="sub">AI Knowledge Intelligence Platform</div>
    """, unsafe_allow_html=True)

    login, signup, forgot = st.tabs(
        ["🔐 Sign In", "✨ Create Account", "🔑 Forgot Password"]
    )

    with login:
        identifier = st.text_input(
            "Email or phone", key="login_identifier"
        )
        password = st.text_input(
            "Password", type="password", key="login_password"
        )
        if st.button("Sign In", use_container_width=True):
            user = sign_in(identifier, password)
            if user:
                st.session_state.authenticated = True
                st.session_state.user_id = user["id"]
                st.session_state.display_name = user["display_name"]
                st.session_state.identifier = user["identifier"]
                st.rerun()
            else:
                st.error("Invalid email/phone or password.")

    with signup:
        name = st.text_input("Full name", key="signup_name")
        identifier = st.text_input(
            "Email or phone", key="signup_identifier"
        )
        password = st.text_input(
            "Password", type="password", key="signup_password"
        )
        confirm = st.text_input(
            "Confirm password", type="password", key="signup_confirm"
        )

        if st.button("Create Account", use_container_width=True):
            kind, normalized = validate_identifier(identifier)
            if len(name.strip()) < 2:
                st.error("Enter your name.")
            elif not kind:
                st.error("Enter a valid email or international phone number.")
            elif len(password) < 8:
                st.error("Password must contain at least 8 characters.")
            elif password != confirm:
                st.error("Passwords do not match.")
            elif db.get_user(normalized):
                st.error("An account already exists.")
            else:
                p_hash, p_salt = hash_password(password)
                ok = db.create_user(
                    normalized, kind, name.strip(), p_hash, p_salt
                )
                if ok:
                    user = db.get_user(normalized)
                    st.session_state.authenticated = True
                    st.session_state.user_id = user["id"]
                    st.session_state.display_name = user["display_name"]
                    st.session_state.identifier = user["identifier"]
                    st.success("Account created successfully.")
                    st.rerun()
                else:
                    st.error("Could not create account.")

    with forgot:
        identifier = st.text_input(
            "Account email or phone", key="forgot_identifier"
        )
        if st.button("Send OTP", use_container_width=True):
            kind, normalized = validate_identifier(identifier)
            if not kind:
                st.error("Enter a valid email or phone.")
            else:
                user = db.get_user(normalized)
                if user:
                    ok, msg = issue_otp(user)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.info(
                        "If an account exists, an OTP will be sent."
                    )

        st.divider()
        otp = st.text_input(
            "6-digit OTP", max_chars=6, key="forgot_otp"
        )
        new_password = st.text_input(
            "New password", type="password", key="new_password"
        )
        confirm = st.text_input(
            "Confirm new password", type="password", key="new_password2"
        )

        if st.button(
            "Verify OTP & Reset Password",
            use_container_width=True
        ):
            kind, normalized = validate_identifier(identifier)
            user = db.get_user(normalized) if kind else None

            if not user:
                st.error("Invalid account or OTP.")
            elif len(new_password) < 8:
                st.error("Password must contain at least 8 characters.")
            elif new_password != confirm:
                st.error("Passwords do not match.")
            else:
                ok, msg = verify_reset_otp(user, otp)
                if ok:
                    p_hash, p_salt = hash_password(new_password)
                    db.update_password(user["id"], p_hash, p_salt)
                    st.success("Password reset successfully. Sign in now.")
                else:
                    st.error(msg)

    st.markdown("</div>", unsafe_allow_html=True)