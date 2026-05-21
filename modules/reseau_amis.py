"""Module Amis — recherche, demandes, classements entre amis."""
from __future__ import annotations
import streamlit as st
from core.supabase_client import supabase_get, supabase_post, supabase_patch

def render_amis() -> None:
    user = st.session_state.get("reseau_user")

    # ── Recherche d'amis ───────────────────────────────────────
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:10px 14px;border-radius:8px;margin-bottom:12px;">'
        '<span style="font-size:14px;font-weight:800;">🔍 Trouver des pêcheurs</span>'
        '</div>', unsafe_allow_html=True,
    )

    search = st.text_input("Recherche par pseudo", placeholder="Ex: JeromeCapFerret",
                             key="ami_search")
    if search and len(search) >= 2:
        results = supabase_get("profils", {
            "pseudo": f"ilike.*{search}*",
            "select": "id,pseudo,localisation,avatar_url",
            "limit": "10",
        })
        if results:
            for r in results:
                if r["id"] == user["id"]: continue
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"**🎣 {r['pseudo']}**  ·  📍 {r.get('localisation','—')}")
                    # Vérifier si déjà amis ou demande envoyée
                    existing = supabase_get("amis", {
                        "or": f"(demandeur_id.eq.{user['id']},recepteur_id.eq.{user['id']})",
                        "select": "id,statut,demandeur_id",
                    })
                    rel = next((a for a in existing
                                if r["id"] in [a.get("demandeur_id"), a.get("recepteur_id")]), None)
                    if rel:
                        statut = rel["statut"]
                        if statut == "accepte":
                            c2.markdown("✅ Amis")
                        elif statut == "en_attente" and rel["demandeur_id"] == user["id"]:
                            c2.markdown("⏳ Demande envoyée")
                        else:
                            if c2.button("✅ Accepter", key=f"acc_{r['id']}"):
                                supabase_patch("amis", rel["id"], {"statut": "accepte"})
                                st.rerun()
                    else:
                        if c2.button("➕ Demande", key=f"req_{r['id']}", type="primary"):
                            supabase_post("amis", {
                                "demandeur_id": user["id"],
                                "recepteur_id": r["id"],
                                "statut": "en_attente",
                            })
                            st.success("Demande envoyée !")
                            st.rerun()
        else:
            st.info("Aucun pêcheur trouvé avec ce pseudo.")

    # ── Demandes reçues ────────────────────────────────────────
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:10px 14px;border-radius:8px;margin:16px 0 12px;">'
        '<span style="font-size:14px;font-weight:800;">📬 Demandes d\'amis reçues</span>'
        '</div>', unsafe_allow_html=True,
    )
    demandes = supabase_get("amis", {
        "recepteur_id": f"eq.{user['id']}",
        "statut":       "eq.en_attente",
        "select":       "id,demandeur_id,created_at",
    })
    if demandes:
        for d in demandes:
            auteur = supabase_get("profils", {"id": f"eq.{d['demandeur_id']}", "select": "pseudo,localisation"})
            if auteur:
                a = auteur[0]
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.markdown(f"**🎣 {a['pseudo']}**  ·  📍 {a.get('localisation','—')}")
                    if c2.button("✅ Accepter", key=f"acc_d_{d['id']}", type="primary"):
                        supabase_patch("amis", d["id"], {"statut": "accepte"})
                        st.rerun()
                    if c3.button("❌ Refuser", key=f"ref_d_{d['id']}"):
                        supabase_patch("amis", d["id"], {"statut": "refuse"})
                        st.rerun()
    else:
        st.info("Aucune demande en attente.")

    # ── Mes amis + classement ──────────────────────────────────
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:10px 14px;border-radius:8px;margin:16px 0 12px;">'
        '<span style="font-size:14px;font-weight:800;">🏆 Classement entre amis</span>'
        '</div>', unsafe_allow_html=True,
    )
    amis_rows = supabase_get("amis", {
        "or":    f"(demandeur_id.eq.{user['id']},recepteur_id.eq.{user['id']})",
        "statut":"eq.accepte",
        "select":"id,demandeur_id,recepteur_id",
    })
    ami_ids = []
    for a in amis_rows:
        aid = a["recepteur_id"] if a["demandeur_id"] == user["id"] else a["demandeur_id"]
        ami_ids.append(aid)
    ami_ids.append(user["id"])  # se inclure

    if len(ami_ids) > 1:
        classement = []
        for uid in ami_ids:
            profil = supabase_get("profils", {"id": f"eq.{uid}", "select": "pseudo"})
            pseudo = profil[0]["pseudo"] if profil else "?"
            posts_u = supabase_get("posts", {"user_id": f"eq.{uid}", "type": "eq.capture", "select": "espece,taille_cm"})
            nb = len(posts_u)
            best = max((p.get("taille_cm") or 0 for p in posts_u), default=0)
            classement.append({"pseudo": pseudo, "nb": nb, "best": best, "moi": uid == user["id"]})
        classement.sort(key=lambda x: (-x["nb"], -x["best"]))

        for i, c in enumerate(classement):
            medal = ["🥇","🥈","🥉"][i] if i < 3 else f"#{i+1}"
            moi_tag = " **(toi)**" if c["moi"] else ""
            with st.container(border=True):
                col_m, col_info, col_stats = st.columns([0.5, 2.5, 2])
                col_m.markdown(f"<div style='font-size:28px;text-align:center'>{medal}</div>",
                               unsafe_allow_html=True)
                col_info.markdown(f"**{c['pseudo']}**{moi_tag}")
                col_stats.markdown(
                    f'<span style="background:#E3F2FD;color:#1565C0;font-size:11px;'
                    f'font-weight:700;padding:2px 8px;border-radius:8px;margin-right:4px;">'
                    f'🐟 {c["nb"]} prises</span>'
                    f'{"<span style=background:#FFF3E0;color:#E65100;font-size:11px;font-weight:700;padding:2px 8px;border-radius:8px;>📏 " + str(int(c["best"])) + " cm</span>" if c["best"] else ""}',
                    unsafe_allow_html=True,
                )
    else:
        st.info("Ajoute des amis pour voir le classement !")
