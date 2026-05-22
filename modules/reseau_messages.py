"""
Messagerie privée — style WhatsApp.
Liste de conversations à gauche, messages à droite.
"""
from __future__ import annotations
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as _comp

from core.supabase_client import supabase_get, supabase_post, supabase_patch
from core.utils import safe_str
from modules.reseau_auth import render_auth


def _fmt_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", ""))
        now = datetime.now()
        if dt.date() == now.date():
            return dt.strftime("%H:%M")
        return dt.strftime("%d/%m %H:%M")
    except Exception:
        return ""


def _get_conversations(user_id: str) -> list:
    """Récupère la liste des conversations avec le dernier message."""
    msgs = supabase_get("messages", {
        "or": f"(expediteur_id.eq.{user_id},destinataire_id.eq.{user_id})",
        "order": "created_at.desc",
        "select": "id,expediteur_id,destinataire_id,contenu,lu,created_at",
        "limit": "200",
    })
    if not msgs:
        return []

    # Regrouper par interlocuteur
    convs = {}
    for m in msgs:
        other_id = m["destinataire_id"] if m["expediteur_id"] == user_id else m["expediteur_id"]
        if other_id not in convs:
            convs[other_id] = {
                "other_id": other_id,
                "last_msg": m["contenu"],
                "last_time": m["created_at"],
                "unread": 0,
            }
        if not m["lu"] and m["destinataire_id"] == user_id:
            convs[other_id]["unread"] += 1

    # Récupérer les pseudos
    result = []
    for other_id, conv in convs.items():
        profil = supabase_get("profils", {"id": f"eq.{other_id}", "select": "pseudo,photo_path"})
        if profil:
            conv["pseudo"] = profil[0].get("pseudo", "?")
            conv["photo"]  = safe_str(profil[0].get("photo_path")) or ""
        else:
            conv["pseudo"] = "Pêcheur"
            conv["photo"]  = ""
        result.append(conv)

    result.sort(key=lambda x: x["last_time"], reverse=True)
    return result


def _get_messages(user_id: str, other_id: str) -> list:
    """Récupère les messages d'une conversation."""
    sent = supabase_get("messages", {
        "expediteur_id":   f"eq.{user_id}",
        "destinataire_id": f"eq.{other_id}",
        "order": "created_at.asc",
        "select": "id,expediteur_id,contenu,lu,created_at",
    }) or []
    received = supabase_get("messages", {
        "expediteur_id":   f"eq.{other_id}",
        "destinataire_id": f"eq.{user_id}",
        "order": "created_at.asc",
        "select": "id,expediteur_id,contenu,lu,created_at",
    }) or []

    # Marquer comme lus
    for m in received:
        if not m.get("lu"):
            supabase_patch("messages", m["id"], {"lu": True})

    all_msgs = sorted(sent + received, key=lambda x: x["created_at"])
    return all_msgs


def render() -> None:
    if not render_auth():
        return

    user = st.session_state["reseau_user"]
    uid  = user["id"]

    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:14px 20px;border-radius:8px;margin-bottom:16px;">'
        '<span style="font-size:18px;font-weight:800;">💬 Messages</span>'
        '<div style="font-size:12px;opacity:.85;margin-top:3px;">'
        'Messagerie privée entre pêcheurs.</div></div>',
        unsafe_allow_html=True,
    )

    # ── Sélection de conversation ────────────────────────────────
    active_id = st.session_state.get("msg_active_id")

    col_list, col_chat = st.columns([1, 2])

    with col_list:
        st.markdown("**💬 Conversations**")

        # Nouvelle conversation
        with st.expander("➕ Nouveau message"):
            search = st.text_input("Rechercher un pêcheur", key="msg_search",
                                    placeholder="Pseudo...")
            if search and len(search) >= 2:
                results = supabase_get("profils", {
                    "pseudo": f"ilike.*{search}*",
                    "select": "id,pseudo",
                    "limit": "5",
                })
                for r in (results or []):
                    if r["id"] == uid: continue
                    if st.button(f"🎣 {r['pseudo']}", key=f"new_conv_{r['id']}",
                                  use_container_width=True):
                        st.session_state["msg_active_id"] = r["id"]
                        st.rerun()

        # Liste des conversations
        convs = _get_conversations(uid)
        if not convs:
            st.info("Aucune conversation.\nEnvoie un message à un pêcheur !")
        else:
            for conv in convs:
                is_active = conv["other_id"] == active_id
                unread_badge = f' 🔴 {conv["unread"]}' if conv["unread"] > 0 else ""
                last = conv["last_msg"][:30] + "..." if len(conv["last_msg"]) > 30 else conv["last_msg"]

                # Avatar
                if conv["photo"] and conv["photo"].startswith("http"):
                    avatar = f'<img src="{conv["photo"]}" style="width:36px;height:36px;border-radius:50%;object-fit:cover;">'
                else:
                    avatar = '<div style="width:36px;height:36px;border-radius:50%;background:#1565C0;display:flex;align-items:center;justify-content:center;color:#fff;font-size:16px;">🎣</div>'

                bg = "linear-gradient(135deg,#1565C0,#0c2340)" if is_active else "#f5f7fa"
                color = "#fff" if is_active else "#0c2340"

                _comp.html(f"""
<div style="background:{bg};border-radius:10px;padding:8px 10px;
  margin-bottom:4px;display:flex;align-items:center;gap:10px;">
  {avatar}
  <div style="flex:1;min-width:0;">
    <div style="font-size:13px;font-weight:700;color:{color};">
      {conv["pseudo"]}{unread_badge}
    </div>
    <div style="font-size:11px;color:{"rgba(255,255,255,.7)" if is_active else "#546E7A"};
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
      {last}
    </div>
  </div>
  <div style="font-size:10px;color:{"rgba(255,255,255,.6)" if is_active else "#90A4AE"};">
    {_fmt_time(conv["last_time"])}
  </div>
</div>
""", height=60, scrolling=False)

                if st.button("Ouvrir", key=f"open_conv_{conv['other_id']}",
                              use_container_width=True,
                              type="primary" if is_active else "secondary"):
                    st.session_state["msg_active_id"] = conv["other_id"]
                    st.rerun()

    with col_chat:
        if not active_id:
            st.info("👈 Sélectionne une conversation ou commence-en une nouvelle.")
            return

        # Infos interlocuteur
        other_profil = supabase_get("profils", {"id": f"eq.{active_id}", "select": "pseudo,photo_path"})
        if not other_profil:
            st.error("Pêcheur introuvable.")
            return
        other = other_profil[0]
        other_pseudo = other.get("pseudo", "Pêcheur")
        other_photo  = safe_str(other.get("photo_path")) or ""

        # En-tête conversation
        if other_photo and other_photo.startswith("http"):
            avatar_h = f'<img src="{other_photo}" style="width:38px;height:38px;border-radius:50%;object-fit:cover;border:2px solid #1565C0;">'
        else:
            avatar_h = '<div style="width:38px;height:38px;border-radius:50%;background:#1565C0;display:flex;align-items:center;justify-content:center;color:#fff;font-size:18px;">🎣</div>'

        st.markdown(
            f'<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
            f'color:#fff;padding:8px 14px;border-radius:8px;margin-bottom:10px;'
            f'display:flex;align-items:center;gap:10px;">'
            f'{avatar_h}'
            f'<span style="font-size:14px;font-weight:800;">{other_pseudo}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Messages
        messages = _get_messages(uid, active_id)

        if not messages:
            st.info(f"Démarre la conversation avec {other_pseudo} 👋")
        else:
            chat_html = '<div style="font-family:system-ui,sans-serif;display:flex;flex-direction:column;gap:6px;padding:4px;">'
            for m in messages[-30:]:  # 30 derniers
                is_me = m["expediteur_id"] == uid
                align = "flex-end" if is_me else "flex-start"
                bg    = "linear-gradient(135deg,#1565C0,#1976D2)" if is_me else "#f0f4f8"
                color = "#fff" if is_me else "#0c2340"
                time_str = _fmt_time(m["created_at"])
                chat_html += f"""
<div style="display:flex;justify-content:{align};">
  <div style="max-width:75%;background:{bg};color:{color};
    padding:8px 12px;border-radius:{"12px 12px 4px 12px" if is_me else "12px 12px 12px 4px"};">
    <div style="font-size:13px;">{m["contenu"]}</div>
    <div style="font-size:10px;opacity:.7;margin-top:3px;text-align:right;">{time_str}</div>
  </div>
</div>"""
            chat_html += '</div>'
            _comp.html(chat_html, height=min(400, 50 + len(messages) * 55), scrolling=True)

        # Zone de saisie
        st.markdown("---")
        with st.form(f"msg_form_{active_id}", clear_on_submit=True):
            c1, c2 = st.columns([5, 1])
            msg_txt = c1.text_input("Ton message", placeholder="Écris un message...",
                                     label_visibility="collapsed", key="msg_input")
            send    = c2.form_submit_button("📤", use_container_width=True)

        if send and msg_txt.strip():
            supabase_post("messages", {
                "expediteur_id":   uid,
                "destinataire_id": active_id,
                "contenu":         msg_txt.strip(),
                "lu":              False,
                "created_at":      datetime.now().isoformat(),
            })
            st.rerun()
