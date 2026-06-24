"""Page Bot de réunion — Skribby rejoint Zoom, Teams ou Google Meet via l'API officielle."""

import time
from pathlib import Path

import streamlit as st

from utils.audio import format_size, list_recordings, save_audio
from utils.skribby_api import (
    create_bot,
    get_bot,
    stop_bot,
    wait_for_status,
    detect_platform,
    get_recording_url,
    download_audio,
    PLATFORM_LABELS,
)
from utils.mistral_api import transcribe_audio

st.set_page_config(page_title="Skribby — Bot de réunion", page_icon="📹", layout="centered")

st.title("📹 Skribby — Bot de réunion")
st.caption("Envoie Skribby dans ta réunion pour enregistrer l'audio automatiquement")

# ── État session ──────────────────────────────────────────────────────────────
for key, default in [
    ("bot_id", None),
    ("recording", False),
    ("saved_path", None),
    ("bot_status", ""),
    ("error", None),
    ("transcription", None),
    ("transcribing", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Consentement ──────────────────────────────────────────────────────────────
with st.expander("ℹ️ Consentement & RGPD", expanded=False):
    st.markdown(
        """
        En démarrant la capture, vous confirmez que **tous les participants**
        ont été informés et ont consenti à être enregistrés.

        - Les enregistrements sont stockés localement sur ce serveur.
        - Durée de conservation : **30 jours** par défaut.
        """
    )

consent = st.checkbox(
    "J'atteste que tous les participants ont consenti à l'enregistrement.",
    disabled=st.session_state.recording,
)

st.divider()

# ── Formulaire ────────────────────────────────────────────────────────────────
st.subheader("Lien de la réunion")

meeting_url = st.text_input(
    "Colle le lien d'invitation",
    placeholder="https://zoom.us/j/…   |   https://meet.google.com/…   |   https://teams.microsoft.com/…",
    disabled=st.session_state.recording,
)

if meeting_url:
    platform = detect_platform(meeting_url)
    if platform != "unknown":
        st.caption(f"{PLATFORM_LABELS[platform]} détecté")
    else:
        st.caption(":red[Plateforme non reconnue — vérifie le lien]")
else:
    platform = "unknown"

display_name = st.text_input(
    "Nom du bot",
    value="Skribby",
    disabled=st.session_state.recording,
)

st.divider()

# ── Contrôles ─────────────────────────────────────────────────────────────────
st.subheader("Contrôle")

col_join, col_stop = st.columns(2)

join_disabled = (
    not consent
    or not meeting_url.strip()
    or st.session_state.recording
    or platform == "unknown"
)

with col_join:
    if st.button(
        "🤖 Envoyer Skribby",
        type="primary",
        use_container_width=True,
        disabled=join_disabled,
    ):
        try:
            with st.spinner("Connexion à l'API Skribby…"):
                result = create_bot(
                    meeting_url=meeting_url,
                    bot_name=display_name,
                    platform=platform,
                )
            bot_id = result.get("id") or result.get("bot_id") or result.get("botId")
            if not bot_id:
                st.error(f"Réponse inattendue de l'API : {result}")
            else:
                st.session_state.bot_id = bot_id
                st.session_state.recording = True
                st.session_state.saved_path = None
                st.session_state.transcription = None
                st.session_state.error = None
                st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")

with col_stop:
    if st.button(
        "⏹ Arrêter & Récupérer",
        use_container_width=True,
        disabled=not st.session_state.recording,
    ):
        bot_id = st.session_state.bot_id
        audio_bytes = None

        with st.status("Récupération de l'enregistrement…", expanded=True) as status:

            st.write("⏹ Arrêt du bot en cours…")
            try:
                stop_bot(bot_id)
                st.write("✅ Bot arrêté")
            except Exception as e:
                st.write(f"⚠️ Arrêt : {e}")

            st.write("⏳ Attente de la fin du traitement audio…")
            try:
                bot_data = wait_for_status(
                    bot_id,
                    target_statuses=["done", "completed", "finished"],
                    timeout=180,
                )
                raw = bot_data.get("status", "?")
                st.write(f"✅ Statut final : `{raw}`")
            except Exception as e:
                bot_data = {}
                st.write(f"⚠️ Timeout ou erreur : {e}")

            audio_url = get_recording_url(bot_data)

            if audio_url:
                st.write("⬇️ Téléchargement de l'audio…")
                try:
                    audio_bytes = download_audio(audio_url)
                    path = save_audio(audio_bytes, extension="webm")
                    st.session_state.saved_path = path
                    st.write(f"✅ Audio sauvegardé : `{path.name}`")
                    status.update(label="✅ Enregistrement récupéré !", state="complete", expanded=False)
                except Exception as e:
                    st.write(f"❌ Erreur téléchargement : {e}")
                    st.session_state.error = str(e)
                    status.update(label="❌ Erreur lors du téléchargement", state="error", expanded=True)
            else:
                msg = (
                    f"Audio non disponible (statut : {bot_data.get('status', '?')}). "
                    "Réessaie dans quelques instants."
                )
                st.write(f"❌ {msg}")
                st.session_state.error = msg
                status.update(label="❌ Audio indisponible", state="error", expanded=True)

        st.session_state.recording = False
        st.session_state.bot_id = None
        st.rerun()

# ── Progression en temps réel ─────────────────────────────────────────────────
STATUS_STEPS = [
    ("booting",    "Démarrage du bot"),
    ("joining",    "Connexion à la réunion"),
    ("in_meeting", "Enregistrement en cours"),
    ("recording",  "Enregistrement en cours"),
    ("leaving",    "Sortie de la réunion"),
    ("processing", "Traitement de l'audio"),
    ("done",       "Terminé"),
]

STEP_ORDER = [s[0] for s in STATUS_STEPS]

def _render_steps(current_status: str) -> None:
    """Affiche les étapes du cycle de vie du bot avec indicateurs visuels."""
    seen = set()
    rows = []
    for key, label in STATUS_STEPS:
        if key in seen:
            continue
        seen.add(key)
        idx = STEP_ORDER.index(key) if key in STEP_ORDER else 99
        cur_idx = STEP_ORDER.index(current_status) if current_status in STEP_ORDER else -1
        if idx < cur_idx:
            icon = "✅"
        elif idx == cur_idx:
            icon = "🔄"
        else:
            icon = "⏳"
        rows.append(f"{icon} {label}")
    cols = st.columns(len(rows))
    for col, row in zip(cols, rows):
        col.markdown(f"<div style='text-align:center;font-size:0.8rem'>{row}</div>", unsafe_allow_html=True)

if st.session_state.recording and st.session_state.bot_id:
    st.divider()
    st.subheader("Progression")
    step_placeholder = st.empty()
    info_placeholder = st.empty()

    try:
        bot_data = get_bot(st.session_state.bot_id)
        raw_status = bot_data.get("status", "")
        st.session_state.bot_status = raw_status

        with step_placeholder.container():
            _render_steps(raw_status)

        status_labels = {
            "booting":    "🟡 Skribby démarre…",
            "joining":    "🟡 Connexion à la réunion en cours…",
            "in_meeting": "🔴 En réunion — enregistrement actif",
            "recording":  "🔴 Enregistrement actif",
            "leaving":    "🟠 Sortie de la réunion…",
            "processing": "🟠 Traitement de l'audio…",
            "done":       "✅ Terminé",
            "error":      "❌ Erreur Skribby",
        }
        label = status_labels.get(raw_status, f"⏳ {raw_status}")
        info_placeholder.info(f"{label}  •  Bot ID : `{st.session_state.bot_id}`")

        if raw_status in ("done", "error"):
            st.session_state.recording = False

    except Exception:
        info_placeholder.warning("Impossible de récupérer le statut du bot.")

    time.sleep(5)
    st.rerun()

elif st.session_state.error:
    st.warning(st.session_state.error)

elif st.session_state.saved_path:
    st.success(f"✅ Prêt — `{st.session_state.saved_path.name}`")

else:
    st.info("En attente — colle un lien de réunion et envoie Skribby.")

# ── Transcription automatique + téléchargement ───────────────────────────────
if st.session_state.saved_path and not st.session_state.transcription:
    p: Path = st.session_state.saved_path
    if p.exists():
        st.divider()
        with st.status("Transcription en cours…", expanded=True) as t_status:
            st.write("📤 Envoi de l'audio à Mistral Voxtral…")
            try:
                text = transcribe_audio(p.read_bytes(), filename=p.name, language=None)
                st.session_state.transcription = text
                st.write(f"✅ Transcription reçue ({len(text)} caractères)")
                t_status.update(label="✅ Transcription terminée", state="complete", expanded=False)
            except Exception as e:
                err_msg = str(e)
                st.write(f"❌ Erreur : {err_msg}")
                st.session_state.transcription = f"ERREUR : {err_msg}"
                t_status.update(label="❌ Erreur de transcription", state="error", expanded=True)
        st.rerun()

if st.session_state.saved_path and st.session_state.transcription:
    p: Path = st.session_state.saved_path
    st.divider()
    st.subheader("Transcription")
    if st.session_state.transcription.startswith("ERREUR"):
        st.error(st.session_state.transcription)
    else:
        st.text_area("Résultat", value=st.session_state.transcription, height=300)
        st.download_button(
            "⬇️ Télécharger la transcription (.txt)",
            data=st.session_state.transcription.encode("utf-8"),
            file_name=p.stem + "_transcription.txt",
            mime="text/plain",
        )

st.divider()

# ── Historique ────────────────────────────────────────────────────────────────
st.subheader("Enregistrements sauvegardés")
recordings = list_recordings()
if not recordings:
    st.info("Aucun enregistrement pour l'instant.")
else:
    for rec in recordings:
        c1, c2, c3, c4 = st.columns([4, 1, 1, 1])
        with c1:
            st.write(f"📄 `{rec.name}`")
        with c2:
            st.write(format_size(rec))
        with c3:
            st.download_button("⬇️", data=rec.read_bytes(), file_name=rec.name, key=f"dl_{rec.name}")
        with c4:
            if st.button("🗑️", key=f"del_{rec.name}", help="Supprimer"):
                rec.unlink()
                st.rerun()

st.divider()
if st.button("← Retour à l'accueil"):
    st.switch_page("app.py")
