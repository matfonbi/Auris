"""Page dictaphone — capture audio via le micro du navigateur."""

import streamlit as st

from utils.audio import format_size, list_recordings, save_audio

st.set_page_config(page_title="Dictaphone — Scribe", page_icon="🎤", layout="centered")

st.title("🎤 Dictaphone")
st.caption("Enregistrez votre réunion en présentiel")

# ── Consentement ────────────────────────────────────────────────────────────
with st.expander("ℹ️ Consentement & RGPD", expanded=False):
    st.markdown(
        """
        En démarrant l'enregistrement, vous confirmez que **tous les participants**
        présents ont été informés et ont consenti à être enregistrés.

        - Les enregistrements sont stockés localement sur ce serveur.
        - Durée de conservation : **30 jours** par défaut.
        - Vous pouvez supprimer un enregistrement à tout moment depuis la liste ci-dessous.
        """
    )

consent = st.checkbox("J'atteste que tous les participants ont consenti à l'enregistrement.")

st.divider()

# ── Capture audio ────────────────────────────────────────────────────────────
st.subheader("Nouvel enregistrement")

if not consent:
    st.info("Cochez la case de consentement pour activer l'enregistrement.")
    audio_data = None
else:
    audio_data = st.audio_input(
        "Cliquez sur le micro pour démarrer, recliquez pour arrêter.",
    )

if audio_data is not None:
    st.audio(audio_data, format="audio/wav")

    col_save, col_discard = st.columns([1, 1])
    with col_save:
        if st.button("💾 Sauvegarder l'enregistrement", type="primary", use_container_width=True):
            with st.spinner("Sauvegarde en cours…"):
                path = save_audio(audio_data.getvalue())
            st.success(f"Enregistrement sauvegardé : `{path.name}`")
            st.rerun()
    with col_discard:
        if st.button("🗑️ Ignorer", use_container_width=True):
            st.rerun()

st.divider()

# ── Historique local ─────────────────────────────────────────────────────────
st.subheader("Enregistrements sauvegardés")

recordings = list_recordings()

if not recordings:
    st.info("Aucun enregistrement pour l'instant.")
else:
    for rec in recordings:
        col_name, col_size, col_dl, col_del = st.columns([4, 1, 1, 1])
        with col_name:
            st.write(f"📄 `{rec.name}`")
        with col_size:
            st.write(format_size(rec))
        with col_dl:
            st.download_button(
                label="⬇️",
                data=rec.read_bytes(),
                file_name=rec.name,
                mime="audio/wav",
                key=f"dl_{rec.name}",
            )
        with col_del:
            if st.button("🗑️", key=f"del_{rec.name}", help="Supprimer"):
                rec.unlink()
                st.rerun()

st.divider()
if st.button("← Retour à l'accueil"):
    st.switch_page("app.py")
