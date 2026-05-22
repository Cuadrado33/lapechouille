"""
Page « Mon profil pêcheur » — style carte de pêcheur / réseaux sociaux.
"""
from __future__ import annotations
from datetime import datetime, date
from pathlib import Path
import base64
import json

import streamlit as st
import streamlit.components.v1 as components

from core.database import load_profil, save_profil, load_sessions, load_captures
from core.utils import safe_str, safe_float
from ui.components import hero, section
from core.storage import save_materiel_photo

NIVEAUX = ["Débutant", "Intermédiaire", "Confirmé", "Expert", "Compétiteur"]
ZONES   = ["Atlantique Sud-Ouest", "Atlantique Centre-Ouest", "Bretagne",
           "Manche / Normandie", "Manche Est", "Méditerranée", "Plusieurs zones"]
ESPECES = ["Bar / Loup", "Daurade royale", "Maigre", "Sole", "Raie",
           "Lieu jaune", "Tacaud", "Maquereau", "Congre", "Autre"]

SOCIAL_NETWORKS = [
    {
        "key": "social_instagram",
        "label": "Instagram",
        "placeholder": "https://instagram.com/monpseudo",
        "color": "#E1306C",
        "bg": "linear-gradient(135deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888)",
        "logo": """<svg viewBox="0 0 24 24" width="22" height="22" fill="#fff">
          <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
        </svg>""",
    },
    {
        "key": "social_facebook",
        "label": "Facebook",
        "placeholder": "https://facebook.com/monprofil",
        "color": "#1877F2",
        "bg": "#1877F2",
        "logo": """<svg viewBox="0 0 24 24" width="22" height="22" fill="#fff">
          <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
        </svg>""",
    },
    {
        "key": "social_youtube",
        "label": "YouTube",
        "placeholder": "https://youtube.com/@machaîne",
        "color": "#FF0000",
        "bg": "#FF0000",
        "logo": """<svg viewBox="0 0 24 24" width="22" height="22" fill="#fff">
          <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
        </svg>""",
    },
    {
        "key": "social_tiktok",
        "label": "TikTok",
        "placeholder": "https://tiktok.com/@monpseudo",
        "color": "#000000",
        "bg": "#010101",
        "logo": """<svg viewBox="0 0 24 24" width="22" height="22" fill="#fff">
          <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z"/>
        </svg>""",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    # Vérifier que l'utilisateur est connecté
    if not st.session_state.get("reseau_user"):
        st.markdown(
            '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
            'color:#fff;padding:14px 20px;border-radius:8px;margin-bottom:20px;">'
            '<span style="font-size:18px;font-weight:800;">👤 Mon profil</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.warning("⚠️ Tu dois être connecté pour accéder à ton profil.")
        st.info("👉 Va dans **Fil d'actualité** pour créer ton compte ou te connecter.")
        if st.button("🌊 Aller au Réseau", type="primary"):
            st.session_state["nav_page"] = "reseau"
            st.rerun()
        return

    profil      = load_profil() or {}
    sessions_df = load_sessions()
    captures_df = load_captures()

    nb_sessions = len(sessions_df)
    nb_captures = len(captures_df)
    espece_top  = "—"
    taille_max  = 0.0
    saison      = str(date.today().year)

    if not captures_df.empty:
        if "espece" in captures_df.columns:
            top = captures_df["espece"].value_counts()
            espece_top = top.index[0] if not top.empty else "—"
        if "taille_cm" in captures_df.columns:
            taille_max = safe_float(captures_df["taille_cm"].max())

    # Sessions de la saison
    nb_saison = 0
    if not sessions_df.empty and "date_session" in sessions_df.columns:
        nb_saison = int(sessions_df["date_session"].str.startswith(saison).sum())

    photo_path = safe_str(profil.get("photo_path"))
    if photo_path and not Path(photo_path).exists():
        photo_path = None

    # ── Carte de profil style réseau social ──────────────────────────
    _render_profile_card(profil, photo_path,
                         nb_sessions, nb_captures, nb_saison, espece_top, taille_max, saison)

    # Avatar IA (toggle)
    if st.session_state.get("pf_avatar_open"):
        with st.container(border=True):
            st.markdown("### 🎨 Avatar IA")
            _render_manga(photo_path)
            if st.button("✕ Fermer le générateur", key="pf_close_avatar"):
                st.session_state["pf_avatar_open"] = False
                st.rerun()

    st.divider()

    # ── Formulaire d'édition (une seule fois) ────────────────────────
    section("Modifier mon profil", icon="✏️")
    _render_form(profil, photo_path)


# ─────────────────────────────────────────────────────────────────────────────
# Carte de profil style réseau social
# ─────────────────────────────────────────────────────────────────────────────

def _render_profile_card(profil, photo_path, nb_sessions, nb_captures,
                          nb_saison, espece_top, taille_max, saison):

    pseudo = (safe_str(profil.get("pseudo")) or
              f"{safe_str(profil.get('prenom'))} {safe_str(profil.get('nom'))}".strip() or
              "Mon profil")
    niveau  = safe_str(profil.get("niveau")) or ""
    zone    = safe_str(profil.get("zone_peche_principale")) or ""
    annees  = int(safe_float(profil.get("annees_peche")) or 0)
    espece  = safe_str(profil.get("espece_preferee")) or "—"
    canne   = safe_str(profil.get("canne_preferee")) or "—"
    bio     = safe_str(profil.get("bio")) or ""

    # ── Photo + bouton avatar ────────────────────────────────────────
    col_photo, col_main = st.columns([1, 3])
    with col_photo:
        if photo_path and Path(photo_path).exists():
            st.image(photo_path, use_container_width=True)
        else:
            st.markdown(
                '<div style="aspect-ratio:1;background:#e8edf2;border-radius:12px;'
                'display:flex;align-items:center;justify-content:center;font-size:52px;">🎣</div>',
                unsafe_allow_html=True,
            )
        if st.button("🎨 Avatar IA", key="pf_open_avatar", use_container_width=True, type="primary"):
            st.session_state["pf_avatar_open"] = not st.session_state.get("pf_avatar_open", False)
            st.rerun()

    # ── Identité + stats ─────────────────────────────────────────────
    with col_main:
        st.markdown(f"## {pseudo}")
        tags = []
        if niveau: tags.append(f"**{niveau}**")
        if zone:   tags.append(zone)
        if annees: tags.append(f"{annees} ans de pêche")
        if tags:
            st.markdown(" · ".join(tags))
        if espece != "—":
            st.markdown(f"🎣 Espèce préférée : **{espece}**")
        if canne != "—":
            st.caption(f"🎯 {canne}")
        if bio:
            st.markdown(f"> _{bio}_")

        # ── Réseaux sociaux avec vrais logos ──────────────────────────
        _render_social_badges(profil)

    # ── Stats encadrées bien visibles ───────────────────────────────
    st.markdown("")
    c1, c2, c3, c4 = st.columns(4)
    stats = [
        (c1, "🎣", "SESSIONS", str(nb_sessions), "#0D47A1", "#E3F2FD"),
        (c2, "🐟", "CAPTURES",  str(nb_captures),  "#1B5E20", "#E8F5E9"),
        (c3, "🏆", "SAISON " + saison, str(nb_saison) + " sorties", "#E65100", "#FFF3E0"),
        (c4, "📏", "RECORD", f"{taille_max:.0f} cm" if taille_max else "—", "#4A148C", "#F3E5F5"),
    ]
    for col, icon, lbl, val, fc, bg in stats:
        with col:
            st.markdown(
                f'<div style="background:{bg};border:2px solid {fc}22;border-radius:14px;'
                f'padding:14px 8px;text-align:center;">'
                f'<div style="font-size:26px;margin-bottom:4px;">{icon}</div>'
                f'<div style="font-size:10px;font-weight:800;letter-spacing:1.5px;color:{fc};'
                f'text-transform:uppercase;margin-bottom:6px;">{lbl}</div>'
                f'<div style="font-size:26px;font-weight:900;color:{fc};line-height:1;">{val}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _render_social_badges(profil: dict) -> None:
    """Logos réseaux sociaux + boutons Copier et Partager sous chaque badge."""
    links = []
    for sn in SOCIAL_NETWORKS:
        url = safe_str(profil.get(sn["key"]))
        if url:
            links.append((url, sn))

    if not links:
        return

    cards_html = ""
    for url, sn in links:
        url_safe = url.replace('"', '&quot;').replace("'", "\\'")
        label_js = sn["label"].replace("'", "\\'")
        card_id  = f"sn_{sn['key']}"
        ok_id    = f"ok_{sn['key']}"

        cards_html += f"""
        <div style="display:inline-flex;flex-direction:column;align-items:stretch;
                    margin:6px 10px 6px 0;vertical-align:top;min-width:160px;max-width:200px;">
          <a href="{url.replace(chr(34), '%22')}" target="_blank" rel="noopener"
             style="display:flex;align-items:center;gap:10px;
                    background:{sn['bg']};color:#fff;border-radius:12px 12px 0 0;
                    padding:13px 18px;font-size:15px;font-weight:700;
                    text-decoration:none;line-height:1;transition:opacity .15s;"
             onmouseover="this.style.opacity='.85'" onmouseout="this.style.opacity='1'">
            <span style="display:flex;align-items:center;flex-shrink:0;width:26px;height:26px;">
              {sn['logo'].replace('width="22"','width="26"').replace('height="22"','height="26"')}
            </span>
            <span>{sn['label']}</span>
          </a>
          <div style="display:flex;border-radius:0 0 10px 10px;overflow:hidden;
                      border:2px solid {sn['color']};border-top:none;">
            <button onclick="snCopy_{card_id}()"
               style="flex:1;background:#fff;color:{sn['color']};border:none;
                      padding:8px 6px;font-size:12px;font-weight:700;cursor:pointer;
                      border-right:1px solid {sn['color']}22;transition:background .15s;"
               onmouseover="this.style.background='#f5f5f5'"
               onmouseout="this.style.background='#fff'">
              📋 Copier <span id="{ok_id}" style="display:none;color:#2e7d32;">✓</span>
            </button>
            <button onclick="snShare_{card_id}()"
               style="flex:1;background:#fff;color:{sn['color']};border:none;
                      padding:8px 6px;font-size:12px;font-weight:700;cursor:pointer;
                      transition:background .15s;"
               onmouseover="this.style.background='#f5f5f5'"
               onmouseout="this.style.background='#fff'">
              💬 Partager
            </button>
          </div>
        </div>
        <script>
        function snCopy_{card_id}() {{
          var txt = '{url_safe}';
          if (navigator.clipboard) {{
            navigator.clipboard.writeText(txt).then(function() {{
              var el = document.getElementById('{ok_id}');
              if (el) {{ el.style.display='inline'; setTimeout(()=>el.style.display='none',2000); }}
            }});
          }}
        }}
        function snShare_{card_id}() {{
          var txt = 'Mon profil {label_js} : {url_safe}';
          if (navigator.share) {{
            navigator.share({{ title: '{label_js}', text: txt, url: '{url_safe}' }});
          }} else {{
            window.open('https://wa.me/?text=' + encodeURIComponent(txt), '_blank');
          }}
        }}
        </script>"""

    nb = len(links)
    # Hauteur généreuse : bouton principal 52px + boutons bas 38px + marges
    h = 110 if nb <= 4 else 230
    components.html(
        f'<div style="padding:6px 0;font-family:system-ui,sans-serif;">{cards_html}</div>',
        height=h,
        scrolling=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Formulaire d'édition
# ─────────────────────────────────────────────────────────────────────────────

def _render_form(profil, photo_path):
    # Photo HORS formulaire (file_uploader incompatible avec st.form)
    with st.container(border=True):
        st.markdown("**📸 Photo de profil**")
        col_cam, col_up = st.columns(2)
        with col_cam:
            cam = st.camera_input("Prendre une photo", key="pf_cam_widget")
        with col_up:
            upl = st.file_uploader("Importer", type=["jpg","jpeg","png","webp"],
                                   key="pf_photo_upload_widget")
        new_photo = upl if upl is not None else cam

    with st.form("profil_form"):
        # Identité
        with st.container(border=True):
            st.markdown("**👤 Identité**")
            c1, c2, c3 = st.columns(3)
            prenom = c1.text_input("Prénom",  value=safe_str(profil.get("prenom")), key="pf_prenom")
            nom    = c2.text_input("Nom",     value=safe_str(profil.get("nom")),    key="pf_nom")
            pseudo = c3.text_input("Pseudo",  value=safe_str(profil.get("pseudo")), key="pf_pseudo")

        # Niveau & pratique
        with st.container(border=True):
            st.markdown("**🎣 Pratique**")
            c1, c2, c3 = st.columns(3)
            niv_i  = NIVEAUX.index(profil["niveau"]) if profil.get("niveau") in NIVEAUX else 0
            niveau = c1.selectbox("Niveau", NIVEAUX, index=niv_i, key="pf_niveau")
            annees = c2.number_input("Années de pêche", 0, 70,
                                     value=int(safe_float(profil.get("annees_peche")) or 0),
                                     key="pf_annees")
            zone_i = ZONES.index(profil["zone_peche_principale"]) \
                     if profil.get("zone_peche_principale") in ZONES else 0
            zone   = c3.selectbox("Zone principale", ZONES, index=zone_i, key="pf_zone")

            c1, c2, c3 = st.columns(3)
            esp_i     = ESPECES.index(profil["espece_preferee"]) \
                        if profil.get("espece_preferee") in ESPECES else 0
            esp_pref   = c1.selectbox("Espèce préférée", ESPECES, index=esp_i, key="pf_esp")
            canne_pref = c2.text_input("Canne de cœur",
                                        value=safe_str(profil.get("canne_preferee")),
                                        placeholder="Daiwa Tournament S…", key="pf_canne")
            appat_pref = c3.text_input("Appât favori",
                                        value=safe_str(profil.get("appat_prefere")),
                                        placeholder="Arénicole…", key="pf_appat")

        # Bio
        with st.container(border=True):
            st.markdown("**📝 Bio**")
            bio = st.text_area("", value=safe_str(profil.get("bio")),
                                placeholder="Raconte-toi : spots, passion, meilleures sorties…",
                                key="pf_bio", height=90, label_visibility="collapsed")

        # Réseaux sociaux
        with st.container(border=True):
            st.markdown("**🌐 Réseaux sociaux**")
            c1, c2 = st.columns(2)
            social_vals = {}
            for i, sn in enumerate(SOCIAL_NETWORKS):
                col = c1 if i % 2 == 0 else c2
                social_vals[sn["key"]] = col.text_input(
                    f"{sn['label']}",
                    value=safe_str(profil.get(sn["key"])),
                    placeholder=sn["placeholder"],
                    key=f"pf_{sn['key']}",
                )

        # Observations
        with st.container(border=True):
            st.markdown("**📋 Observations & notes personnelles**")
            observations = st.text_area(
                "", value=safe_str(profil.get("observations")),
                placeholder="Astuces, mémos, conditions idéales par espèce…",
                key="pf_observations", height=110, label_visibility="collapsed",
            )

        if st.form_submit_button("💾 Sauvegarder le profil",
                                  use_container_width=True, type="primary"):
            data = {
                "prenom": prenom, "nom": nom, "pseudo": pseudo,
                "niveau": niveau, "annees_peche": annees,
                "zone_peche_principale": zone, "espece_preferee": esp_pref,
                "canne_preferee": canne_pref, "appat_prefere": appat_pref,
                "bio": bio, "observations": observations,
                **social_vals,
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
            if new_photo:
                pp = save_materiel_photo(new_photo, 0, "profil")
                if pp:
                    data["photo_path"] = pp
            elif photo_path:
                data["photo_path"] = photo_path
            if not profil:
                data["created_at"] = datetime.now().isoformat(timespec="seconds")
            save_profil(data)
            st.success("✅ Profil sauvegardé !")
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Générateur avatar manga / Ghibli / pêcheur IA
# ─────────────────────────────────────────────────────────────────────────────

def _render_manga(photo_path: str | None) -> None:
    has_photo = bool(photo_path and Path(photo_path).exists())

    STYLES = {
        "Pêcheur héroïque 🎣":                   "heroic fisherman manga style, surfcasting rod, dramatic ocean, epic realistic pose",
        "Studio Ghibli 🌊":                       "Studio Ghibli Miyazaki animation style, painterly, sea and nature, warm cinematic light",
        "Shōnen (Naruto, One Piece)":            "classic shonen manga style, bold outlines, dynamic determined pose",
        "Seinen réaliste (Berserk, Vagabond)":   "seinen manga style, realistic detailed, rugged face, dramatic lighting",
        "Anime moderne (Demon Slayer)":          "modern anime style, Demon Slayer quality, vibrant cinematic colors",
        "Chibi pêcheur 🐟":                      "chibi super deformed manga, cute big head, tiny fisherman with rod",
    }
    BG = {
        "Plage coucher de soleil 🌅": "sunset beach, golden hour light",
        "Océan et vagues 🌊":         "dramatic ocean waves, sea spray",
        "Port de pêche 🚢":           "rustic fishing harbor, boats, dawn",
        "Fond neutre":                "clean neutral background",
        "Ciel étoilé 🌙":            "starry night sky, moonlight reflection on water",
    }

    if has_photo:
        c_img, c_info = st.columns([1, 3])
        c_img.image(photo_path, use_container_width=True)
        c_info.success("✅ Ta photo sera analysée par Claude Vision pour personnaliser l'avatar.")
        use_existing = c_info.checkbox("Utiliser ma photo", value=True, key="mg_use")
    else:
        st.info("Ajoute une photo de profil pour un avatar personnalisé à ton image.")
        use_existing = False

    upload = None
    if not use_existing:
        upload = st.file_uploader("Ou charger une photo", type=["jpg","jpeg","png","webp"],
                                   key="mg_upload")

    c1, c2, c3 = st.columns(3)
    style = c1.selectbox("Style", list(STYLES.keys()), key="mg_style")
    bg    = c2.selectbox("Fond",  list(BG.keys()),     key="mg_bg")
    extra = c3.text_input("Détails", placeholder="lunettes, barbe, chapeau…", key="mg_extra")

    generate = st.button("✨ Générer l'avatar", key="mg_gen", type="primary",
                          use_container_width=True)

    if generate:
        source = (Path(photo_path) if use_existing and has_photo else upload)
        face_desc = ""
        if source:
            with st.spinner("Analyse par Claude Vision…"):
                face_desc = _analyze_face(source)
            if face_desc:
                st.caption(f"👁 Visage détecté : _{face_desc}_")
        subject = face_desc or "a rugged fisherman with a weathered determined look"
        prompt = ", ".join(filter(None,[
            f"manga portrait of {subject}", STYLES[style], BG[bg], extra,
            "high quality illustration, professional anime art",
        ]))
        with st.spinner("Génération… (15-30 s)"):
            _, img = _pollinations(prompt)
        if img:
            st.session_state["mg_bytes"] = img
        else:
            st.error("Échec. Vérifie ta connexion et réessaie.")

    img = st.session_state.get("mg_bytes")
    if img:
        c_res, c_act = st.columns([2, 1])
        c_res.image(img, caption="✨ Avatar généré", use_container_width=True)
        c_act.download_button("⬇️ Télécharger", img, "avatar.png", "image/png",
                               use_container_width=True)
        if c_act.button("💾 Définir comme photo de profil", key="mg_save",
                         use_container_width=True):
            p = Path("photos_materiel") / f"profil_manga_{int(datetime.now().timestamp())}.png"
            p.parent.mkdir(exist_ok=True)
            p.write_bytes(img)
            pd_ = load_profil() or {}
            pd_["photo_path"] = str(p)
            pd_.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
            pd_["updated_at"] = datetime.now().isoformat(timespec="seconds")
            save_profil(pd_)
            st.session_state.pop("mg_bytes", None)
            st.success("Photo de profil mise à jour !")
            st.rerun()
        if c_act.button("🔄 Regénérer", key="mg_regen", use_container_width=True):
            st.session_state.pop("mg_bytes", None)
            st.rerun()


def _analyze_face(source) -> str:
    try:
        import requests as _r
        if isinstance(source, Path):
            data = source.read_bytes()
            ext  = source.suffix.lower().lstrip(".")
        else:
            data = source.read(); source.seek(0)
            ext  = getattr(source, "name", "x.jpg").rsplit(".",1)[-1].lower()
        mt = {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png",
              "webp":"image/webp"}.get(ext,"image/jpeg")
        resp = _r.post(
            "https://api.anthropic.com/v1/messages",
            json={"model":"claude-sonnet-4-20250514","max_tokens":180,"messages":[
                {"role":"user","content":[
                    {"type":"image","source":{"type":"base64","media_type":mt,
                     "data":base64.b64encode(data).decode()}},
                    {"type":"text","text":"Describe this person's appearance for a manga portrait prompt in 1-2 sentences. Focus on hair color/style, eye color, face shape, age, skin tone, expression. Start with 'a person with'."},
                ]}
            ]},
            headers={"Content-Type":"application/json"},
            timeout=25,
        )
        if resp.status_code == 200:
            return resp.json()["content"][0]["text"].strip()
    except Exception:
        pass
    return ""


def _pollinations(prompt: str) -> tuple[str, bytes | None]:
    try:
        import requests as _r
        from urllib.parse import quote
        url = (f"https://image.pollinations.ai/prompt/{quote(prompt)}"
               f"?model=flux&width=512&height=512&nologo=true&seed={abs(hash(prompt))%99999}")
        r = _r.get(url, timeout=60)
        if r.status_code == 200 and r.headers.get("content-type","").startswith("image"):
            return url, r.content
        return url, None
    except Exception:
        return "", None
