"""
The "Test your knowledge" button (OSHCwise).

It sits at the bottom of the cards page (pages/1_Question.py) and opens the
Myth or fact quiz (pages/Test_Knowledge.py).

    from quiz_button import show_quiz_button
    show_quiz_button()
"""

import streamlit as st

QUIZ_PAGE = "pages/Test_Knowledge.py"


def show_quiz_button() -> None:
    st.markdown("<div style='border-top:1px solid #d7dbe1;margin:1.6rem 0 1rem'></div>", unsafe_allow_html=True)
    _, middle, _ = st.columns([1, 2, 1])
    with middle:
        st.markdown(
            "<div style='text-align:center;font:700 16px \"Lucida Sans\",\"Lucida Sans Unicode\",Arial,sans-serif;"
            "color:#143a5a;margin-bottom:0.5rem'>Already know a lot? See what you remember.</div>",
            unsafe_allow_html=True,
        )
        if st.button("🎯 Test your knowledge", key="to_quiz", type="primary", use_container_width=True):
            st.switch_page(QUIZ_PAGE)

    # empty space under the button, so it does not touch the bottom of the page
    st.markdown("<div style='height:4rem'></div>", unsafe_allow_html=True)
