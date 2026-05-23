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
    import streamlit.components.v1 as _cv

    search = st.text_input("Rechercher", placeholder="Marque, modèle...", key=f"search_{kind}")
    if search:
        s = search.lower()
        mask = df.astype(str).apply(lambda c: c.str.lower().str.contains(s, na=False)).any(axis=1)
        df = df[mask]
    if df.empty:
        st.info("Aucun résultat.")
        return

    for row_start in range(0, len(df), 3):
        row_items = df.iloc[row_start:row_start+3]
        cols = st.columns(len(row_items))

        for col, (_, row) in zip(cols, row_items.iterrows()):
            item_id    = int(row["id"])
            photo_path = safe_str(row.get("photo_path")) if "photo_path" in row.index else ""
            marque     = safe_str(row.get("marque")) or "—"
            modele     = safe_str(row.get("modele")) or "—"

            with col:
                with st.container(border=True):
                    # Bandeau bleu titre
                    st.markdown(
                        f'<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
                        f'color:#fff;padding:6px 10px;border-radius:6px;margin-bottom:8px;">'
                        f'<span style="font-size:13px;font-weight:800;">🎯 {marque}</span>'
                        f'<div style="font-size:11px;opacity:.85;">{modele}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    # Photo portrait complète + lightbox
                    if photo_path and str(photo_path).startswith("http"):
                        lb_id = f"lb_canne_{item_id}"
                        _cv.html(f"""
<img src="{photo_path}"
  onclick="document.getElementById('{lb_id}').style.display='flex'"
  style="width:100%;max-height:300px;object-fit:contain;border-radius:6px;
  margin-bottom:6px;cursor:pointer;background:#f5f5f5;display:block;">
<div id="{lb_id}" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);
  z-index:9999;align-items:center;justify-content:center;flex-direction:column;">
  <img src="{photo_path}" style="max-width:90vw;max-height:85vh;object-fit:contain;border-radius:8px;">
  <button onclick="document.getElementById('{lb_id}').style.display='none'"
    style="margin-top:14px;background:rgba(255,255,255,.2);color:#fff;border:none;
    padding:10px 24px;border-radius:8px;font-size:14px;cursor:pointer;">✕ Fermer</button>
</div>
""", height=310, scrolling=False)

                    # Pastilles caractéristiques
                    badges = []
                    for lbl, k, color, bg in [
                        ("longueur_canne",  "📏", "#1565C0", "#E3F2FD"),
                        ("puissance_canne", "⚡", "#E65100", "#FFF3E0"),
                        ("action_canne",    "🎯", "#2E7D32", "#E8F5E9"),
                        ("type_scion",      "🔧", "#6A1B9A", "#F3E5F5"),
                    ]:
                        v = safe_str(row.get(lbl)) if lbl in row.index else ""
                        if v:
                            badges.append(
                                f'<span style="background:{bg};color:{color};'
                                f'font-size:10px;font-weight:700;padding:2px 7px;'
                                f'border-radius:8px;margin:2px;">{k} {v}</span>'
                            )
                    if badges:
                        st.markdown(
                            '<div style="display:flex;flex-wrap:wrap;gap:3px;margin-bottom:6px;">'
                            + "".join(badges) + '</div>',
                            unsafe_allow_html=True,
                        )

                    # État
                    etat = safe_str(row.get("etat")) if "etat" in row.index else ""
                    if etat:
                        etat_color = {"Neuf":"#2E7D32","Bon état":"#1565C0",
                                      "Usé":"#E65100","À remplacer":"#C62828"}.get(etat,"#546E7A")
                        st.markdown(
                            f'<span style="background:{etat_color}22;color:{etat_color};'
                            f'font-size:10px;font-weight:700;padding:2px 8px;border-radius:8px;">'
                            f'{etat}</span>',
                            unsafe_allow_html=True,
                        )

                    com = safe_str(row.get("commentaire")) if "commentaire" in row.index else ""
                    if com:
                        st.caption(f"💬 {com}")

                    # Boutons Modifier / Partager / Supprimer
                    ca, cb, cc = st.columns(3)
                    edit_key  = f"edit_{kind}_{item_id}"
                    share_key = f"share_{kind}_{item_id}"
                    if ca.button("✏️", key=f"edit_btn_{kind}_{item_id}",
                                  use_container_width=True, help="Modifier"):
                        st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                        st.rerun()
                    if cb.button("📤", key=f"share_btn_{kind}_{item_id}",
                                  use_container_width=True, help="Partager"):
                        st.session_state[share_key] = not st.session_state.get(share_key, False)
                        st.rerun()
                    if cc.button("🗑️", key=f"del_{kind}_{item_id}",
                                  use_container_width=True, help="Supprimer"):
                        st.session_state[f"confirm_{kind}_{item_id}"] = True

                    if st.session_state.get(share_key):
                        from ui.components import share_button
                        long_c  = safe_str(row.get("longueur_canne")) if "longueur_canne" in row.index else ""
                        puis_c  = safe_str(row.get("puissance_canne")) if "puissance_canne" in row.index else ""
                        txt = (f"🎣 La Péchouille — Ma canne\n\n"
                               f"🎯 {marque} {modele}\n"
                               + (f"📏 {long_c}\n" if long_c else "")
                               + (f"⚡ {puis_c}\n" if puis_c else "")
                               + (f"État : {etat}\n" if etat else "")
                               + "\nApp : https://lapechouille.fr")
                        share_button(txt, share_key)

                    if st.session_state.get(f"confirm_{kind}_{item_id}"):
                        if confirm_destructive(f"{kind}_{item_id}", f"Supprimer {marque} {modele} ?"):
                            delete_row("materiel", item_id)
                            st.session_state[f"confirm_{kind}_{item_id}"] = False
                            st.cache_data.clear()
                            st.rerun()

                    if st.session_state.get(edit_key):
                        _render_edit(row, item_id, kind)


def _render_edit(row, item_id: int, kind: str) -> None:
    """Formulaire d'édition inline d'une canne."""
    with st.form(f"edit_form_{kind}_{item_id}"):
        st.markdown("**✏️ Modifier cette canne**")
        c1, c2 = st.columns(2)
        marque   = c1.text_input("Marque",    value=safe_str(row.get("marque")),          key=f"em_marque_{item_id}")
        modele   = c2.text_input("Modèle",    value=safe_str(row.get("modele")),           key=f"em_modele_{item_id}")
        longueur = c1.text_input("Longueur",  value=safe_str(row.get("longueur_canne")),  key=f"em_long_{item_id}")
        puissance= c2.text_input("Puissance", value=safe_str(row.get("puissance_canne")), key=f"em_puis_{item_id}")
        from data.constants import TYPES_SCION, ACTIONS_CANNE, ETATS_MATERIEL
        scion    = c1.selectbox("Scion",  TYPES_SCION,    key=f"em_scion_{item_id}")
        action   = c2.selectbox("Action", ACTIONS_CANNE,  key=f"em_action_{item_id}")
        etat     = st.selectbox("État",   ETATS_MATERIEL, key=f"em_etat_{item_id}")
        com      = st.text_area("Commentaire", value=safe_str(row.get("commentaire")),    key=f"em_com_{item_id}")
        if st.form_submit_button("💾 Sauvegarder", use_container_width=True, type="primary"):
            update_row("materiel", item_id, {
                "marque": marque, "modele": modele,
                "longueur_canne": longueur, "puissance_canne": puissance,
                "type_scion": scion, "action_canne": action,
                "etat": etat, "commentaire": com,
            })
            st.session_state.pop(f"edit_canne_{item_id}", None)
            st.cache_data.clear()
            st.success("✅ Canne mise à jour.")
            st.rerun()

    # Photo
    st.markdown("**📸 Changer la photo**")
    new_photo = photo_inputs(f"ep_{kind}_{item_id}")
    if new_photo:
        pp = save_materiel_photo(new_photo, item_id, kind)
        if pp:
            update_row("materiel", item_id, {"photo_path": pp})
            st.cache_data.clear()
            st.success("Photo mise à jour.")
            st.rerun()
