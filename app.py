"""Scribe — point d'entrée de l'application."""

import streamlit as st

st.set_page_config(
    page_title="Scribe",
    page_icon="🎙️",
    layout="centered",
)

st.title("🎙️ Auris")
st.caption("Assistant de réunion intelligent")

st.markdown(
    """
    Bienvenue sur **Scribe**. Choisissez un mode de captation :

    - **Dictaphone** — enregistrez une réunion en présentiel via le micro de votre appareil.
    - **Visioconférence** *(à venir)* — intégration d'une visio directement dans l'application.
    """
)

col1, col2 = st.columns(2)
with col1:
    if st.button("🎤 Mode Dictaphone", use_container_width=True, type="primary"):
        st.switch_page("pages/dictaphone.py")
with col2:
    if st.button("📹 Mode Visio (Skribby)", use_container_width=True):
        st.switch_page("pages/zoom_bot.py")
