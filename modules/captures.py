"""
Page « Mes captures » — deux points d'entrée : ajout direct + consultation.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from core.database import (
    load_sessions, load_captures, load_captures_for_session,
    insert_row, update_row, delete_capture, next_capture_number, load_spots,
    load_materiel,
)
from core.storage import save_capture_photo
from core.utils import (
    safe_str, safe_float, format_date_fr, list_index,
    estimate_fish_weight_g, format_weight_display,
)
from data.constants import (
    ESPECES, APPATS, MONTAGES,
    MARQUES_HAMECONS, TYPES_HAMECONS, MODELES_HAMECONS, TAILLES_HAMECONS,
)
from data.emojis import APPAT, icon_box
from data.fish_data import FISH_SVG, FISH_EMOJI_FALLBACK
from ui.components import hero, section, confirm_destructive, photo_inputs, photo_placeholder
import streamlit.components.v1 as _comp

# Mapping appât → emoji SVG
APPAT_SVG_MAP = {
    "Arénicole":          APPAT.get("arenicole", ""),
    "Néréide":            APPAT.get("nereide", ""),
    "Bibi":               APPAT.get("bibi", ""),
    "Couteau / Clam":     APPAT.get("couteau_clam", ""),
    "Crabe":              APPAT.get("crabe", ""),
    "Crevette":           APPAT.get("crevette", ""),
    "Seiche":             APPAT.get("seiche", ""),
    "Lançon":             APPAT.get("lancon", ""),
    "Sardine":            APPAT.get("sardine", ""),
    "Moule":              APPAT.get("moule", ""),
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _spot_info_banner() -> None:
    try:
        spots_df = load_spots()
    except Exception:
        return
    if spots_df.empty:
        return
    active_nom = st.session_state.get("active_spot_nom")
    if active_nom:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"📍 **Spot actif : {active_nom}**")
            if c2.button("Changer", key="cap_change_spot"):
                st.session_state.pop("active_spot_nom", None)
                st.rerun()
    else:
        names = ["— Choisir un spot —"] + spots_df["nom"].tolist()
        chosen = st.selectbox("⭐ Spot rapide (optionnel)", names, key="cap_spot_qs")
        if chosen != "— Choisir un spot —":
            row = spots_df[spots_df["nom"] == chosen].iloc[0]
            st.session_state["active_spot_lat"] = float(row["latitude"])
            st.session_state["active_spot_lon"] = float(row["longitude"])
            st.session_state["active_spot_nom"] = chosen
            st.rerun()


def _session_select(sessions: pd.DataFrame, key: str, default_id=None) -> int:
    options = {}
    for r in sessions.itertuples():
        d    = format_date_fr(getattr(r, "date_session", ""))
        lieu = safe_str(getattr(r, "lieu", "")) or "Sans lieu"
        options[f"{d} — {lieu}"] = int(r.id)
    labels = list(options.keys())
    def_idx = 0
    if default_id:
        for idx, lbl in enumerate(labels):
            if options[lbl] == default_id:
                def_idx = idx; break
    sel = st.selectbox("Session", labels, index=def_idx, key=key)
    return options[sel]


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    # Bandeau bleu marine pleine largeur
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:14px 20px;border-radius:8px;margin:8px 0 18px;">'
        '<span style="font-size:18px;font-weight:800;">🎣 Mes captures</span>'
        '<div style="font-size:12px;opacity:.85;margin-top:3px;">'
        'Ajoute et consulte toutes tes prises — par session ou en vue globale.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    sessions = load_sessions()
    if sessions.empty:
        st.info("Crée d'abord une session dans **Mes sessions** pour enregistrer des captures.")
        return

    tab_new, tab_session, tab_fish, tab_global = st.tabs([
        "➕ Nouvelle capture",
        "📋 Par session",
        "🐟 Par poisson",
        "📊 Vue globale",
    ])

    with tab_new:
        _render_new_capture(sessions)
    with tab_session:
        _render_captures_by_session(sessions)
    with tab_fish:
        _render_captures_by_fish(sessions)
    with tab_global:
        _render_captures_global()


# ─────────────────────────────────────────────────────────────────────────────
# Ajout d'une capture — PHOTO HORS FORM
# ─────────────────────────────────────────────────────────────────────────────

def _render_new_capture(sessions: pd.DataFrame) -> None:
    section("Ajouter une capture", icon="🐟")
    _spot_info_banner()

    # ── Photo HORS formulaire (file_uploader interdit dans st.form) ──
    with st.container(border=True):
        st.markdown("**📸 Photo de la capture**")
        col_cam, col_up = st.columns(2)
        with col_cam:
            cam = st.camera_input("Prendre une photo", key="nc_cam")
        with col_up:
            upl = st.file_uploader("Importer",
                                    type=["jpg","jpeg","png","webp"],
                                    key="nc_upl")
        new_photo = upl if upl is not None else cam
        # Stocker en bytes immédiatement pour survivre au rerun du form
        if new_photo is not None:
            st.session_state["nc_photo_bytes"] = new_photo.getvalue()
            st.session_state["nc_photo_name"]  = getattr(new_photo, "name", "capture.jpg")
        if st.session_state.get("nc_photo_bytes"):
            st.image(st.session_state["nc_photo_bytes"], width=120, caption="Aperçu")

    # ── Matériel HORS form pour que les bobines s'actualisent en live ──
    with st.expander("🎒 Matériel utilisé (canne / moulinet / bobine)"):
        # Récupérer les cannes enregistrées
        cannes_opts = ["— Aucune —"]
        try:
            df_c = load_materiel("canne")
            if not df_c.empty:
                for _, r in df_c.iterrows():
                    label = f"{safe_str(r.get('marque'))} {safe_str(r.get('modele'))}".strip()
                    if label and label not in cannes_opts:
                        cannes_opts.append(label)
        except Exception:
            pass

        moulinets_opts = ["— Aucun —"]
        moulinets_bobines = {}
        try:
            df_m = load_materiel("moulinet")
            if not df_m.empty:
                import json as _json
                for _, r in df_m.iterrows():
                    label = f"{safe_str(r.get('marque'))} {safe_str(r.get('modele'))}".strip()
                    if not label or label in moulinets_opts:
                        continue
                    moulinets_opts.append(label)
                    bobines = []
                    try:
                        bj = safe_str(r.get("bobines_json"))
                        if bj:
                            for i, b in enumerate(_json.loads(bj), start=1):
                                fl = b.get("type_fil", "")
                                dm = b.get("diametre", "")
                                bobines.append(f"Bobine {i} — {fl} {dm}".strip())
                    except Exception:
                        pass
                    moulinets_bobines[label] = bobines
        except Exception:
            pass

        mc1, mc2 = st.columns(2)
        canne_sel    = mc1.selectbox("🎯 Canne",    cannes_opts,    key="nc_canne")
        moulinet_sel = mc2.selectbox("⚙️ Moulinet", moulinets_opts, key="nc_moulinet")

        # Liste des bobines dynamique selon moulinet
        bobines_opts = ["— Aucune —"]
        if moulinet_sel and moulinet_sel != "— Aucun —":
            bobines_opts.extend(moulinets_bobines.get(moulinet_sel, []))
        # Si la bobine actuellement choisie n'est plus valable, réinitialiser
        if "nc_bobine" in st.session_state and \
           st.session_state["nc_bobine"] not in bobines_opts:
            st.session_state["nc_bobine"] = bobines_opts[0]
        bobine_sel = st.selectbox("🧵 Bobine utilisée", bobines_opts, key="nc_bobine",
                                    help="Bobines du moulinet sélectionné ci-dessus")

    with st.form("new_capture_form", clear_on_submit=True):
        session_id = _session_select(sessions, "nc_session")
        cap_num    = next_capture_number(session_id)
        st.caption(f"Capture n°{cap_num}")

        c1, c2, c3 = st.columns(3)
        with c1:
            espece = st.selectbox("Espèce", ESPECES, key="nc_espece")
            taille = st.number_input("Taille (cm)", 0.0, step=1.0, key="nc_taille")
        with c2:
            poids  = st.number_input("Poids mesuré (g)", 0.0, step=10.0, key="nc_poids")
            heure  = st.time_input("Heure",
                                    value=datetime.now().time().replace(second=0, microsecond=0),
                                    key="nc_heure")
        with c3:
            appat   = st.selectbox("Appât",   APPATS,   key="nc_appat")
            # Montages : charger d'abord les montages enregistrés
            user_montages = []
            try:
                _df_m = load_materiel("Montage")
                if not _df_m.empty:
                    for _, _r in _df_m.iterrows():
                        _nom = safe_str(_r.get("montage_nom")) or safe_str(_r.get("modele"))
                        if _nom and _nom not in user_montages:
                            user_montages.append(_nom)
            except Exception:
                pass
            montage_opts = ["— Choisir —"] + user_montages
            if user_montages:
                montage_opts.append("──────────")
            for _m in MONTAGES:
                if _m not in user_montages:
                    montage_opts.append(_m)
            montage = st.selectbox("Montage", montage_opts, key="nc_montage",
                                     help="Tes montages enregistrés en haut, classiques en dessous")
            if montage in ("— Choisir —", "──────────"):
                montage = None

        c4, c5 = st.columns(2)
        relache = c4.checkbox("↩️ Poisson relâché", value=True,  key="nc_relache")
        trophee = c5.checkbox("🏅 Trophée",         value=False, key="nc_trophee")

        with st.expander("🪝 Détails hameçon"):
            h1, h2, h3, h4 = st.columns(4)
            marque_h = h1.selectbox("Marque",  MARQUES_HAMECONS, key="nc_mh")
            type_h   = h2.selectbox("Type",    TYPES_HAMECONS,   key="nc_th")
            modele_h = h3.selectbox("Modèle",  MODELES_HAMECONS, key="nc_modh")
            taille_h = h4.selectbox("Taille",  TAILLES_HAMECONS, key="nc_tailh")

        distance    = st.number_input("Distance lancer (m)", 0.0, step=5.0, key="nc_dist")
        commentaire = st.text_area("Commentaire", key="nc_com")

        submitted = st.form_submit_button("🎣 Enregistrer la capture",
                                           use_container_width=True, type="primary")

    if submitted:
        # Récupérer les valeurs matériel sélectionnées hors form
        canne    = st.session_state.get("nc_canne",    "— Aucune —")
        moulinet = st.session_state.get("nc_moulinet", "— Aucun —")
        bobine   = st.session_state.get("nc_bobine",   "— Aucune —")

        poids_est = estimate_fish_weight_g(espece, taille) if poids <= 0 else None
        data = {
            "session_id": session_id, "capture_num": cap_num,
            "capture_label": f"Capture {cap_num}", "espece": espece,
            "taille_cm": taille or None, "poids_g": poids or None,
            "poids_estime_g": poids_est, "poisson_trophee": int(trophee),
            "heure_capture": heure.strftime("%H:%M"),
            "appat":   appat   if appat   != "Non renseigné" else None,
            "montage": montage,
            "marque_hamecon": marque_h, "type_hamecon": type_h,
            "modele_hamecon": modele_h, "taille_hamecon": taille_h,
            "hamecon": f"{marque_h} | {type_h} | {modele_h} | {taille_h}",
            "canne":           canne    if canne    not in ("— Aucune —", "")  else None,
            "moulinet":        moulinet if moulinet not in ("— Aucun —", "")   else None,
            "bobine_moulinet": bobine   if bobine   not in ("— Aucune —", "")  else None,
            "distance_lancer_m": distance or None,
            "relache": int(relache), "commentaire": commentaire,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        cap_id = insert_row("captures", data)
        # Utiliser les bytes stockés pour l'upload photo
        photo_bytes = st.session_state.get("nc_photo_bytes")
        if photo_bytes:
            import io
            f = io.BytesIO(photo_bytes)
            f.name = st.session_state.get("nc_photo_name", "capture.jpg")
            pp = save_capture_photo(f, cap_id)
            if pp:
                update_row("captures", cap_id, {"photo_path": pp})
            st.session_state.pop("nc_photo_bytes", None)
            st.session_state.pop("nc_photo_name", None)
        st.cache_data.clear()
        st.success(f"✅ Capture {cap_num} enregistrée !")
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Vue par session — cartes avec photo + modification inline
# ─────────────────────────────────────────────────────────────────────────────

def _render_captures_by_session(sessions: pd.DataFrame) -> None:
    section("Captures par session", icon="📋")
    session_id = _session_select(sessions, "cl_session")
    caps       = load_captures_for_session(session_id)

    # Résumé
    nb = len(caps)
    if nb > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("Captures", nb)
        if "taille_cm" in caps.columns:
            best = caps["taille_cm"].max()
            c2.metric("Meilleure taille", f"{best:.0f} cm" if best else "—")
        if "relache" in caps.columns:
            c3.metric("Relâchées", int(caps["relache"].sum()))

    if caps.empty:
        st.info("Aucune capture pour cette session.")
        return

    # Charger toutes les captures pour calculer les records par espèce
    from core.database import load_captures, load_sessions
    all_caps = load_captures()
    all_sess = load_sessions()

    for i, (_, row) in enumerate(caps.iterrows()):
        cap_id      = int(row["id"])
        espece      = safe_str(row.get("espece")) or "—"
        taille      = safe_float(row.get("taille_cm"))
        poids_g     = safe_float(row.get("poids_g"))
        poids_est   = safe_float(row.get("poids_estime_g"))
        poids_aff   = poids_g or poids_est
        poids_txt   = format_weight_display(row)
        heure       = safe_str(row.get("heure_capture")) or "—"
        photo_path  = safe_str(row.get("photo_path"))
        relache     = bool(row.get("relache"))
        trophee     = bool(row.get("poisson_trophee") or row.get("poisson_trophe"))
        appat       = safe_str(row.get("appat")) or ""
        montage     = safe_str(row.get("montage")) or ""
        canne       = safe_str(row.get("canne")) or ""
        moulinet    = safe_str(row.get("moulinet")) or ""
        bobine      = safe_str(row.get("bobine_moulinet")) or ""
        fil         = safe_str(row.get("fil_corps_de_ligne")) or safe_str(row.get("fil")) or ""
        taille_fil  = safe_str(row.get("taille_corps_de_ligne")) or ""
        empile      = safe_str(row.get("fil_empile")) or ""
        taille_emp  = safe_str(row.get("taille_empile")) or ""
        dist        = safe_float(row.get("distance_lancer_m"))
        commentaire = safe_str(row.get("commentaire")) or ""
        ham_marque  = safe_str(row.get("marque_hamecon")) or ""
        ham_type    = safe_str(row.get("type_hamecon")) or ""
        ham_modele  = safe_str(row.get("modele_hamecon")) or ""
        ham_taille  = safe_str(row.get("taille_hamecon")) or ""

        # Localité depuis la session liée
        lieu = "—"
        sid  = row.get("session_id")
        if sid and not all_sess.empty and "id" in all_sess.columns:
            sr = all_sess[all_sess["id"] == sid]
            if not sr.empty:
                lieu = safe_str(sr.iloc[0].get("lieu")) or "—"

        # Record personnel pour cette espèce
        record_esp = None
        if not all_caps.empty and "espece" in all_caps.columns and "taille_cm" in all_caps.columns:
            esp_caps = all_caps[all_caps["espece"] == espece]
            if not esp_caps.empty:
                tt = pd.to_numeric(esp_caps["taille_cm"], errors="coerce").dropna()
                if not tt.empty:
                    record_esp = float(tt.max())

        is_record = taille and record_esp and taille >= record_esp

        from data.fish_data import get_fish_visual
        svg_html = get_fish_visual(espece, size=80)

        # Photo lightbox
        lb_id = f"lb_cap_{cap_id}"
        photo_block = ""
        if photo_path and str(photo_path).startswith("http"):
            photo_block = f"""
<img src="{photo_path}" onclick="document.getElementById('{lb_id}').style.display='flex'"
  style="width:100%;max-height:260px;object-fit:contain;border-radius:8px;
  margin:8px 0;cursor:pointer;background:#f0f4f8;display:block;">
<div id="{lb_id}" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);
  z-index:9999;align-items:center;justify-content:center;flex-direction:column;">
  <img src="{photo_path}" style="max-width:90vw;max-height:85vh;object-fit:contain;border-radius:8px;">
  <button onclick="document.getElementById('{lb_id}').style.display='none'"
    style="margin-top:14px;background:rgba(255,255,255,.2);color:#fff;border:none;
    padding:10px 24px;border-radius:8px;font-size:14px;cursor:pointer;">Fermer</button>
</div>"""

        # Badges
        badges = []
        if trophee:   badges.append('<span style="background:#FFD54F;color:#5d3a00;font-size:10px;font-weight:800;padding:3px 8px;border-radius:6px;">TROPHEE</span>')
        if is_record: badges.append('<span style="background:#E8F5E9;color:#1B5E20;font-size:10px;font-weight:800;padding:3px 8px;border-radius:6px;">RECORD PERSO</span>')
        badges.append(f'<span style="background:{"#E8F5E9" if not relache else "#FFF3E0"};color:{"#2E7D32" if not relache else "#E65100"};font-size:10px;font-weight:700;padding:3px 8px;border-radius:6px;">{"GARDE" if not relache else "RELACHE"}</span>')
        badges_html = " ".join(badges)

        # Section Poisson
        poisson_rows = []
        if taille:    poisson_rows.append(f'<div class="lp-row"><span class="lp-lbl">Taille</span><span class="lp-val lp-blue">{taille:.0f} cm</span></div>')
        if poids_aff: poisson_rows.append(f'<div class="lp-row"><span class="lp-lbl">Poids</span><span class="lp-val lp-orange">{poids_txt}</span></div>')
        if record_esp and taille:
            diff = taille - record_esp
            diff_txt = f"+{diff:.0f} cm" if diff > 0 else (f"Record !" if diff == 0 else f"{diff:.0f} cm du record")
            poisson_rows.append(f'<div class="lp-row"><span class="lp-lbl">Record perso {espece}</span><span class="lp-val" style="color:#2E7D32;">{record_esp:.0f} cm &nbsp;({diff_txt})</span></div>')
        poisson_rows.append(f'<div class="lp-row"><span class="lp-lbl">Lieu</span><span class="lp-val">{lieu}</span></div>')
        poisson_rows.append(f'<div class="lp-row"><span class="lp-lbl">Heure</span><span class="lp-val">{heure}</span></div>')
        if dist:      poisson_rows.append(f'<div class="lp-row"><span class="lp-lbl">Distance lancer</span><span class="lp-val">{dist:.0f} m</span></div>')

        # Section Technique
        tech_rows = []
        if appat:     tech_rows.append(f'<div class="lp-row"><span class="lp-lbl">Appat</span><span class="lp-val">{appat}</span></div>')
        if montage:   tech_rows.append(f'<div class="lp-row"><span class="lp-lbl">Montage</span><span class="lp-val">{montage}</span></div>')
        if canne:     tech_rows.append(f'<div class="lp-row"><span class="lp-lbl">Canne</span><span class="lp-val">{canne}</span></div>')
        if moulinet:  tech_rows.append(f'<div class="lp-row"><span class="lp-lbl">Moulinet</span><span class="lp-val">{moulinet}</span></div>')
        if bobine:    tech_rows.append(f'<div class="lp-row"><span class="lp-lbl">Bobine</span><span class="lp-val">{bobine}</span></div>')
        if fil:
            fil_txt = fil + (f" {taille_fil}" if taille_fil else "")
            tech_rows.append(f'<div class="lp-row"><span class="lp-lbl">Corps de ligne</span><span class="lp-val">{fil_txt}</span></div>')
        if empile:
            emp_txt = empile + (f" {taille_emp}" if taille_emp else "")
            tech_rows.append(f'<div class="lp-row"><span class="lp-lbl">Empile</span><span class="lp-val">{emp_txt}</span></div>')
        ham = " ".join(filter(None, [ham_marque, ham_type, ham_modele, f"#{ham_taille}" if ham_taille else ""]))
        if ham:       tech_rows.append(f'<div class="lp-row"><span class="lp-lbl">Hamecon</span><span class="lp-val">{ham}</span></div>')

        poisson_html = "".join(poisson_rows)
        tech_html    = "".join(tech_rows)
        tech_section = f'<div class="lp-section-title">Technique</div>{tech_html}' if tech_html else ""
        comment_section = f'<div style="background:#f8f9fa;border-left:3px solid #1565C0;padding:8px 12px;border-radius:4px;font-size:12px;color:#546E7A;font-style:italic;margin-top:8px;">{commentaire}</div>' if commentaire else ""

        # Hauteur dynamique : base + lignes + photo
        h_base   = 80   # header seulement (sans SVG)
        h_rows   = (len(poisson_rows) + len(tech_rows)) * 28
        h_titles = 30 + (30 if tech_html else 0)
        h_photo  = 270 if photo_block else 0
        h_com    = 50  if commentaire else 0
        h_total  = h_base + h_rows + h_titles + h_photo + h_com + 30

        with st.container(border=True):
            _comp.html(f"""
<style>
.lp-card {{ font-family:system-ui,sans-serif;color:#1a2332; }}
.lp-header {{ background:linear-gradient(135deg,#0c2340,#1565C0);color:#fff;
  padding:10px 14px;border-radius:10px;margin-bottom:10px; }}
.lp-species {{ font-size:17px;font-weight:900;letter-spacing:.3px; }}
.lp-badges {{ margin-top:5px;display:flex;gap:6px;flex-wrap:wrap; }}
.lp-svg {{ background:#f0f6ff;border-radius:8px;padding:10px;
  display:flex;align-items:center;justify-content:center;margin-bottom:8px; }}
.lp-section-title {{ font-size:9px;font-weight:800;letter-spacing:1.5px;
  text-transform:uppercase;color:#90A4AE;margin:10px 0 4px; }}
.lp-row {{ display:flex;justify-content:space-between;align-items:center;
  padding:4px 0;border-bottom:1px solid #f0f4f8; }}
.lp-lbl {{ font-size:11px;color:#78909C;font-weight:500; }}
.lp-val {{ font-size:12px;font-weight:700;color:#1a2332; }}
.lp-blue {{ background:#E3F2FD;color:#1565C0;padding:1px 7px;border-radius:6px; }}
.lp-orange {{ background:#FFF3E0;color:#E65100;padding:1px 7px;border-radius:6px; }}
</style>
<div class="lp-card">
  <div class="lp-header">
    <div class="lp-species">🐟 {espece}</div>
    <div class="lp-badges">{badges_html}</div>
  </div>
  {photo_block}
  <div class="lp-section-title">Capture</div>
  {poisson_html}
  {tech_section}
  {comment_section}
</div>
""", height=h_total, scrolling=False)

            c1, c2, c3 = st.columns(3)
            edit_key = f"cap_edit_open_{cap_id}"
            if c1.button("Modifier", key=f"cap_edit_btn_{cap_id}", use_container_width=True):
                st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                st.rerun()
            share_key = f"cap_share_{cap_id}"
            if c2.button("📤 Partager", key=f"cap_share_btn_{cap_id}", use_container_width=True):
                st.session_state[share_key] = not st.session_state.get(share_key, False)
                st.rerun()
            if c3.button("Supprimer", key=f"cap_del_{cap_id}", use_container_width=True):
                st.session_state[f"confirm_cap_{cap_id}"] = True

            if st.session_state.get(share_key):
                from ui.components import share_button
                txt = (f"🎣 La Péchouille — Ma capture\n\n"
                       f"🐟 {espece}\n"
                       f"📏 {taille:.0f} cm · {poids_txt}\n"
                       f"📍 {lieu}\n"
                       f"🕐 {heure}\n"
                       + (f"🪱 {appat}\n" if appat else "")
                       + "\nApp : https://lapechouille.fr")
                share_button(txt, share_key)

            if st.session_state.get(f"confirm_cap_{cap_id}"):
                if confirm_destructive(f"cap_{cap_id}", f"Supprimer {espece} ?"):
                    delete_capture(cap_id)
                    st.session_state[f"confirm_cap_{cap_id}"] = False
                    st.cache_data.clear()
                    st.rerun()

            if st.session_state.get(edit_key):
                _render_edit_capture(row, cap_id)


def _render_edit_capture(row, cap_id: int) -> None:
    with st.container(border=True):
        st.markdown("**✏️ Modifier**")

        with st.container(border=True):
            col_cam, col_up = st.columns(2)
            with col_cam:
                cam = st.camera_input("Nouvelle photo", key=f"ec_cam_{cap_id}")
            with col_up:
                upl = st.file_uploader("Importer", type=["jpg","jpeg","png","webp"],
                                        key=f"ec_upl_{cap_id}")
            new_photo = upl if upl is not None else cam

        with st.form(f"edit_cap_{cap_id}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                espece = st.selectbox("Espèce", ESPECES,
                                       index=list_index(ESPECES, row.get("espece")),
                                       key=f"ec_esp_{cap_id}")
                taille = st.number_input("Taille (cm)", 0.0,
                                          value=safe_float(row.get("taille_cm")),
                                          step=1.0, key=f"ec_t_{cap_id}")
            with c2:
                poids = st.number_input("Poids (g)", 0.0,
                                         value=safe_float(row.get("poids_g")),
                                         step=10.0, key=f"ec_p_{cap_id}")
                appat = st.selectbox("Appât", APPATS,
                                      index=list_index(APPATS, row.get("appat")),
                                      key=f"ec_a_{cap_id}")
            with c3:
                relache = st.checkbox("↩️ Relâché",
                                       value=bool(row.get("relache")),
                                       key=f"ec_r_{cap_id}")
                trophee = st.checkbox("🏅 Trophée",
                                       value=bool(row.get("poisson_trophee") or row.get("poisson_trophe")),
                                       key=f"ec_tr_{cap_id}")

            commentaire = st.text_area("Commentaire",
                                        value=safe_str(row.get("commentaire")),
                                        key=f"ec_com_{cap_id}")

            if st.form_submit_button("💾 Enregistrer", use_container_width=True, type="primary"):
                poids_est = estimate_fish_weight_g(espece, taille) if poids <= 0 else None
                data = {
                    "espece": espece, "taille_cm": taille or None,
                    "poids_g": poids or None, "poids_estime_g": poids_est,
                    "appat": appat if appat != "Non renseigné" else None,
                    "relache": int(relache), "poisson_trophee": int(trophee),
                    "commentaire": commentaire,
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                }
                update_row("captures", cap_id, data)
                if new_photo:
                    pp = save_capture_photo(new_photo, cap_id)
                    if pp:
                        update_row("captures", cap_id, {"photo_path": pp})
                st.session_state[f"cap_edit_open_{cap_id}"] = False
                st.cache_data.clear()
                st.success("✅ Capture modifiée !")
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Tableau complet
# ─────────────────────────────────────────────────────────────────────────────

def _render_captures_by_fish(sessions: pd.DataFrame) -> None:
    """Affiche toutes les captures groupées par espèce, avec filtre."""
    section("Captures par poisson", icon="🐟")

    captures = load_captures()
    if captures.empty:
        st.info("Aucune capture enregistrée.")
        return

    # Index session_id → ligne pour récupérer date/lieu
    sess_idx = {}
    if not sessions.empty:
        for _, s in sessions.iterrows():
            sess_idx[int(s["id"])] = s

    # Nettoyer
    cap = captures.copy()
    if "espece" not in cap.columns:
        st.warning("Données incomplètes.")
        return
    cap["espece"] = cap["espece"].fillna("").astype(str)
    cap = cap[cap["espece"].str.strip() != ""]
    if cap.empty:
        st.info("Aucune capture avec espèce identifiée.")
        return

    # ── Filtre par espèce ──────────────────────────────────────────
    especes_disponibles = sorted(cap["espece"].unique().tolist())
    options = ["🌍 Toutes les espèces"] + especes_disponibles
    selection = st.selectbox(
        "Filtrer par poisson",
        options,
        key="bf_filter",
        help="Affiche toutes les prises d'une espèce ou laisse vide pour tout voir",
    )

    if selection != "🌍 Toutes les espèces":
        cap = cap[cap["espece"] == selection]

    # ── Stats sur la sélection ─────────────────────────────────────
    nb_total = len(cap)
    if "taille_cm" in cap.columns:
        tt = pd.to_numeric(cap["taille_cm"], errors="coerce").dropna()
        tt = tt[tt > 0]
        best_t = tt.max() if not tt.empty else None
    else:
        best_t = None
    if "poids_g" in cap.columns:
        pp = pd.to_numeric(cap["poids_g"], errors="coerce").dropna()
        pp = pp[pp > 0]
        best_p = pp.max() if not pp.empty else None
    else:
        best_p = None

    m1, m2, m3 = st.columns(3)
    m1.metric("🎣 Prises", nb_total)
    m2.metric("📏 Record taille", f"{best_t:.0f} cm" if best_t else "—")
    if best_p:
        p_txt = f"{best_p/1000:.2f} kg" if best_p >= 1000 else f"{best_p:.0f} g"
    else:
        p_txt = "—"
    m3.metric("⚖️ Record poids", p_txt)

    st.markdown("---")

    # ── Affichage groupé par espèce ────────────────────────────────
    from data.fish_data import FISH_SVG, FISH_META, FISH_EMOJI_FALLBACK
    from modules.identification import _capture_matches_fish

    for espece, group in cap.groupby("espece"):
        nb_esp = len(group)

        # Trouver la fiche FISH_META correspondante pour le SVG
        fish_match = None
        for f in FISH_META:
            if _capture_matches_fish(espece, f):
                fish_match = f
                break
        svg = FISH_SVG.get(fish_match["id"], "") if fish_match else ""
        emoji = FISH_EMOJI_FALLBACK.get(fish_match["id"], "🐟") if fish_match else "🐟"

        # En-tête de groupe : bandeau vert avec espèce + nb prises
        # SVG inline ou emoji
        if svg:
            ico_html = (f'<div style="display:inline-block;vertical-align:middle;'
                          f'width:50px;height:30px;overflow:hidden;">'
                          f'<div style="width:60px;margin-top:-5px;">{svg}</div></div>')
        else:
            ico_html = f'<span style="font-size:24px;">{emoji}</span>'

        st.markdown(
            f'<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
            f'color:#fff;padding:10px 14px;border-radius:8px;margin:14px 0 10px;'
            f'display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">'
            f'<div>{ico_html} <span style="font-size:16px;font-weight:800;'
            f'margin-left:8px;">{espece}</span></div>'
            f'<div style="background:rgba(255,255,255,.25);font-size:12px;font-weight:700;'
            f'padding:3px 10px;border-radius:10px;">{nb_esp} prise(s)</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Tri par taille décroissante puis date (les plus belles d'abord)
        group_sorted = group.copy()
        if "taille_cm" in group_sorted.columns:
            group_sorted["_tri"] = pd.to_numeric(group_sorted["taille_cm"],
                                                    errors="coerce").fillna(0)
            group_sorted = group_sorted.sort_values("_tri", ascending=False)

        for _, row in group_sorted.iterrows():
            cap_id     = int(row["id"])
            taille     = safe_float(row.get("taille_cm"))
            poids_txt  = format_weight_display(row)
            heure      = safe_str(row.get("heure_capture")) or "—"
            photo_path = safe_str(row.get("photo_path"))
            relache    = bool(row.get("relache"))
            trophee    = bool(row.get("poisson_trophee") or row.get("poisson_trophe"))
            appat      = safe_str(row.get("appat")) or ""
            montage    = safe_str(row.get("montage")) or ""

            # Date + lieu via session
            session_id = row.get("session_id")
            d_str, lieu_str, type_sess = "—", "—", ""
            if pd.notna(session_id) and int(session_id) in sess_idx:
                s = sess_idx[int(session_id)]
                d_str    = format_date_fr(s.get("date_session")) or "—"
                lieu_str = safe_str(s.get("lieu")) or "—"
                type_sess = safe_str(s.get("type_session")) or ""

            # Couleur selon type de session
            type_color = "#C62828" if "ompétition" in type_sess \
                         else ("#EF6C00" if "ntra" in type_sess else "#2E7D32")
            type_icon  = "🏆" if "ompétition" in type_sess \
                         else ("🎯" if "ntra" in type_sess else "🎣")

            # Badges relâché / trophée
            badge_html = ""
            if trophee:
                badge_html += ('<span style="background:#FFD54F;color:#5d4f1a;'
                                'font-size:10px;font-weight:700;padding:2px 7px;'
                                'border-radius:8px;margin-right:4px;">🏆 TROPHÉE</span>')
            if relache:
                badge_html += ('<span style="background:#E8F5E9;color:#2E7D32;'
                                'font-size:10px;font-weight:700;padding:2px 7px;'
                                'border-radius:8px;margin-right:4px;">↩️ Relâché</span>')
            else:
                badge_html += ('<span style="background:#E3F2FD;color:#1565C0;'
                                'font-size:10px;font-weight:700;padding:2px 7px;'
                                'border-radius:8px;margin-right:4px;">📦 Gardé</span>')

            with st.container(border=True):
                col_img, col_main, col_size = st.columns([1, 3, 1])
                with col_img:
                    if photo_path and str(photo_path).startswith("http"):
                        if str(photo_path).startswith("http"):
                            _comp.html(
                                f'<img src="{photo_path}" style="width:100%;aspect-ratio:1;'
                                f'object-fit:cover;border-radius:8px;">',
                                height=110, scrolling=False,
                            )
                        else:
                            import streamlit.components.v1 as _cv2
                            _cv2.html(
                                f'<img src="{photo_path}" style="width:100%;max-height:200px;'
                                f'object-fit:contain;border-radius:8px;">',
                                height=208, scrolling=False,
                            )
                    else:
                        from data.fish_data import get_fish_visual
                        visual_html = get_fish_visual(espece, size=100)
                        _comp.html(
                            f'<div style="display:flex;align-items:center;justify-content:center;'
                            f'aspect-ratio:1;">{visual_html}</div>',
                            height=110, scrolling=False,
                        )

                with col_main:
                    st.markdown(
                        f'<div style="margin-bottom:6px;">{badge_html}</div>'
                        f'<div style="font-size:13px;color:#0c2340;">'
                        f'<span style="color:{type_color};font-weight:700;">{type_icon} {lieu_str}</span>'
                        f' · 📅 {d_str} · 🕐 {heure}</div>',
                        unsafe_allow_html=True,
                    )
                    extra_lines = []
                    if appat:
                        extra_lines.append(f"🪱 <strong>Appât :</strong> {appat}")
                    if montage:
                        extra_lines.append(f"🧵 <strong>Montage :</strong> {montage}")
                    if extra_lines:
                        st.markdown(
                            f'<div style="font-size:12px;color:#37474F;margin-top:4px;">'
                            + " · ".join(extra_lines) +
                            '</div>',
                            unsafe_allow_html=True,
                        )
                    # Matériel + hameçon
                    mat = []
                    if safe_str(row.get("canne")):    mat.append(f"🎯 {row['canne']}")
                    if safe_str(row.get("moulinet")): mat.append(f"⚙️ {row['moulinet']}")
                    if safe_str(row.get("bobine_moulinet")): mat.append(f"🧵 {row['bobine_moulinet']}")
                    if mat:
                        st.markdown(
                            f'<div style="font-size:11px;color:#546E7A;margin-top:2px;">'
                            + " · ".join(mat) + '</div>',
                            unsafe_allow_html=True,
                        )
                    ham = " ".join(filter(None, [
                        safe_str(row.get("marque_hamecon")),
                        safe_str(row.get("modele_hamecon")),
                        f"#{row['taille_hamecon']}" if safe_str(row.get("taille_hamecon")) else ""
                    ]))
                    if ham:
                        st.markdown(
                            f'<div style="font-size:11px;color:#546E7A;margin-top:2px;">🪝 {ham}</div>',
                            unsafe_allow_html=True,
                        )

                with col_size:
                    taille_txt = f"{taille:.0f} cm" if taille else "—"
                    st.markdown(
                        f'<div style="background:linear-gradient(135deg,#FFB300,#E65100);'
                        f'color:#fff;border-radius:8px;padding:8px;text-align:center;'
                        f'min-height:60px;display:flex;flex-direction:column;justify-content:center;">'
                        f'<div style="font-size:18px;font-weight:900;">{taille_txt}</div>'
                        f'<div style="font-size:11px;opacity:.9;">{poids_txt or ""}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                # Boutons Modifier (vert via CSS global) / Supprimer (rouge via CSS global)
                ba1, ba2 = st.columns(2)
                edit_key = f"bf_edit_open_{cap_id}"
                with ba1:
                    lbl_e = "✕ Fermer" if st.session_state.get(edit_key) else "✏️ Modifier"
                    if st.button(lbl_e, key=f"bf_edit_btn_{cap_id}",
                                  use_container_width=True):
                        st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                        st.rerun()
                with ba2:
                    if st.button("🗑️ Supprimer", key=f"bf_del_{cap_id}",
                                  use_container_width=True):
                        st.session_state[f"bf_confirm_{cap_id}"] = True

                if st.session_state.get(f"bf_confirm_{cap_id}"):
                    if confirm_destructive(f"bf_cap_{cap_id}",
                                           f"Supprimer cette prise de {espece} ?"):
                        delete_capture(cap_id)
                        st.session_state[f"bf_confirm_{cap_id}"] = False
                        st.cache_data.clear()
                        st.rerun()

                # Édition inline (réutilise _render_edit_capture déjà défini)
                if st.session_state.get(edit_key):
                    _render_edit_capture(row, cap_id)


def _render_captures_global() -> None:
    captures = load_captures()
    if captures.empty:
        st.info("Aucune capture enregistrée.")
        return

    # ── Stats globales ─────────────────────────────────────────────
    nb_total      = len(captures)
    nb_especes    = captures["espece"].nunique() if "espece" in captures.columns else 0
    nb_relachees  = 0
    if "relache" in captures.columns:
        nb_relachees = int(captures["relache"].fillna(0).astype(int).sum())
    record_t = "—"
    record_p = "—"
    if "taille_cm" in captures.columns:
        ts = pd.to_numeric(captures["taille_cm"], errors="coerce").dropna()
        ts = ts[ts > 0]
        if not ts.empty:
            record_t = f"{ts.max():.0f} cm"
    if "poids_g" in captures.columns:
        ps = pd.to_numeric(captures["poids_g"], errors="coerce").dropna()
        ps = ps[ps > 0]
        if not ps.empty:
            mv = ps.max()
            record_p = f"{mv/1000:.2f} kg" if mv >= 1000 else f"{mv:.0f} g"

    section("Statistiques globales", icon="📊")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total prises",  nb_total)
    m2.metric("Espèces",       nb_especes)
    m3.metric("Relâchées",     nb_relachees)
    m4.metric("Record taille", record_t)
    m5.metric("Record poids",  record_p)

    # ── Répartition par espèce ─────────────────────────────────────
    if "espece" in captures.columns:
        section("Captures par espèce", icon="🐟")
        counts = (captures["espece"].fillna("—").value_counts()
                                       .reset_index()
                                       .rename(columns={"index": "Espèce",
                                                         "espece": "Espèce",
                                                         "count": "Nb prises"}))
        # Selon version pandas la colonne s'appelle différemment, on s'adapte
        if "count" in counts.columns:
            counts.columns = ["Espèce", "Nb prises"]
        st.dataframe(counts, use_container_width=True, hide_index=True)

    # ── Tableau filtrable ──────────────────────────────────────────
    section("Tableau filtrable", icon="🔍")
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        esp_filter = st.selectbox("Espèce", ["Toutes"] + ESPECES, key="cg_esp")
    with fc2:
        rel_filter = st.selectbox("Statut", ["Tous", "Relâchés", "Gardés"], key="cg_rel")
    with fc3:
        search = st.text_input("Rechercher", placeholder="Appât, lieu…", key="cg_search")

    df = captures.copy()
    if esp_filter != "Toutes" and "espece" in df.columns:
        df = df[df["espece"] == esp_filter]
    if rel_filter == "Relâchés" and "relache" in df.columns:
        df = df[df["relache"].fillna(0).astype(int) == 1]
    elif rel_filter == "Gardés" and "relache" in df.columns:
        df = df[df["relache"].fillna(0).astype(int) == 0]
    if search:
        s = search.lower()
        df = df[df.astype(str).apply(lambda c: c.str.lower().str.contains(s, na=False)).any(axis=1)]

    st.caption(f"**{len(df)} capture(s)** affichée(s)")

    display_cols = [c for c in [
        "date_session", "lieu", "espece", "taille_cm", "poids_g",
        "appat", "montage", "relache", "commentaire",
    ] if c in df.columns]
    st.dataframe(df[display_cols].head(500), use_container_width=True, hide_index=True)
    st.download_button(
        "📥 Export CSV",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="captures.csv",
        mime="text/csv",
    )


# Conservé en alias pour compat (au cas où d'autres modules y feraient référence)
def _render_captures_table() -> None:
    _render_captures_global()
