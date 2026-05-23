"""Classement général des pêcheurs avec photo de profil et trophée."""
from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as _comp
from core.supabase_client import supabase_get
from modules.reseau_auth import render_auth


def render() -> None:
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:14px 20px;border-radius:8px;margin:8px 0 18px;">'
        '<span style="font-size:18px;font-weight:800;">🏆 Classement des pêcheurs</span>'
        '<div style="font-size:12px;opacity:.85;margin-top:3px;">'
        'Les meilleurs pêcheurs de la communauté.</div></div>',
        unsafe_allow_html=True,
    )

    if not render_auth():
        return

    user = st.session_state.get("reseau_user")

    tab_global, tab_amis = st.tabs(["🌍 Classement général", "👥 Entre amis"])

    with tab_global:
        _render_classement(user, friends_only=False)

    with tab_amis:
        _render_classement(user, friends_only=True)


def _photo_html(url: str | None, size: int = 50) -> str:
    if url and url.startswith("http"):
        return (f'<img src="{url}" style="width:{size}px;height:{size}px;'
                f'border-radius:50%;object-fit:cover;border:2px solid #1565C0;flex-shrink:0;">')
    return (f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
            f'background:#1565C0;display:flex;align-items:center;justify-content:center;'
            f'color:#fff;font-size:{size//2}px;flex-shrink:0;">🎣</div>')


def _user_data(uid: str) -> dict:
    """Récupère pseudo, photo, captures, trophée pour un utilisateur."""
    profil = supabase_get("profils", {
        "id": f"eq.{uid}",
        "select": "pseudo,localisation,photo_path",
    })
    if not profil:
        return {}
    p = profil[0]

    # Captures depuis la table captures
    caps = supabase_get("captures", {
        "user_id": f"eq.{uid}",
        "select":  "id,espece,taille_cm,photo_path,poisson_trophee,created_at",
        "order":   "taille_cm.desc",
        "limit":   "200",
    })
    if not caps: caps = []

    nb = len(caps)
    best = 0.0
    best_row = None
    especes = set()
    for c in caps:
        t = float(c.get("taille_cm") or 0)
        if t > best:
            best = t
            best_row = c
        if c.get("espece"):
            especes.add(c["espece"])

    # Dernier trophée
    trophy_row = None
    for c in caps:
        if c.get("poisson_trophee"):
            trophy_row = c
            break

    return {
        "pseudo":  p["pseudo"],
        "localisation": p.get("localisation") or "—",
        "photo":   p.get("photo_path") or "",
        "nb":      nb,
        "best":    best,
        "best_row": best_row,
        "especes": len(especes),
        "trophy":  trophy_row,
    }


def _render_classement(user: dict, friends_only: bool):
    if friends_only:
        amis_rows = supabase_get("amis", {
            "or":     f"(demandeur_id.eq.{user['id']},recepteur_id.eq.{user['id']})",
            "statut": "eq.accepte",
            "select": "demandeur_id,recepteur_id",
        })
        ami_ids = []
        for a in (amis_rows or []):
            aid = a["recepteur_id"] if a["demandeur_id"] == user["id"] else a["demandeur_id"]
            ami_ids.append(aid)
        ami_ids.append(user["id"])
        ami_ids = list(set(ami_ids))

        if len(ami_ids) <= 1:
            st.info("Ajoute des amis pour voir le classement entre vous ! 👥")
            return

        users_data = [_user_data(uid) for uid in ami_ids]
    else:
        profils = supabase_get("profils", {"select": "id", "limit": "100"})
        if not profils:
            st.info("Aucun pêcheur inscrit pour l'instant.")
            return
        users_data = [_user_data(p["id"]) for p in profils]

    # Filtrer les vides + calculer points
    users_data = [u for u in users_data if u]
    for u in users_data:
        u["points"] = u["nb"] * 10 + int(u["best"]) * 2 + u["especes"] * 5
        u["moi"] = u["pseudo"] == user.get("pseudo", "")

    users_data.sort(key=lambda x: -x["points"])

    for i, u in enumerate(users_data[:20]):
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
        moi_badge = ' <span style="background:#FFD54F;color:#5d3a00;font-size:9px;font-weight:800;padding:2px 6px;border-radius:6px;">TOI</span>' if u["moi"] else ""

        # Photo dernier trophée ou meilleure prise
        trophy_photo = ""
        trophy_title = ""
        trophy_row = u["trophy"] or u["best_row"]
        if trophy_row:
            ph = trophy_row.get("photo_path") or ""
            esp = trophy_row.get("espece") or "—"
            tt = float(trophy_row.get("taille_cm") or 0)
            trophy_title = f"{'🏆 ' if u['trophy'] else '📏 '}{esp} · {int(tt)} cm"
            if ph and ph.startswith("http"):
                trophy_photo = (f'<img src="{ph}" style="width:48px;height:48px;'
                                f'object-fit:cover;border-radius:8px;border:2px solid #FFB300;">')

        photo_html  = _photo_html(u["photo"], 48)
        trophy_html = (f'<div style="display:flex;align-items:center;gap:6px;">'
                       f'{trophy_photo}'
                       f'<div style="font-size:10px;color:#546E7A;">{trophy_title}</div>'
                       f'</div>') if trophy_row else ""

        bg = "linear-gradient(135deg,#FFD54F33,#FFB30022)" if u["moi"] else "#fff"

        _comp.html(f"""
<div style="background:{bg};border:1px solid #e0e4e8;border-radius:10px;
  padding:10px 14px;margin-bottom:6px;display:flex;align-items:center;gap:12px;
  font-family:system-ui,sans-serif;">
  <div style="font-size:22px;font-weight:800;min-width:40px;text-align:center;">{medal}</div>
  {photo_html}
  <div style="flex:1;min-width:0;">
    <div style="font-size:14px;font-weight:800;color:#0c2340;">{u["pseudo"]}{moi_badge}</div>
    <div style="font-size:10px;color:#78909C;">📍 {u["localisation"]}</div>
    <div style="margin-top:4px;">
      <span style="background:#E3F2FD;color:#1565C0;font-size:10px;font-weight:700;padding:2px 7px;border-radius:6px;margin-right:3px;">🎣 {u["nb"]}</span>
      <span style="background:#FFF3E0;color:#E65100;font-size:10px;font-weight:700;padding:2px 7px;border-radius:6px;margin-right:3px;">📏 {int(u["best"])} cm</span>
      <span style="background:#E8F5E9;color:#2E7D32;font-size:10px;font-weight:700;padding:2px 7px;border-radius:6px;">🐟 {u["especes"]}</span>
    </div>
  </div>
  {trophy_html}
  <div style="background:linear-gradient(135deg,#FFB300,#E65100);color:#fff;
    border-radius:8px;padding:6px 12px;font-weight:800;font-size:14px;
    min-width:70px;text-align:center;">{u["points"]} pts</div>
</div>
""", height=90, scrolling=False)
