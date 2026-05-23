"""Page Montages — inventaire avec empiles détaillées."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
import streamlit as st

from core.database import load_materiel, insert_row, update_row, delete_row
from core.storage import save_materiel_photo
from core.utils import safe_str
from data.constants import (
    FILS_BOBINE, FILS_EMPILE, TAILLES_LIGNE, LONGUEURS_CM, ESPECES,
    MARQUES_HAMECONS, TYPES_HAMECONS, MODELES_HAMECONS, TAILLES_HAMECONS,
)
from ui.components import (
    hero, section, confirm_destructive, photo_inputs, photo_placeholder,
)

# Longueurs typiques d'empile (cm)
LONGUEURS_EMPILE = [
    "10 cm", "15 cm", "20 cm", "25 cm", "30 cm", "40 cm", "50 cm",
    "60 cm", "80 cm", "100 cm", "120 cm", "150 cm", "Autre",
]


def render() -> None:
    # Bandeau bleu marine
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:14px 20px;border-radius:8px;margin:8px 0 18px;">'
        '<span style="font-size:18px;font-weight:800;">🧵 Mes montages</span>'
        '<div style="font-size:12px;opacity:.85;margin-top:3px;">'
        'Crée et consulte tes montages surfcasting avec empiles détaillées.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    tab_add, tab_list = st.tabs(["➕ Créer", "📐 Mes montages"])
    with tab_add:
        _render_add()
    with tab_list:
        _render_list()


# ─────────────────────────────────────────────────────────────────────────────
# Création d'un montage
# ─────────────────────────────────────────────────────────────────────────────

def _render_add() -> None:
    section("Nouveau montage", icon="🧵")

    # ── Photo HORS form ──────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**📸 Photo du montage** *(optionnel)*")
        photo = photo_inputs("amon")

    # ── Infos générales HORS form (pour que nb_empiles déclenche un rerun) ──
    with st.container(border=True):
        st.markdown("**📋 Informations générales**")
        nom = st.text_input("Nom du montage *",
                              placeholder="Ex : Traînard long spécial dorade",
                              key="amon_nom")
        c1, c2, c3 = st.columns(3)
        with c1:
            longueur_tot = st.selectbox("Longueur totale", LONGUEURS_CM, key="amon_longtot")
            type_corps   = st.selectbox("Fil corps de ligne", FILS_BOBINE, key="amon_corps_type")
        with c2:
            diametre_corps = st.selectbox("Diamètre corps", TAILLES_LIGNE, key="amon_corps_diam")
            plomb          = st.text_input("Plomb conseillé",
                                              placeholder="Ex : 100 g grappin",
                                              key="amon_plomb")
        with c3:
            cible       = st.selectbox("Poisson cible", ESPECES, key="amon_cible")
            nb_empiles  = st.number_input("Nombre d'empiles",
                                            min_value=1, max_value=6, value=2, step=1,
                                            key="amon_nb_emp",
                                            help="Le formulaire affiche un bloc par empile")

    # ── Empiles : N blocs dynamiques ─────────────────────────────────
    section(f"Empiles ({int(nb_empiles)})", icon="🪝")
    st.caption("Renseigne les caractéristiques de chaque empile (du haut vers le bas).")

    for i in range(int(nb_empiles)):
        prefix = f"amon_emp{i}"
        with st.container(border=True):
            # Bandeau identifiant l'empile
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#37474F,#263238);'
                f'color:#fff;padding:6px 12px;border-radius:6px;margin-bottom:8px;">'
                f'<strong>🪝 Empile {i + 1}</strong></div>',
                unsafe_allow_html=True,
            )
            ec1, ec2 = st.columns(2)
            with ec1:
                st.selectbox("Type de fil",
                             FILS_EMPILE,
                             key=f"{prefix}_type_fil",
                             help="Nylon, fluorocarbone, tresse…")
                st.selectbox("Diamètre du fil",
                             TAILLES_LIGNE,
                             key=f"{prefix}_diam")
                st.selectbox("Longueur d'empile",
                             LONGUEURS_EMPILE,
                             key=f"{prefix}_longueur")
            with ec2:
                st.selectbox("Marque hameçon",
                             MARQUES_HAMECONS,
                             key=f"{prefix}_marque_h")
                st.selectbox("Modèle hameçon",
                             MODELES_HAMECONS,
                             key=f"{prefix}_modele_h")
                st.selectbox("Taille hameçon",
                             TAILLES_HAMECONS,
                             key=f"{prefix}_taille_h")

            ec3, ec4 = st.columns(2)
            with ec3:
                st.text_input("Perles / attractants",
                              placeholder="Ex : 3 perles rouges fluo + plumes",
                              key=f"{prefix}_perles")
            with ec4:
                st.text_input("Commentaire empile",
                              placeholder="Ex : bras de potence 8 cm, agrafe rapide",
                              key=f"{prefix}_com")

    # ── Accessoires globaux ──────────────────────────────────────────
    section("Accessoires & notes", icon="📝")
    accessoires = st.text_area("Accessoires globaux",
                                placeholder="Émerillons, perles flottantes, agrafes Rosco…",
                                key="amon_acc")

    st.divider()

    # ── Bouton d'enregistrement ──────────────────────────────────────
    if st.button("💾 Enregistrer le montage", use_container_width=True,
                  type="primary", key="amon_save"):
        if not nom.strip():
            st.error("Le nom du montage est obligatoire.")
            return

        # Récupérer chaque empile depuis session_state
        empiles = []
        for i in range(int(nb_empiles)):
            prefix = f"amon_emp{i}"
            empiles.append({
                "index":         i + 1,
                "type_fil":      st.session_state.get(f"{prefix}_type_fil", ""),
                "diametre":      st.session_state.get(f"{prefix}_diam", ""),
                "longueur":      st.session_state.get(f"{prefix}_longueur", ""),
                "marque_h":      st.session_state.get(f"{prefix}_marque_h", ""),
                "modele_h":      st.session_state.get(f"{prefix}_modele_h", ""),
                "taille_h":      st.session_state.get(f"{prefix}_taille_h", ""),
                "perles":        st.session_state.get(f"{prefix}_perles", ""),
                "commentaire":   st.session_state.get(f"{prefix}_com", ""),
            })

        data = {
            "categorie":                "Montage",
            "montage_nom":              nom.strip(),
            "modele":                   nom.strip(),
            "montage_longueur_totale":  longueur_tot,
            "montage_type_corps":       type_corps,
            "montage_diametre_corps":   diametre_corps,
            "montage_nb_empiles":       int(nb_empiles),
            "montage_plomb":            plomb,
            "montage_cible":            cible,
            "montage_accessoires":      accessoires,
            "empiles_json":             json.dumps(empiles, ensure_ascii=False),
            "created_at":               datetime.now().isoformat(timespec="seconds"),
        }
        mid = insert_row("materiel", data)
        if photo:
            pp = save_materiel_photo(photo, mid, "montage")
            if pp:
                update_row("materiel", mid, {"photo_path": pp})

        # Nettoyage des keys du formulaire
        st.cache_data.clear()
        keys_to_clear = [k for k in list(st.session_state.keys())
                         if k.startswith("amon_")]
        for k in keys_to_clear:
            st.session_state.pop(k, None)

        st.success(f"✅ Montage « {nom} » enregistré avec {len(empiles)} empile(s).")
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Liste des montages
# ─────────────────────────────────────────────────────────────────────────────

def _generate_montage_svg(row, empiles: list, compact: bool = False) -> str:
    """
    Génère un schéma SVG technique d'un montage surfcasting.
    Vue verticale : plomb en bas, corps de ligne vers le haut, empiles latérales.
    compact=True → version réduite pour la vignette (200px de haut)
    compact=False → version complète avec légendes détaillées
    """
    from core.utils import safe_str

    # ── Données du montage ──────────────────────────────────────────
    plomb         = safe_str(row.get("montage_plomb")) or "Plomb"
    type_corps    = safe_str(row.get("montage_type_corps")) or "Corps"
    diam_corps    = safe_str(row.get("montage_diametre_corps")) or ""
    longueur_tot  = safe_str(row.get("montage_longueur_totale")) or ""
    accessoires   = safe_str(row.get("montage_accessoires")) or ""
    nom           = safe_str(row.get("montage_nom")) or safe_str(row.get("modele")) or "Montage"

    # ── Dimensions SVG ──────────────────────────────────────────────
    nb_emp    = len(empiles) or 1
    if compact:
        W, margin_left, margin_right = 340, 20, 20
        empile_h   = min(60, int(260 / max(nb_emp, 1)))
        top_pad    = 24
        bottom_pad = 40
        font_main  = 10
        font_sub   = 8
        corps_x    = 80
        arm_len    = 180
    else:
        W, margin_left, margin_right = 540, 30, 30
        empile_h   = 100
        top_pad    = 40
        bottom_pad = 60
        font_main  = 12
        font_sub   = 10
        corps_x    = 140
        arm_len    = 260

    H = top_pad + nb_emp * empile_h + bottom_pad

    # Couleurs par type de fil
    FIL_COLORS = {
        "nylon":        "#4FC3F7",
        "fluorocarbone": "#FFB300",
        "fluoro":       "#FFB300",
        "tresse":       "#EF9A9A",
        "autre":        "#CE93D8",
    }

    def fil_color(fil_type: str) -> str:
        t = (fil_type or "").lower()
        for k, c in FIL_COLORS.items():
            if k in t:
                return c
        return "#90A4AE"

    corps_color = fil_color(type_corps)
    corps_x_mid = corps_x

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'style="width:100%;height:{H}px;font-family:system-ui,monospace;">'
        f'<rect width="{W}" height="{H}" fill="#f8f9fb" rx="8"/>'
    ]

    # ── Corps de ligne (ligne verticale centrale) ────────────────────
    corps_top    = top_pad
    corps_bottom = top_pad + nb_emp * empile_h

    # Trait du corps
    lines.append(
        f'<line x1="{corps_x_mid}" y1="{corps_top}" '
        f'x2="{corps_x_mid}" y2="{corps_bottom}" '
        f'stroke="{corps_color}" stroke-width="{4 if not compact else 2.5}" '
        f'stroke-linecap="round"/>'
    )

    # Label corps en haut
    if not compact:
        corps_lbl = f"{type_corps}{' ' + diam_corps if diam_corps else ''}"
        lines.append(
            f'<text x="{corps_x_mid}" y="{corps_top - 8}" text-anchor="middle" '
            f'font-size="{font_main}" fill="#1565C0" font-weight="700">'
            f'Corps : {corps_lbl}</text>'
        )
        if longueur_tot:
            lines.append(
                f'<text x="{corps_x_mid}" y="{corps_top - 8 + 14}" text-anchor="middle" '
                f'font-size="{font_sub}" fill="#546E7A">Longueur totale : {longueur_tot}</text>'
            )
    else:
        lines.append(
            f'<text x="{corps_x_mid + 4}" y="{corps_top + 10}" '
            f'font-size="{font_sub}" fill="#546E7A">{type_corps[:8]}</text>'
        )

    # ── Plomb en bas ─────────────────────────────────────────────────
    plomb_y = corps_bottom
    plomb_w = 28 if not compact else 18
    plomb_h = 18 if not compact else 12
    lines.append(
        f'<rect x="{corps_x_mid - plomb_w//2}" y="{plomb_y}" '
        f'width="{plomb_w}" height="{plomb_h}" rx="4" '
        f'fill="#455A64" stroke="#263238" stroke-width="1"/>'
        f'<text x="{corps_x_mid}" y="{plomb_y + plomb_h//2 + 4}" '
        f'text-anchor="middle" font-size="{font_sub}" fill="#fff" font-weight="700">'
        f'{plomb[:10] if not compact else plomb[:6]}</text>'
    )

    # ── Emerillon en haut (connexion bas de ligne) ────────────────────
    em_y = corps_top
    em_r = 5 if not compact else 3
    lines.append(
        f'<circle cx="{corps_x_mid}" cy="{em_y}" r="{em_r}" '
        f'fill="#78909C" stroke="#546E7A" stroke-width="1"/>'
    )
    if not compact:
        lines.append(
            f'<text x="{corps_x_mid - em_r - 4}" y="{em_y + 4}" '
            f'text-anchor="end" font-size="{font_sub}" fill="#546E7A">Émerillon</text>'
        )

    # ── Empiles ──────────────────────────────────────────────────────
    for i, emp in enumerate(empiles):
        y_center = corps_top + i * empile_h + empile_h // 2

        typ_fil  = emp.get("type_fil", "Nylon")
        diam_emp = emp.get("diametre", "")
        longueur = emp.get("longueur", "")
        marque_h = emp.get("marque_h", "")
        modele_h = emp.get("modele_h", "")
        taille_h = emp.get("taille_h", "")
        perles   = emp.get("perles", "")
        commentaire = emp.get("commentaire", "")
        idx      = emp.get("index", i + 1)

        arm_color = fil_color(typ_fil)
        arm_x_end = corps_x_mid + arm_len
        noeud_r   = 4 if not compact else 3

        # Nœud sur le corps
        lines.append(
            f'<circle cx="{corps_x_mid}" cy="{y_center}" r="{noeud_r}" '
            f'fill="{arm_color}" stroke="#fff" stroke-width="1"/>'
        )

        # Fil de l'empile (bras horizontal)
        lines.append(
            f'<line x1="{corps_x_mid}" y1="{y_center}" '
            f'x2="{arm_x_end}" y2="{y_center}" '
            f'stroke="{arm_color}" stroke-width="{3 if not compact else 2}" '
            f'stroke-linecap="round"/>'
        )

        # Hameçon au bout (forme simplifiée)
        hk_x = arm_x_end + (4 if not compact else 3)
        hk_h = 16 if not compact else 10
        hk_w = 8  if not compact else 5
        lines.append(
            f'<path d="M{hk_x},{y_center} '
            f'q{hk_w},{0} {hk_w},{hk_h//2} '
            f'q{0},{hk_h//2} {-hk_w},{hk_h//2}" '
            f'fill="none" stroke="#37474F" stroke-width="{2 if not compact else 1.5}" '
            f'stroke-linecap="round"/>'
            f'<line x1="{hk_x}" y1="{y_center}" '
            f'x2="{hk_x + hk_w//3}" y2="{y_center - (6 if not compact else 4)}" '
            f'stroke="#37474F" stroke-width="{1.5 if not compact else 1}"/>'
        )

        # Perles (petits cercles colorés)
        if perles and not compact:
            nb_perles = min(perles.lower().count("perle") + perles.count("×") + 1, 5)
            p_col = "#EF5350" if "rouge" in perles.lower() else \
                    "#FFA726" if "orange" in perles.lower() else \
                    "#AB47BC" if "violet" in perles.lower() else \
                    "#42A5F5" if "bleu" in perles.lower() else "#FFCA28"
            p_spacing = 12
            p_start   = corps_x_mid + 20
            for pi in range(nb_perles):
                px_p = p_start + pi * p_spacing
                lines.append(
                    f'<circle cx="{px_p}" cy="{y_center - 8}" r="4" '
                    f'fill="{p_col}" stroke="#fff" stroke-width="0.5" opacity="0.9"/>'
                )

        # Labels (version complète uniquement)
        if not compact:
            lbl_x  = corps_x_mid + 8
            lbl_y  = y_center - 6
            lbl_h_y= y_center + 14

            # Numéro empile
            lines.append(
                f'<rect x="{corps_x_mid - 22}" y="{y_center - 9}" '
                f'width="18" height="18" rx="9" '
                f'fill="{arm_color}" stroke="#fff" stroke-width="1"/>'
                f'<text x="{corps_x_mid - 13}" y="{y_center + 4}" '
                f'text-anchor="middle" font-size="9" fill="#fff" font-weight="700">'
                f'{idx}</text>'
            )

            # Type + diamètre fil
            fil_lbl = f"{typ_fil}{' ' + diam_emp if diam_emp else ''}"
            lines.append(
                f'<text x="{lbl_x}" y="{lbl_y}" '
                f'font-size="{font_sub}" fill="#37474F" font-weight="600">'
                f'{fil_lbl}{" · " + longueur if longueur else ""}</text>'
            )

            # Hameçon
            hk_parts = [p for p in [marque_h, modele_h, f"#{taille_h}" if taille_h else ""] if p]
            if hk_parts:
                lines.append(
                    f'<text x="{lbl_x}" y="{lbl_h_y}" '
                    f'font-size="{font_sub}" fill="#546E7A">'
                    f'🪝 {" ".join(hk_parts)}'
                    + (f'  ·  {perles[:25]}' if perles else '') +
                    f'</text>'
                )
            if commentaire:
                lines.append(
                    f'<text x="{lbl_x}" y="{lbl_h_y + 12}" '
                    f'font-size="{font_sub - 1}" fill="#90A4AE" font-style="italic">'
                    f'{commentaire[:40]}</text>'
                )
        else:
            # Compact : numéro minimal
            lines.append(
                f'<text x="{corps_x_mid - 14}" y="{y_center + 4}" '
                f'font-size="{font_sub}" fill="{arm_color}" font-weight="700">{idx}</text>'
            )

    # ── Légende des couleurs (version complète) ──────────────────────
    if not compact:
        leg_y  = H - 18
        leg_x  = corps_x_mid + 10
        legend_items = [
            (type_corps or "Corps", corps_color),
        ]
        for emp in empiles:
            t = emp.get("type_fil", "")
            c = fil_color(t)
            label = t
            if label and (label, c) not in legend_items:
                legend_items.append((label, c))

        for j, (lbl, clr) in enumerate(legend_items[:5]):
            lx = leg_x + j * 100
            lines.append(
                f'<rect x="{lx}" y="{leg_y - 6}" width="12" height="6" rx="2" fill="{clr}"/>'
                f'<text x="{lx + 16}" y="{leg_y}" font-size="9" fill="#546E7A">{lbl}</text>'
            )

    lines.append('</svg>')
    return "".join(lines)


def _render_list() -> None:
    df = load_materiel("montage")
    if df.empty:
        st.info("Aucun montage enregistré. Utilise l'onglet « Créer ».")
        return

    # CSS qui colore les boutons via leur key (Streamlit ajoute classe st-key-{key})
    st.markdown("""
    <style>
    /* Boutons Éditer : VERT */
    .stApp [class*="st-key-edit_mont_"] button {
        background-color: #2E7D32 !important;
        border-color: #2E7D32 !important;
        color: white !important;
    }
    .stApp [class*="st-key-edit_mont_"] button:hover {
        background-color: #1B5E20 !important;
        border-color: #1B5E20 !important;
    }
    /* Boutons Supprimer : ROUGE */
    .stApp [class*="st-key-del_mont_"] button {
        background-color: #C62828 !important;
        border-color: #C62828 !important;
        color: white !important;
    }
    .stApp [class*="st-key-del_mont_"] button:hover {
        background-color: #B71C1C !important;
        border-color: #B71C1C !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.caption(f"{len(df)} montage(s)")

    for _, row in df.iterrows():
        item_id = int(row["id"])
        nom     = safe_str(row.get("montage_nom")) or safe_str(row.get("modele")) or "—"
        cible   = safe_str(row.get("montage_cible"))
        nb_emp  = safe_str(row.get("montage_nb_empiles"))
        plomb   = safe_str(row.get("montage_plomb"))
        photo_path = safe_str(row.get("photo_path"))

        # Décoder les empiles
        empiles = []
        try:
            empiles_json = safe_str(row.get("empiles_json"))
            if empiles_json:
                empiles = json.loads(empiles_json)
        except Exception:
            empiles = []

        with st.container(border=True):
            # Bandeau bleu marine
            extra = f"  🎯 {cible}" if cible else ""
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
                f'color:#fff;padding:10px 14px;border-radius:8px;margin-bottom:12px;">'
                f'<span style="font-size:16px;font-weight:700;">🧵 {nom}</span>'
                f'<span style="float:right;font-size:11px;opacity:.85;">'
                f'{nb_emp} empile(s){extra}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            col_photo, col_info, col_act = st.columns([1, 3, 1])
            with col_photo:
                if photo_path and str(photo_path).startswith("http"):
                    import streamlit.components.v1 as _cv_fix
                    _cv_fix.html(
                        f'<img src="{photo_path}" style="width:100%;max-height:200px;'
                        f'object-fit:contain;border-radius:8px;">',
                        height=208, scrolling=False,
                    )
                else:
                    # Schéma SVG généré depuis les données du montage
                    schema_svg = _generate_montage_svg(row, empiles, compact=True)
                    import streamlit.components.v1 as _comp
                    _comp.html(schema_svg, height=320, scrolling=False)
            with col_info:
                # Infos avec police plus grande
                lines = []
                for lbl, k, ico in [
                    ("Longueur totale", "montage_longueur_totale", "📏"),
                    ("Corps de ligne",  "montage_type_corps",       "🧵"),
                    ("Diamètre corps",  "montage_diametre_corps",   "🔍"),
                    ("Plomb conseillé", "montage_plomb",            "⚓"),
                    ("Poisson cible",   "montage_cible",            "🎯"),
                ]:
                    v = safe_str(row.get(k))
                    if v:
                        lines.append(
                            f'<div style="font-size:14px;margin:2px 0;">'
                            f'{ico} <strong>{lbl}</strong> : '
                            f'<span style="color:#1565C0;font-weight:600;">{v}</span>'
                            f'</div>'
                        )
                if lines:
                    st.markdown("".join(lines), unsafe_allow_html=True)

                acc = safe_str(row.get("montage_accessoires"))
                if acc:
                    st.markdown(
                        f'<div style="margin-top:8px;background:#fffbea;'
                        f'border-left:3px solid #f0c84a;padding:8px 12px;'
                        f'border-radius:0 6px 6px 0;font-size:13px;color:#5d4f1a;">'
                        f'📝 <em>{acc}</em></div>',
                        unsafe_allow_html=True,
                    )

            with col_act:
                # Boutons colorés via Streamlit button type
                edit_open = st.session_state.get(f"mon_edit_{item_id}", False)
                btn_edit_label = "✕ Fermer" if edit_open else "✏️ Éditer"
                if st.button(btn_edit_label, key=f"edit_mont_{item_id}",
                              use_container_width=True):
                    st.session_state[f"mon_edit_{item_id}"] = not edit_open
                    st.rerun()

                share_key = f"share_mont_{item_id}"
                if st.button("📤 Partager", key=f"share_mont_{item_id}",
                              use_container_width=True):
                    st.session_state[share_key] = not st.session_state.get(share_key, False)
                    st.rerun()

                if st.button("🗑️ Supprimer", key=f"del_mont_{item_id}",
                              use_container_width=True, type="secondary"):
                    st.session_state[f"mon_confirm_{item_id}"] = True

            if st.session_state.get(share_key):
                from ui.components import share_button
                nom_mont = safe_str(row.get("modele")) or safe_str(row.get("marque")) or "Mon montage"
                txt = (f"🎣 La Péchouille — Mon montage\n\n"
                       f"🧵 {nom_mont}\n"
                       + (f"📐 {len(empiles)} empile(s)\n" if empiles else "")
                       + "\nApp : https://lapechouille.fr")
                share_button(txt, share_key)

            # Formulaire d'édition (si déplié)
            if st.session_state.get(f"mon_edit_{item_id}"):
                _render_edit_montage(item_id, row, empiles)

            # Schéma complet en expander
            if empiles:
                with st.expander(f"📐 Schéma complet du montage ({len(empiles)} empile(s))", expanded=False):
                    import streamlit.components.v1 as _comp
                    schema_full = _generate_montage_svg(row, empiles, compact=False)
                    nb_emp_full = len(empiles)
                    h_full = max(300, 120 + nb_emp_full * 110)
                    _comp.html(schema_full, height=h_full, scrolling=False)

            # Confirmation suppression
            if st.session_state.get(f"mon_confirm_{item_id}"):
                if confirm_destructive(f"mon_{item_id}",
                                       f"Supprimer le montage « {nom} » ?"):
                    delete_row("materiel", item_id)
                    st.session_state.pop(f"mon_confirm_{item_id}", None)
                    st.cache_data.clear()
                    st.success("Montage supprimé.")
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Édition d'un montage existant
# ─────────────────────────────────────────────────────────────────────────────

def _render_edit_montage(item_id: int, row, empiles_existantes: list) -> None:
    with st.container(border=True):
        col_title, col_close = st.columns([4, 1])
        col_title.markdown("**✏️ Modifier ce montage**")
        if col_close.button("✕ Fermer", key=f"mon_close_edit_{item_id}",
                             use_container_width=True):
            st.session_state[f"mon_edit_{item_id}"] = False
            st.rerun()

        # Infos générales HORS form pour permettre le rerun sur nb_empiles
        nom = st.text_input("Nom du montage *",
                              value=safe_str(row.get("montage_nom")) or safe_str(row.get("modele")),
                              key=f"em_nom_{item_id}")
        c1, c2, c3 = st.columns(3)
        with c1:
            lt_idx = LONGUEURS_CM.index(row.get("montage_longueur_totale")) \
                     if row.get("montage_longueur_totale") in LONGUEURS_CM else 0
            longueur_tot = st.selectbox("Longueur totale", LONGUEURS_CM, index=lt_idx,
                                          key=f"em_longtot_{item_id}")
            tc_idx = FILS_BOBINE.index(row.get("montage_type_corps")) \
                     if row.get("montage_type_corps") in FILS_BOBINE else 0
            type_corps   = st.selectbox("Fil corps de ligne", FILS_BOBINE, index=tc_idx,
                                          key=f"em_corps_type_{item_id}")
        with c2:
            dc_idx = TAILLES_LIGNE.index(row.get("montage_diametre_corps")) \
                     if row.get("montage_diametre_corps") in TAILLES_LIGNE else 0
            diametre_corps = st.selectbox("Diamètre corps", TAILLES_LIGNE, index=dc_idx,
                                            key=f"em_corps_diam_{item_id}")
            plomb          = st.text_input("Plomb conseillé",
                                              value=safe_str(row.get("montage_plomb")),
                                              key=f"em_plomb_{item_id}")
        with c3:
            ci_idx = ESPECES.index(row.get("montage_cible")) \
                     if row.get("montage_cible") in ESPECES else 0
            cible = st.selectbox("Poisson cible", ESPECES, index=ci_idx,
                                   key=f"em_cible_{item_id}")
            nb_default = len(empiles_existantes) or int(row.get("montage_nb_empiles") or 2)
            nb_empiles = st.number_input("Nombre d'empiles",
                                            min_value=1, max_value=6,
                                            value=nb_default, step=1,
                                            key=f"em_nb_emp_{item_id}")

        # Pour chaque empile : pré-remplir depuis empiles_existantes
        st.markdown(f"**🪝 Empiles ({int(nb_empiles)})**")
        for i in range(int(nb_empiles)):
            prefix = f"em{item_id}_emp{i}"
            existante = empiles_existantes[i] if i < len(empiles_existantes) else {}
            with st.container(border=True):
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,#37474F,#263238);'
                    f'color:#fff;padding:6px 12px;border-radius:6px;margin-bottom:8px;">'
                    f'<strong>🪝 Empile {i + 1}</strong></div>',
                    unsafe_allow_html=True,
                )
                ec1, ec2 = st.columns(2)
                with ec1:
                    fl_idx = FILS_EMPILE.index(existante.get("type_fil")) \
                             if existante.get("type_fil") in FILS_EMPILE else 0
                    st.selectbox("Type de fil", FILS_EMPILE, index=fl_idx,
                                  key=f"{prefix}_type_fil")
                    dm_idx = TAILLES_LIGNE.index(existante.get("diametre")) \
                             if existante.get("diametre") in TAILLES_LIGNE else 0
                    st.selectbox("Diamètre du fil", TAILLES_LIGNE, index=dm_idx,
                                  key=f"{prefix}_diam")
                    lg_idx = LONGUEURS_EMPILE.index(existante.get("longueur")) \
                             if existante.get("longueur") in LONGUEURS_EMPILE else 0
                    st.selectbox("Longueur d'empile", LONGUEURS_EMPILE, index=lg_idx,
                                  key=f"{prefix}_longueur")
                with ec2:
                    mh_idx = MARQUES_HAMECONS.index(existante.get("marque_h")) \
                             if existante.get("marque_h") in MARQUES_HAMECONS else 0
                    st.selectbox("Marque hameçon", MARQUES_HAMECONS, index=mh_idx,
                                  key=f"{prefix}_marque_h")
                    mo_idx = MODELES_HAMECONS.index(existante.get("modele_h")) \
                             if existante.get("modele_h") in MODELES_HAMECONS else 0
                    st.selectbox("Modèle hameçon", MODELES_HAMECONS, index=mo_idx,
                                  key=f"{prefix}_modele_h")
                    ta_idx = TAILLES_HAMECONS.index(existante.get("taille_h")) \
                             if existante.get("taille_h") in TAILLES_HAMECONS else 0
                    st.selectbox("Taille hameçon", TAILLES_HAMECONS, index=ta_idx,
                                  key=f"{prefix}_taille_h")
                ec3, ec4 = st.columns(2)
                with ec3:
                    st.text_input("Perles / attractants",
                                    value=existante.get("perles", ""),
                                    key=f"{prefix}_perles")
                with ec4:
                    st.text_input("Commentaire empile",
                                    value=existante.get("commentaire", ""),
                                    key=f"{prefix}_com")

        accessoires = st.text_area("Accessoires globaux",
                                     value=safe_str(row.get("montage_accessoires")),
                                     key=f"em_acc_{item_id}")

        # Bouton de sauvegarde
        if st.button("💾 Sauvegarder les modifications",
                      key=f"em_save_{item_id}",
                      type="primary", use_container_width=True):
            if not nom.strip():
                st.error("Le nom du montage est obligatoire.")
                return
            empiles = []
            for i in range(int(nb_empiles)):
                prefix = f"em{item_id}_emp{i}"
                empiles.append({
                    "index":       i + 1,
                    "type_fil":    st.session_state.get(f"{prefix}_type_fil", ""),
                    "diametre":    st.session_state.get(f"{prefix}_diam", ""),
                    "longueur":    st.session_state.get(f"{prefix}_longueur", ""),
                    "marque_h":    st.session_state.get(f"{prefix}_marque_h", ""),
                    "modele_h":    st.session_state.get(f"{prefix}_modele_h", ""),
                    "taille_h":    st.session_state.get(f"{prefix}_taille_h", ""),
                    "perles":      st.session_state.get(f"{prefix}_perles", ""),
                    "commentaire": st.session_state.get(f"{prefix}_com", ""),
                })
            update_row("materiel", item_id, {
                "montage_nom":             nom.strip(),
                "modele":                  nom.strip(),
                "montage_longueur_totale": longueur_tot,
                "montage_type_corps":      type_corps,
                "montage_diametre_corps":  diametre_corps,
                "montage_nb_empiles":      int(nb_empiles),
                "montage_plomb":           plomb,
                "montage_cible":           cible,
                "montage_accessoires":     accessoires,
                "empiles_json":            json.dumps(empiles, ensure_ascii=False),
            })
            st.cache_data.clear()
            st.session_state[f"mon_edit_{item_id}"] = False
            st.success("✅ Montage mis à jour.")
            st.rerun()
