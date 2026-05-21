"""Page Matériel divers — bobines, fils, hameçons, plombs, accessoires."""
from __future__ import annotations
from datetime import datetime
import streamlit as st
from core.database import load_materiel, insert_row, delete_row
from core.utils import safe_str
from data.constants import MARQUES_MATERIEL, ETATS_MATERIEL
from ui.components import hero, section, confirm_destructive

CATS_DIVERS = ["Bobine", "Fil", "Hameçon", "Plomb", "Pique / support",
               "Sac / rangement", "Lampe", "Waders / vêtements", "Accessoire", "Autre"]

def render() -> None:
    hero("Axe 3 · Matériel", "Matériel divers", "Bobines, fils, hameçons, plombs, accessoires.")
    tab_add, tab_list = st.tabs(["➕ Ajouter", "📚 Consulter"])
    with tab_add:
        with st.form("add_divers", clear_on_submit=True):
            categorie = st.selectbox("Catégorie", CATS_DIVERS, key="ad_cat")
            c1, c2 = st.columns(2)
            with c1:
                marque = st.selectbox("Marque", MARQUES_MATERIEL, key="ad_marque")
                modele = st.text_input("Modèle", key="ad_modele")
            with c2:
                etat = st.selectbox("État", ETATS_MATERIEL, key="ad_etat")
                reference = st.text_input("Référence", key="ad_ref")
            commentaire = st.text_area("Commentaire", key="ad_com")
            if st.form_submit_button("➕ Ajouter"):
                insert_row("materiel", {"categorie": categorie, "marque": marque, "modele": modele,
                           "reference": reference, "etat": etat, "commentaire": commentaire,
                           "created_at": datetime.now().isoformat(timespec="seconds")})
                st.cache_data.clear()
                st.success("Matériel ajouté.")
                st.rerun()
    with tab_list:
        df = load_materiel()
        if df.empty:
            st.info("Aucun matériel enregistré.")
            return
        exclude = {"canne", "moulinet", "montage"}
        df = df[~df["categorie"].fillna("").str.lower().isin(exclude)]
        if df.empty:
            st.info("Aucun matériel divers.")
            return
        for _, row in df.iterrows():
            item_id = int(row["id"])
            marque = safe_str(row.get("marque")) or "—"
            modele = safe_str(row.get("modele")) or "—"
            cat = safe_str(row.get("categorie")) or "—"
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"**{cat}** — {marque} {modele}")
                c1.caption(safe_str(row.get("commentaire")) or "")
                if c2.button("🗑️ Supprimer", key=f"del_div_{item_id}", use_container_width=True):
                    delete_row("materiel", item_id)
                    st.cache_data.clear()
                    st.rerun()
