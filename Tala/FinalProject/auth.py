"""Very small login helper for the OSHCwise prototype.

Two roles:
    "student"  - sees the practice pages
    "admin"    - sees everything a student sees, plus the analytics dashboard

This is a PROTOTYPE login (a shared password for the admin, no real accounts).
A real version should use single sign-on (for example the university's or
Medibank's login). Do not put real secrets in the code.

Accounts: see USERS below (Student / 123456 and Admin / 123456 for now).
"""

import hmac

import streamlit as st

LOGIN_PAGE = "oshc_welcome.py"
DASHBOARD_PAGE = "pages/Admin_Dashboard.py"
DEMO_ADMIN_PASSWORD = "oshcwise-demo"


# Prototype accounts (one shared login per role). Change them here for now.
# A real version should use single sign-on instead of passwords in the code.
USERS = {
    "student": {"username": "Student", "password": "123456"},
    "admin": {"username": "Admin", "password": "123456"},
}


def check_login(role: str, username: str, password: str) -> bool:
    """True when the username and password match the account of that role."""
    account = USERS.get(role)
    if not account:
        return False
    user_ok = hmac.compare_digest(username.strip().lower().encode(), account["username"].lower().encode())
    pass_ok = hmac.compare_digest(str(password).encode(), account["password"].encode())
    return user_ok and pass_ok


def login(role: str, name: str) -> None:
    st.session_state["role"] = role
    st.session_state["student_name"] = name


def logout() -> None:
    for key in ("role", "student_name", "admin_form"):
        st.session_state.pop(key, None)
    st.switch_page(LOGIN_PAGE)


def get_role():
    return st.session_state.get("role")


def is_admin() -> bool:
    return get_role() == "admin"


def require_login(admin_only: bool = False) -> None:
    """Put this at the top of every page (after set_page_config).

    Not logged in            -> back to the first page.
    admin_only and a student -> a short message and a way back.
    """
    role = get_role()
    if role is None:
        st.switch_page(LOGIN_PAGE)
    if admin_only and role != "admin":
        st.error("This page is for administrators only.")
        if st.button("← Back"):
            st.switch_page("pages/1_Question.py")
        st.stop()
