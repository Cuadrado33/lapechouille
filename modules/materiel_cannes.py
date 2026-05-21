"""Page Cannes — inventaire."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import streamlit as st
from core.database import load_materiel, insert_row, update_row, delete_row
from core.storage import save_materiel_photo
from core.utils import safe_str, safe_float
from data.constants import MARQUES_MATERIEL, ETATS_MATERIEL, TYPES_SCION, ACTIONS_CANNE
from ui.components import hero, section, confirm_destructive, photo_inputs, photo_placeholder

def render() -> None:
    hero("Axe 3 · Matériel", "Mes cannes", "Inventaire de tes cannes surfcasting.")
    tab_add, tab_list = st.tabs(["➕ Ajouter", "📚 Consulter"])
    with tab_add:
        _render_add()
    with tab_list:
        _render_list()

def _render_add() -> None:
    with st.form("add_canne", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            marque = st.selectbox("Marque", MARQUES_MATERIEL, key="ac_marque")
            modele = st.text_input("Modèle", key="ac_modele")
            longueur = st.text_input("Longueur", placeholder="Ex. 4,20 m", key="ac_long")
        with c2:
            puissance = st.text_input("Puissance", placeholder="Ex. 100-250 g", key="ac_puis")
            scion = st.selectbox("Type scion", TYPES_SCION, key="ac_scion")
            action = st.selectbox("Action", ACTIONS_CANNE, key="ac_action")
        etat = st.selectbox("État", ETATS_MATERIEL, key="ac_etat")
        commentaire = st.text_area("Commentaire", key="ac_com")
        photo = photo_inputs("ac")
        if st.form_submit_button("➕ Ajouter la canne"):
            data = {"categorie": "Canne", "marque": marque, "modele": modele,
                    "longueur_canne": longueur, "puissance_canne": puissance,
                    "type_scion": scion, "action_canne": action, "etat": etat,
                    "commentaire": commentaire,
                    "created_at": datetime.now().isoformat(timespec="seconds")}
            mid = insert_row("materiel", data)
            if photo:
                pp = save_materiel_photo(photo, mid, "canne")
                if pp: update_row("materiel", mid, {"photo_path": pp})
            st.cache_data.clear()
            st.success("Canne ajoutée.")
            st.rerun()

def _render_list() -> None:
    df = load_materiel("canne")
    if df.empty:
        st.info("Aucune canne enregistrée.")
        return
    _render_cards(df, "canne")

def _render_cards(df, kind):
    search = st.text_input("Rechercher", placeholder="Marque, modèle...", key=f"search_{kind}")
    if search:
        s = search.lower()
        mask = df.astype(str).apply(lambda c: c.str.lower().str.contains(s, na=False)).any(axis=1)
        df = df[mask]
    if df.empty:
        st.info("Aucun résultat.")
        return
    for _, row in df.iterrows():
        item_id = int(row["id"])
        photo_path = safe_str(row.get("photo_path")) if "photo_path" in row.index else ""
        marque = safe_str(row.get("marque")) or "—"
        modele = safe_str(row.get("modele")) or "—"
        with st.container(border=True):
            c_photo, c_main, c_actions = st.columns([1, 3.5, 1.5])
            with c_photo:
                if photo_path and Path(photo_path).exists():
                    st.image(photo_path, use_container_width=True)
                else:
                    photo_placeholder()
            with c_main:
                st.markdown(f"**{marque} {modele}**")
                details = []
                for lbl, k in [("Longueur","longueur_canne"),("Puissance","puissance_canne"),
                                ("Action","action_canne"),("Scion","type_scion"),("État","etat")]:
                    v = safe_str(row.get(k)) if k in row.index else ""
                    if v: details.append(f"{lbl} : {v}")
                st.caption(" · ".join(details) if details else "")
            with c_actions:
                if st.button("🗑️ Supprimer", key=f"del_{kind}_{item_id}", use_container_width=True):
                    st.session_state[f"confirm_{kind}_{item_id}"] = True
            if st.session_state.get(f"confirm_{kind}_{item_id}"):
                if confirm_destructive(f"{kind}_{item_id}", f"Supprimer {marque} {modele} ?"):
                    delete_row("materiel", item_id)
                    st.session_state[f"confirm_{kind}_{item_id}"] = False
                    st.cache_data.clear()
                    st.success("Supprimé.")
                    st.rerun()
