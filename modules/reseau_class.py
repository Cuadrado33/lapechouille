"""Classement général des pêcheurs."""
from __future__ import annotations
import streamlit as st
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
        _render_classement_global(user)

    with tab_amis:
        _render_classement_amis(user)


def _render_classement_global(user):
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:8px 14px;border-radius:8px;margin-bottom:12px;">'
        '<span style="font-size:13px;font-weight:700;">🌍 Top pêcheurs — tous les temps</span>'
        '</div>', unsafe_allow_html=True,
    )

    profils = supabase_get("profils", {"select": "id,pseudo,localisation", "limit": "100"})
    if not profils:
        st.info("Aucun pêcheur inscrit pour l'instant.")
        return

    classement = []
    for p in profils:
        posts = supabase_get("posts", {
            "user_id": f"eq.{p['id']}",
            "type":    "eq.capture",
            "select":  "taille_cm,espece",
        })
        nb = len(posts)
        best = max((float(x.get("taille_cm") or 0) for x in posts), default=0)
        especes = len({x.get("espece") for x in posts if x.get("espece")})
        points = nb * 10 + int(best) * 2 + especes * 5
        classement.append({
            "pseudo": p["pseudo"],
            "localisation": p.get("localisation") or "—",
            "nb": nb, "best": best, "especes": especes,
            "points": points,
            "moi": p["id"] == user["id"],
        })

    classement.sort(key=lambda x: -x["points"])

    for i, c in enumerate(classement[:20]):
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"**#{i+1}**"
        moi = " ← **toi**" if c["moi"] else ""
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([0.5, 2.5, 3, 1])
            c1.markdown(f"<div style='font-size:24px;text-align:center;'>{medal}</div>",
                        unsafe_allow_html=True)
            c2.markdown(f"**{c['pseudo']}**{moi}  \n📍 {c['localisation']}")
            c3.markdown(
                f'<span style="background:#E3F2FD;color:#1565C0;font-size:11px;font-weight:700;padding:2px 8px;border-radius:8px;margin-right:4px;">🎣 {c["nb"]} prises</span>'
                f'<span style="background:#FFF3E0;color:#E65100;font-size:11px;font-weight:700;padding:2px 8px;border-radius:8px;margin-right:4px;">📏 {int(c["best"])} cm</span>'
                f'<span style="background:#E8F5E9;color:#2E7D32;font-size:11px;font-weight:700;padding:2px 8px;border-radius:8px;">🐟 {c["especes"]} espèces</span>',
                unsafe_allow_html=True,
            )
            c4.markdown(
                f'<div style="background:linear-gradient(135deg,#FFB300,#E65100);color:#fff;'
                f'border-radius:8px;padding:4px 8px;text-align:center;font-weight:800;">'
                f'{c["points"]} pts</div>',
                unsafe_allow_html=True,
            )


def _render_classement_amis(user):
    from modules.reseau_amis import render_amis
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:8px 14px;border-radius:8px;margin-bottom:12px;">'
        '<span style="font-size:13px;font-weight:700;">👥 Classement entre amis</span>'
        '</div>', unsafe_allow_html=True,
    )
    # Réutilise la logique classement de reseau_amis
    from modules.reseau_amis import render_amis
    amis_rows = supabase_get("amis", {
        "or":     f"(demandeur_id.eq.{user['id']},recepteur_id.eq.{user['id']})",
        "statut": "eq.accepte",
        "select": "demandeur_id,recepteur_id",
    })
    ami_ids = []
    for a in amis_rows:
        aid = a["recepteur_id"] if a["demandeur_id"] == user["id"] else a["demandeur_id"]
        ami_ids.append(aid)
    ami_ids.append(user["id"])

    if len(ami_ids) <= 1:
        st.info("Ajoute des amis pour voir le classement entre vous ! 👥")
        return

    classement = []
    for uid in ami_ids:
        profil = supabase_get("profils", {"id": f"eq.{uid}", "select": "pseudo"})
        pseudo = profil[0]["pseudo"] if profil else "?"
        posts = supabase_get("posts", {"user_id": f"eq.{uid}", "type": "eq.capture", "select": "taille_cm"})
        nb   = len(posts)
        best = max((float(x.get("taille_cm") or 0) for x in posts), default=0)
        classement.append({"pseudo": pseudo, "nb": nb, "best": best, "moi": uid == user["id"]})
    classement.sort(key=lambda x: (-x["nb"], -x["best"]))

    for i, c in enumerate(classement):
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
        moi = " ← **toi**" if c["moi"] else ""
        with st.container(border=True):
            c1, c2, c3 = st.columns([0.5, 3, 3])
            c1.markdown(f"<div style='font-size:24px;text-align:center;'>{medal}</div>",
                        unsafe_allow_html=True)
            c2.markdown(f"**{c['pseudo']}**{moi}")
            c3.markdown(
                f'<span style="background:#E3F2FD;color:#1565C0;font-size:11px;font-weight:700;padding:2px 8px;border-radius:8px;margin-right:4px;">🎣 {c["nb"]} prises</span>'
                f'{"<span style=background:#FFF3E0;color:#E65100;font-size:11px;font-weight:700;padding:2px 8px;border-radius:8px;>📏 " + str(int(c["best"])) + " cm</span>" if c["best"] else ""}',
                unsafe_allow_html=True,
            )
