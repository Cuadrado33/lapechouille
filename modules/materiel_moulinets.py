"""
Page Moulinets — inventaire avec 4 bobines détaillées par défaut.
Chaque bobine : type fil, diamètre, résistance estimée auto, capacité, marque/modèle fil, état, note.
Bouton ➕ pour ajouter jusqu'à 8 bobines.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json

import streamlit as st
import streamlit.components.v1 as components

from core.database import load_materiel, insert_row, update_row, delete_row
from core.storage import save_materiel_photo
from core.utils import safe_str, safe_float, format_resistance
from data.constants import MARQUES_MATERIEL, ETATS_MATERIEL, TYPES_MOULINET
from ui.components import hero, section, confirm_destructive, photo_inputs, photo_placeholder

# ── Constantes bobines ────────────────────────────────────────────────────────
TYPES_FIL = ["Nylon", "Tresse", "Fluorocarbone"]

DIAMETRES_COMMUNS = [
    # Tous les diamètres couverts par les tables de résistance (6/100 → 100/100)
    # L'interpolation calcule la résistance même pour les valeurs intermédiaires
    "6/100",  "7/100",  "8/100",  "9/100",  "10/100",
    "11/100", "12/100", "13/100", "14/100", "15/100",
    "16/100", "17/100", "18/100", "19/100", "20/100",
    "22/100", "24/100", "25/100", "26/100", "28/100",
    "30/100", "32/100", "35/100", "40/100", "45/100",
    "50/100", "55/100", "60/100", "70/100", "80/100",
    "90/100", "100/100",
    "Autre / libre",
]

MARQUES_FIL = [
    "Asso", "Berkley", "Daiwa", "Garbolino", "Maxima", "Mitchell",
    "PowerPro", "Shimano", "Spiderwire", "Stroft", "Sufix", "Sunline",
    "Toray", "Ultima", "YGK", "Yuki", "Autre",
]

NB_BOBINES_DEFAULT = 2
NB_BOBINES_MAX     = 8

# Couleurs par type de fil
FIL_COLOR = {
    "Nylon":         "#1565C0",
    "Tresse":        "#E65100",
    "Fluorocarbone": "#6A1B9A",
}


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    hero("Axe 3 · Matériel", "Mes moulinets",
         "Inventaire complet — caractéristiques + 4 bobines avec résistance estimée.")
    tab_add, tab_list = st.tabs(["➕ Ajouter", "📚 Consulter & Modifier"])
    with tab_add:
        _render_add()
    with tab_list:
        _render_list()


# ─────────────────────────────────────────────────────────────────────────────
# Formulaire bobines — réutilisé à l'ajout ET à la modification
# ─────────────────────────────────────────────────────────────────────────────

def _render_bobines_section(prefix: str, existing: list[dict]) -> None:
    nb_key  = f"{prefix}_nb_bob"
    del_key = f"{prefix}_del_bob"  # index à supprimer (-1 = rien)

    if nb_key not in st.session_state:
        st.session_state[nb_key] = max(NB_BOBINES_DEFAULT, len(existing))
    if del_key not in st.session_state:
        st.session_state[del_key] = -1

    nb = int(st.session_state[nb_key])

    st.markdown("---")
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">'
        f'<span style="font-size:16px;font-weight:800;">🔵 Bobines</span>'
        f'<span style="background:#1565C020;color:#1565C0;border:1px solid #1565C055;'
        f'border-radius:20px;padding:2px 10px;font-size:12px;font-weight:700;">'
        f'{nb} / {NB_BOBINES_MAX}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.caption("Les 2 premières bobines sont incluses par défaut.")

    for i in range(nb):
        prev = existing[i] if i < len(existing) else {}
        is_extra = i >= NB_BOBINES_DEFAULT
        border_color = "#E65100" if is_extra else "#1565C0"
        label_txt = f"Bobine {i + 1}" + (" — supplémentaire" if is_extra else "")

        st.markdown(
            f'<div style="background:{border_color};color:#fff;'
            f'padding:8px 14px;font-weight:800;font-size:13px;'
            f'letter-spacing:.3px;border-radius:8px 8px 0 0;margin-top:16px;">'
            f'{"🔵" if not is_extra else "🟠"} {label_txt}</div>',
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            # Bouton supprimer dans l'en-tête de chaque bobine
            c_del = st.columns([5, 1])
            with c_del[1]:
                if st.form_submit_button(
                    "🗑️ Supprimer",
                    key=f"{prefix}_del_btn_{i}",
                    help=f"Supprimer la bobine {i+1}",
                ):
                    st.session_state[del_key] = i
                    st.rerun()

            c1, c2, c3 = st.columns([1.4, 2.2, 1.4])
            with c1:
                tf_idx   = TYPES_FIL.index(prev.get("type_fil","Nylon")) \
                           if prev.get("type_fil") in TYPES_FIL else 0
                type_fil = st.selectbox("Type de fil", TYPES_FIL, index=tf_idx,
                                         key=f"{prefix}_b{i}_type")
            with c2:
                diam_prev = prev.get("diametre", "")
                if diam_prev and diam_prev not in DIAMETRES_COMMUNS:
                    diam_choice_init = "Autre / libre"
                else:
                    diam_choice_init = diam_prev if diam_prev in DIAMETRES_COMMUNS else "25/100"
                diam_sel_idx = DIAMETRES_COMMUNS.index(diam_choice_init) \
                               if diam_choice_init in DIAMETRES_COMMUNS else 0
                diam_sel = st.selectbox("Diamètre", DIAMETRES_COMMUNS, index=diam_sel_idx,
                                         key=f"{prefix}_b{i}_diam_sel")
                if diam_sel == "Autre / libre":
                    diametre = st.text_input("Diamètre libre", value=diam_prev,
                                              placeholder="Ex : 27/100",
                                              key=f"{prefix}_b{i}_diam_libre")
                else:
                    diametre = diam_sel
            with c3:
                st.markdown("**Résistance estimée**")
                res_txt = format_resistance(type_fil, diametre)
                col     = FIL_COLOR.get(type_fil, "#555")
                components.html(
                    f'<div style="margin-top:2px;padding:7px 10px;background:{col}18;'
                    f'border:2px solid {col};border-radius:8px;font-family:system-ui;'
                    f'font-size:17px;font-weight:900;color:{col};text-align:center;">'
                    f'{res_txt}</div>',
                    height=48, scrolling=False,
                )

            c4, c5, c6 = st.columns([1.5, 1.5, 1.5])
            with c4:
                capacite = st.text_input("Capacité (mètres)",
                                          value=prev.get("capacite",""),
                                          placeholder="Ex : 300 m",
                                          key=f"{prefix}_b{i}_cap")
            with c5:
                mf_idx   = MARQUES_FIL.index(prev.get("marque_fil","Autre")) \
                           if prev.get("marque_fil") in MARQUES_FIL else len(MARQUES_FIL)-1
                marque_f = st.selectbox("Marque du fil", MARQUES_FIL, index=mf_idx,
                                         key=f"{prefix}_b{i}_mf")
            with c6:
                modele_f = st.text_input("Modèle / ref.",
                                          value=prev.get("modele_fil",""),
                                          placeholder="Ex : J-Braid X8",
                                          key=f"{prefix}_b{i}_modele")

            c7, c8 = st.columns([1, 2])
            with c7:
                et_idx = ETATS_MATERIEL.index(prev.get("etat","Bon")) \
                         if prev.get("etat") in ETATS_MATERIEL else 2
                etat_b = st.selectbox("État", ETATS_MATERIEL, index=et_idx,
                                       key=f"{prefix}_b{i}_etat")
            with c8:
                note_b = st.text_input("Note / usage",
                                        value=prev.get("note",""),
                                        placeholder="Ex : surfcasting bars…",
                                        key=f"{prefix}_b{i}_note")

    st.markdown("")
    if nb < NB_BOBINES_MAX:
        if st.form_submit_button(
            f"➕ Ajouter une bobine supplémentaire ({nb}/{NB_BOBINES_MAX})",
            use_container_width=True,
        ):
            st.session_state[nb_key] = nb + 1
            st.rerun()


def _collect_bobines(prefix: str) -> list[dict]:
    """Lit les widgets bobines depuis session_state après soumission.
    Si un index de suppression est en attente, on le retire de la liste."""
    nb      = int(st.session_state.get(f"{prefix}_nb_bob", NB_BOBINES_DEFAULT))
    del_idx = st.session_state.get(f"{prefix}_del_bob", -1)
    out = []
    for i in range(nb):
        if i == del_idx:
            continue  # sauter la bobine supprimée
        diam_sel   = st.session_state.get(f"{prefix}_b{i}_diam_sel", "")
        diam_libre = st.session_state.get(f"{prefix}_b{i}_diam_libre", "")
        diametre   = diam_libre if diam_sel == "Autre / libre" else diam_sel
        out.append({
            "type_fil":   st.session_state.get(f"{prefix}_b{i}_type",   "Nylon"),
            "diametre":   diametre,
            "capacite":   st.session_state.get(f"{prefix}_b{i}_cap",    ""),
            "marque_fil": st.session_state.get(f"{prefix}_b{i}_mf",     ""),
            "modele_fil": st.session_state.get(f"{prefix}_b{i}_modele", ""),
            "etat":       st.session_state.get(f"{prefix}_b{i}_etat",   "Bon"),
            "note":       st.session_state.get(f"{prefix}_b{i}_note",   ""),
        })
    # Appliquer la suppression : décrémenter nb et reset del_idx
    if del_idx >= 0:
        st.session_state[f"{prefix}_nb_bob"] = max(NB_BOBINES_DEFAULT, nb - 1)
        st.session_state[f"{prefix}_del_bob"] = -1
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Ajout
# ─────────────────────────────────────────────────────────────────────────────

def _render_add() -> None:
    section("Nouveau moulinet", icon="⚙️")

    # Photo hors form
    with st.container(border=True):
        st.markdown("**📸 Photo du moulinet**")
        photo = photo_inputs("am_photo")

    with st.form("add_moulinet"):
        c1, c2 = st.columns(2)
        with c1:
            marque   = st.selectbox("Marque",    MARQUES_MATERIEL, key="am_marque")
            modele   = st.text_input("Modèle",   placeholder="Ex. Daiwa Emblem X 14000", key="am_modele")
            type_m   = st.selectbox("Type",      TYPES_MOULINET, key="am_type")
            taille   = st.text_input("Taille",   placeholder="Ex. 14000", key="am_taille")
        with c2:
            ratio    = st.text_input("Ratio",    placeholder="Ex. 4.3:1", key="am_ratio")
            frein    = st.text_input("Frein (kg)", placeholder="Ex. 15", key="am_frein")
            poids    = st.text_input("Poids (g)", placeholder="Ex. 535", key="am_poids")

        etat        = st.selectbox("État général", ETATS_MATERIEL, key="am_etat")
        commentaire = st.text_area("Commentaire", key="am_com")

        _render_bobines_section("am", [])

        submitted = st.form_submit_button("➕ Enregistrer le moulinet",
                                           use_container_width=True, type="primary")

    if submitted and st.session_state.get("am_modele","").strip():
        bobines = _collect_bobines("am")
        data = {
            "categorie":     "Moulinet",
            "marque":        st.session_state.get("am_marque",""),
            "modele":        st.session_state.get("am_modele",""),
            "type_moulinet": st.session_state.get("am_type",""),
            "taille_moulinet": st.session_state.get("am_taille",""),
            "ratio_moulinet":  st.session_state.get("am_ratio",""),
            "frein_kg":        st.session_state.get("am_frein",""),
            "poids_moulinet_g": st.session_state.get("am_poids",""),
            "capacite_bobine": bobines[0]["capacite"] if bobines else "",
            "bobines_json":    json.dumps(bobines, ensure_ascii=False),
            "etat":            st.session_state.get("am_etat",""),
            "commentaire":     st.session_state.get("am_com",""),
            "created_at":      datetime.now().isoformat(timespec="seconds"),
        }
        mid = insert_row("materiel", data)
        if photo:
            pp = save_materiel_photo(photo, mid, "moulinet")
            if pp:
                update_row("materiel", mid, {"photo_path": pp})

        # Nettoyer le cache ET toutes les clés du formulaire d'ajout
        st.cache_data.clear()
        # Liste explicite des clés à effacer (préfixe "am_")
        keys_to_clear = [k for k in list(st.session_state.keys())
                         if k.startswith("am_")]
        for k in keys_to_clear:
            st.session_state.pop(k, None)

        st.success(f"✅ Moulinet enregistré !")
        st.rerun()
    elif submitted:
        st.error("Le modèle est obligatoire.")


# ─────────────────────────────────────────────────────────────────────────────
# Liste
# ─────────────────────────────────────────────────────────────────────────────

def _render_list() -> None:
    df = load_materiel("moulin")
    if df.empty:
        st.info("Aucun moulinet enregistré. Utilise l'onglet « Ajouter ».")
        return

    search = st.text_input("🔍 Rechercher", placeholder="Marque, modèle…", key="search_moulinet")
    if search:
        s = search.lower()
        df = df[df.astype(str).apply(lambda c: c.str.lower().str.contains(s, na=False)).any(axis=1)]

    if df.empty:
        st.info("Aucun résultat.")
        return

    for i, (_, row) in enumerate(df.iterrows()):
        item_id    = int(row["id"])
        photo_path = safe_str(row.get("photo_path",""))
        marque     = safe_str(row.get("marque","")) or "—"
        modele     = safe_str(row.get("modele","")) or "—"
        etat       = safe_str(row.get("etat",""))

        # Parse bobines existantes
        bobines_raw = safe_str(row.get("bobines_json","")) if "bobines_json" in row.index else ""
        try:
            bobines = json.loads(bobines_raw) if bobines_raw else []
        except Exception:
            bobines = []
        # Toujours avoir au moins NB_BOBINES_DEFAULT slots
        while len(bobines) < NB_BOBINES_DEFAULT:
            bobines.append({})

        bg = "#ffffff" if i % 2 == 0 else "#f0f4f8"

        etat_html = f'<span style="background:rgba(255,255,255,.2);font-size:10px;' \
                    f'font-weight:600;padding:2px 8px;border-radius:10px;margin-left:8px;">' \
                    f'{etat}</span>' if etat else ""
        with st.container(border=True):
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
                f'color:#fff;padding:10px 14px;border-radius:8px;margin-bottom:12px;">'
                f'<span style="font-size:16px;font-weight:700;">⚙️ {marque} {modele}</span>'
                f'{etat_html}'
                f'</div>',
                unsafe_allow_html=True,
            )

            c_photo, c_main, c_actions = st.columns([1, 4, 1.5])

            with c_photo:
                if photo_path and str(photo_path).startswith("http"):
                    import streamlit.components.v1 as _cv
                    _cv.html(
                        f'<img src="{photo_path}" style="width:100%;max-height:120px;'
                        f'object-fit:cover;border-radius:8px;">',
                        height=128, scrolling=False,
                    )
                else:
                    photo_placeholder()

            with c_main:
                specs = []
                for lbl, k in [("Type","type_moulinet"),("Taille","taille_moulinet"),
                                ("Ratio","ratio_moulinet"),("Frein","frein_kg"),
                                ("Poids","poids_moulinet_g")]:
                    v = safe_str(row.get(k,"")) if k in row.index else ""
                    if v:
                        specs.append(f"**{lbl}** : {v}")
                if specs:
                    st.markdown("  ·  ".join(specs))
                if safe_str(row.get("commentaire","")):
                    st.caption(f"💬 {safe_str(row.get('commentaire',''))}")

                # Tableau des bobines
                _render_bobines_table(bobines)

            with c_actions:
                edit_key = f"edit_moul_{item_id}"
                share_key = f"share_moul_{item_id}"
                edit_lbl = "✕ Fermer" if st.session_state.get(edit_key) else "✏️ Modifier"
                if st.button(edit_lbl, key=f"edit_btn_{item_id}", use_container_width=True):
                    st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                    st.rerun()
                if st.button("📤 Partager", key=f"share_btn_moul_{item_id}", use_container_width=True):
                    st.session_state[share_key] = not st.session_state.get(share_key, False)
                    st.rerun()
                if st.button("🗑️ Supprimer", key=f"del_{item_id}", use_container_width=True):
                    st.session_state[f"confirm_{item_id}"] = True

            if st.session_state.get(share_key):
                from ui.components import share_button
                txt = (f"🎣 La Péchouille — Mon moulinet\n\n"
                       f"⚙️ {marque} {modele}\n"
                       + "\nApp : https://lapechouille.fr")
                share_button(txt, share_key)

            if st.session_state.get(f"confirm_{item_id}"):
                if confirm_destructive(f"moul_{item_id}", f"Supprimer {marque} {modele} ?"):
                    delete_row("materiel", item_id)
                    st.session_state.pop(f"confirm_{item_id}", None)
                    st.cache_data.clear()
                    st.success("Supprimé.")
                    st.rerun()

            if st.session_state.get(edit_key):
                _render_edit(item_id, row, bobines)


def _render_bobines_table(bobines: list[dict]) -> None:
    """Tableau HTML compact — une ligne par bobine."""
    rows = ""
    for idx, b in enumerate(bobines):
        tf   = b.get("type_fil","")
        diam = b.get("diametre","")
        cap  = b.get("capacite","")
        mf   = b.get("marque_fil","")
        mfl  = b.get("modele_fil","")
        note = b.get("note","")
        etat = b.get("etat","")

        bg = "#fff" if idx % 2 == 0 else "#f5f7fb"

        if not tf and not diam and not cap:
            rows += (
                f'<tr style="background:{bg};">'
                f'<td style="padding:5px 8px;font-weight:700;color:#bbb;">Bobine {idx+1}</td>'
                f'<td colspan="4" style="color:#ccc;font-style:italic;font-size:11px;padding:5px 8px;">vide</td>'
                f'</tr>'
            )
            continue

        col = FIL_COLOR.get(tf, "#555")
        res = format_resistance(tf, diam) if tf and diam else "—"
        fil_info = " ".join(filter(None, [mf if mf != "Autre" else "", mfl]))
        extras   = "  ·  ".join(filter(None, [
            cap, fil_info,
            etat if etat not in ("Bon","Neuf","") else "",
            f"💬 {note}" if note else "",
        ]))

        rows += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:5px 8px;font-weight:700;font-size:12px;">Bobine {idx+1}</td>'
            f'<td style="padding:5px 8px;">'
            f'<span style="background:{col}18;color:{col};border:1px solid {col}44;'
            f'border-radius:5px;padding:2px 8px;font-size:11px;font-weight:700;">{tf or "—"}</span>'
            f'</td>'
            f'<td style="padding:5px 8px;font-family:monospace;font-size:12px;">{diam or "—"}</td>'
            f'<td style="padding:5px 8px;font-weight:700;color:{col};font-size:12px;">{res}</td>'
            f'<td style="padding:5px 8px;color:#555;font-size:11px;">{extras}</td>'
            f'</tr>'
        )

    if not rows:
        return

    table = (
        '<table style="width:100%;border-collapse:collapse;font-family:system-ui;margin-top:8px;">'
        '<thead><tr style="background:#e8edf2;">'
        '<th style="padding:4px 8px;text-align:left;font-size:10px;text-transform:uppercase;'
        'letter-spacing:.8px;color:#555;font-weight:700;">#</th>'
        '<th style="padding:4px 8px;text-align:left;font-size:10px;text-transform:uppercase;'
        'letter-spacing:.8px;color:#555;font-weight:700;">Type</th>'
        '<th style="padding:4px 8px;text-align:left;font-size:10px;text-transform:uppercase;'
        'letter-spacing:.8px;color:#555;font-weight:700;">Ø</th>'
        '<th style="padding:4px 8px;text-align:left;font-size:10px;text-transform:uppercase;'
        'letter-spacing:.8px;color:#555;font-weight:700;">Résistance</th>'
        '<th style="padding:4px 8px;text-align:left;font-size:10px;text-transform:uppercase;'
        'letter-spacing:.8px;color:#555;font-weight:700;">Capacité / Fil / Note</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody></table>'
    )
    h = len(bobines) * 34 + 42
    components.html(table, height=h, scrolling=False)


# ─────────────────────────────────────────────────────────────────────────────
# Modification inline
# ─────────────────────────────────────────────────────────────────────────────

def _render_edit(item_id: int, row, existing_bobines: list[dict]) -> None:
    with st.container(border=True):
        st.markdown("**✏️ Modifier ce moulinet**")

        with st.container(border=True):
            st.markdown("**📸 Changer la photo**")
            new_photo = photo_inputs(f"em_photo_{item_id}")

        pfx = f"em_{item_id}"

        with st.form(f"edit_moulinet_{item_id}"):
            c1, c2 = st.columns(2)
            with c1:
                mi = MARQUES_MATERIEL.index(row["marque"]) \
                     if row.get("marque") in MARQUES_MATERIEL else 0
                marque  = st.selectbox("Marque", MARQUES_MATERIEL, index=mi,
                                        key=f"{pfx}_marque")
                modele  = st.text_input("Modèle", value=safe_str(row.get("modele","")),
                                         key=f"{pfx}_modele")
                ti = TYPES_MOULINET.index(row["type_moulinet"]) \
                     if row.get("type_moulinet") in TYPES_MOULINET else 0
                type_m  = st.selectbox("Type", TYPES_MOULINET, index=ti,
                                        key=f"{pfx}_type")
                taille  = st.text_input("Taille", value=safe_str(row.get("taille_moulinet","")),
                                         key=f"{pfx}_taille")
            with c2:
                ratio   = st.text_input("Ratio",  value=safe_str(row.get("ratio_moulinet","")),
                                         key=f"{pfx}_ratio")
                frein   = st.text_input("Frein",  value=safe_str(row.get("frein_kg","")),
                                         key=f"{pfx}_frein")
                poids   = st.text_input("Poids",  value=safe_str(row.get("poids_moulinet_g","")),
                                         key=f"{pfx}_poids")

            ei = ETATS_MATERIEL.index(row["etat"]) if row.get("etat") in ETATS_MATERIEL else 0
            etat = st.selectbox("État général", ETATS_MATERIEL, index=ei, key=f"{pfx}_etat")
            commentaire = st.text_area("Commentaire",
                                        value=safe_str(row.get("commentaire","")),
                                        key=f"{pfx}_com")

            _render_bobines_section(pfx, existing_bobines)

            saved = st.form_submit_button("💾 Enregistrer",
                                           use_container_width=True, type="primary")

        if saved:
            bobines = _collect_bobines(pfx)
            data = {
                "marque": marque, "modele": modele,
                "type_moulinet": type_m, "taille_moulinet": taille,
                "ratio_moulinet": ratio, "frein_kg": frein,
                "poids_moulinet_g": poids,
                "capacite_bobine": bobines[0]["capacite"] if bobines else "",
                "bobines_json": json.dumps(bobines, ensure_ascii=False),
                "etat": etat, "commentaire": commentaire,
            }
            if new_photo:
                pp = save_materiel_photo(new_photo, item_id, "moulinet")
                if pp:
                    data["photo_path"] = pp
            update_row("materiel", item_id, data)
            st.cache_data.clear()
            st.session_state[f"edit_moul_{item_id}"] = False
            st.session_state.pop(f"{pfx}_nb_bob", None)
            st.success("✅ Moulinet mis à jour !")
            st.rerun()
