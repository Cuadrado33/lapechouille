"""
Navigation latérale.
- Analyse des conditions : sous-items avec scroll ancre
- Chaque autre bouton = une page unique
"""
from __future__ import annotations
import streamlit as st

NAV_GROUPS = [
    {
        "title": "ACCUEIL",
        "items": [
            {"key": "accueil", "label": "Tableau de bord", "icon": "🏠"},
            {"key": "profil",  "label": "Mon profil",       "icon": "👤"},
        ],
    },
    {
        "title": "🌊 RÉSEAU LA PÉCHOUILLE",
        "items": [
            {"key": "reseau",          "label": "Fil d'actualité",     "icon": "📰"},
            {"key": "reseau_amis",     "label": "Amis",                "icon": "👥"},
            {"key": "reseau_messages", "label": "Messages",            "icon": "💬"},
            {"key": "reseau_class",    "label": "Classement pêcheurs", "icon": "🏆"},
        ],
    },
    {
        "title": "ANALYSE DES CONDITIONS",
        "items": [
            {"key": "conditions", "label": "Mon spot",       "icon": "📍", "anchor": "spot"},
            {"key": "conditions", "label": "Cartographie",   "icon": "🗺️", "anchor": "carto"},
            {"key": "conditions", "label": "Marée",          "icon": "🌊", "anchor": "maree"},
            {"key": "conditions", "label": "Météo générale", "icon": "🌦️", "anchor": "meteo_gen"},
            {"key": "conditions", "label": "Soleil & Lune",  "icon": "☀️", "anchor": "astro"},
            {"key": "conditions", "label": "Réglementation", "icon": "⚖️", "anchor": "regle"},
        ],
    },
    {
        "title": "SUIVI PÊCHE",
        "items": [
            {"key": "mes_spots",      "label": "Mes spots",               "icon": "⭐"},
            {"key": "sessions",       "label": "Mes sessions",            "icon": "📓"},
            {"key": "competition",    "label": "Compétition",             "icon": "🎖️"},
            {"key": "captures",       "label": "Mes captures",            "icon": "🎣"},
            {"key": "identification", "label": "Identification poissons", "icon": "🐟"},
            {"key": "spots_appats",   "label": "Mes spots appâts",        "icon": "🪱"},
            {"key": "analyse",        "label": "Analyse performance",     "icon": "📈"},
        ],
    },
    {
        "title": "MATÉRIEL",
        "items": [
            {"key": "mat_cannes",    "label": "Cannes",                "icon": "🎯"},
            {"key": "mat_moulinets", "label": "Moulinets",             "icon": "⚙️"},
            {"key": "mat_montages",  "label": "Mes montages",          "icon": "🧵"},
            {"key": "mat_divers",    "label": "Matériel divers",       "icon": "🎒"},
            {"key": "mat_tableaux",  "label": "Références & tableaux", "icon": "📊"},
        ],
    },
    {
        "title": "DIVERS",
        "items": [
            {"key": "photos",   "label": "Photos / souvenirs",   "icon": "📸"},
            {"key": "webcams",  "label": "Webcams plages",        "icon": "🌐"},
            {"key": "services", "label": "Services à proximité", "icon": "🧭"},
            {"key": "alertes",  "label": "Alertes locales",      "icon": "🚨"},
            {"key": "export",   "label": "Export des données",   "icon": "📤"},
        ],
    },
]


def _ensure_defaults() -> None:
    st.session_state.setdefault("nav_page", "accueil")
    st.session_state.setdefault("nav_label", "Tableau de bord")
    st.session_state.setdefault("nav_anchor", None)


def get_active_page() -> str:
    _ensure_defaults()
    return st.session_state["nav_page"]


def get_active_anchor() -> str | None:
    return st.session_state.get("nav_anchor")


def set_active(page: str, label: str, anchor: str | None = None) -> None:
    st.session_state["nav_page"] = page
    st.session_state["nav_label"] = label
    st.session_state["nav_anchor"] = anchor


def render_sidebar_navigation() -> None:
    _ensure_defaults()

    user = st.session_state.get("reseau_user")

    # ── Bandeau La Péchouille ────────────────────────────────────────
    st.sidebar.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:10px 14px;border-radius:8px;margin-bottom:8px;'
        'text-align:center;">'
        '<div style="font-size:24px;">🎣</div>'
        '<div style="font-size:15px;font-weight:800;letter-spacing:1px;">La Péchouille</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Utilisateur connecté ─────────────────────────────────────────
    if user:
        if st.sidebar.button("🚪 Se déconnecter", key="nav_logout",
                              use_container_width=True):
            from core.auth import logout as auth_logout
            auth_logout()
            st.rerun()

    # ── Formulaire de connexion inline ───────────────────────────────
    else:
        login_open = st.session_state.get("sidebar_login_open", False)

        if not login_open:
            if st.sidebar.button("🔑 Se connecter", key="nav_login",
                                  use_container_width=True, type="primary"):
                st.session_state["sidebar_login_open"] = True
                st.rerun()
        else:
            # Mini-formulaire inline dans la sidebar
            st.sidebar.markdown(
                '<div style="background:#F5F7FA;border-radius:8px;'
                'padding:10px;margin-bottom:6px;">'
                '<div style="font-size:12px;font-weight:700;color:#1565C0;'
                'margin-bottom:6px;">🔑 Connexion</div></div>',
                unsafe_allow_html=True,
            )
            email = st.sidebar.text_input("Email", key="sl_email",
                                           placeholder="ton@email.com",
                                           label_visibility="collapsed")
            pwd   = st.sidebar.text_input("Mot de passe", key="sl_pwd",
                                           type="password",
                                           placeholder="Mot de passe",
                                           label_visibility="collapsed")
            c1, c2 = st.sidebar.columns(2)
            if c1.button("✅ OK", key="sl_submit", use_container_width=True,
                          type="primary"):
                if email and pwd:
                    from core.auth import login as auth_login
                    user = auth_login(email, pwd)
                    if user:
                        st.session_state.pop("sidebar_login_open", None)
                        st.rerun()
                    else:
                        st.sidebar.error("Email ou mot de passe incorrect.")
                else:
                    st.sidebar.warning("Remplis les deux champs.")
            if c2.button("✕", key="sl_cancel", use_container_width=True):
                st.session_state.pop("sidebar_login_open", None)
                st.rerun()

            st.sidebar.markdown("---")
            st.sidebar.caption("Pas encore de compte ?")
            if st.sidebar.button("📝 Créer un compte", key="sl_register",
                                  use_container_width=True):
                st.session_state.pop("sidebar_login_open", None)
                set_active("reseau", "Fil d'actualité")
                st.rerun()

    st.sidebar.divider()

    # ── Navigation ───────────────────────────────────────────────────
    active_page   = st.session_state["nav_page"]
    active_anchor = st.session_state.get("nav_anchor")

    for group in NAV_GROUPS:
        st.sidebar.markdown(f"**{group['title']}**")
        for item in group["items"]:
            anchor    = item.get("anchor")
            is_active = (active_page == item["key"] and active_anchor == anchor)
            if st.sidebar.button(
                f"{item['icon']}  {item['label']}",
                key=f"nav_{item['key']}_{item['label']}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                set_active(item["key"], item["label"], anchor)
                st.rerun()

    st.sidebar.divider()
    st.sidebar.caption(f"Vue : {st.session_state['nav_label']}")


def _render_sidebar_profile_card() -> None:
    """Miniature profil dans la sidebar : photo ronde + prénom nom + stats saison."""
    try:
        from core.database import load_profil, load_captures, load_sessions
        from core.utils import safe_str, safe_float
        from pathlib import Path
        import base64
        from datetime import date

        profil = load_profil() or {}
        if not profil:
            return  # Pas encore de profil, on n'affiche rien

        pseudo = (safe_str(profil.get("pseudo")) or
                  f"{safe_str(profil.get('prenom'))} {safe_str(profil.get('nom'))}".strip() or
                  "Pêcheur")
        niveau = safe_str(profil.get("niveau")) or ""

        # Stats de la saison courante (année en cours)
        saison = str(date.today().year)
        today  = date.today().isoformat()
        sessions_df = load_sessions()
        captures_df = load_captures()

        nb_sessions_saison = 0
        nb_captures_saison = 0
        en_session = False
        if not sessions_df.empty and "date_session" in sessions_df.columns:
            nb_sessions_saison = int(sessions_df["date_session"].str.startswith(saison).sum())
            # Session du jour = en session
            en_session = bool((sessions_df["date_session"] == today).any())
        if not captures_df.empty and "created_at" in captures_df.columns:
            nb_captures_saison = int(captures_df["created_at"].str.startswith(saison).sum())

        session_badge = ""
        if en_session:
            session_badge = (
                '<div style="background:#E65100;color:#fff;font-size:10px;font-weight:800;'
                'letter-spacing:1px;padding:3px 8px;border-radius:20px;display:inline-block;'
                'margin-top:4px;animation:pulse 1.5s infinite;">🎣 EN SESSION</div>'
                '<style>@keyframes pulse{0%,100%{opacity:1}50%{opacity:.7}}</style>'
            )
            # Alerte orage clignotante si en session ET orage prévu
            if st.session_state.get("storm_alert_2h"):
                session_badge += (
                    '<div style="background:#C62828;color:#fff;font-size:11px;font-weight:900;'
                    'letter-spacing:1px;padding:4px 10px;border-radius:6px;'
                    'display:block;margin-top:6px;text-align:center;'
                    'animation:dangerblink 0.8s infinite;border:2px solid #FFEB3B;">'
                    '⚠️ DANGER ORAGE</div>'
                    '<style>@keyframes dangerblink{0%,100%{opacity:1;'
                    'transform:scale(1)}50%{opacity:.5;transform:scale(1.05)}}</style>'
                )

        # Photo — supporte URL Supabase ET chemin local
        photo_path = safe_str(profil.get("photo_path"))
        photo_html = ""
        if photo_path:
            if photo_path.startswith("http"):
                # URL Supabase — img direct
                photo_html = (
                    f'<img src="{photo_path}" '
                    f'style="width:48px;height:48px;border-radius:50%;object-fit:cover;'
                    f'border:2px solid #1565C0;flex-shrink:0;"/>'
                )
            elif Path(photo_path).exists():
                try:
                    ext  = Path(photo_path).suffix.lower().lstrip(".")
                    mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
                    b64  = base64.b64encode(Path(photo_path).read_bytes()).decode()
                    photo_html = (
                        f'<img src="data:{mime};base64,{b64}" '
                        f'style="width:48px;height:48px;border-radius:50%;object-fit:cover;'
                        f'border:2px solid #1565C0;flex-shrink:0;"/>'
                    )
                except Exception:
                    pass

        if not photo_html:
            photo_html = ('<div style="width:48px;height:48px;border-radius:50%;'
                          'background:#1565C0;display:flex;align-items:center;'
                          'justify-content:center;font-size:22px;flex-shrink:0;">🎣</div>')

        import streamlit.components.v1 as _c
        _c.html(f"""
<style>
.spf-card {{
  display:flex;align-items:center;gap:10px;
  background:#f0f4f8;border-radius:10px;padding:8px 10px;
  margin:0 0 8px;font-family:system-ui,sans-serif;
}}
.spf-info {{ flex:1;min-width:0; }}
.spf-name {{ font-weight:800;font-size:13px;color:#1a2332;
             white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }}
.spf-level {{ font-size:10px;color:#888;font-weight:600;text-transform:uppercase;
              letter-spacing:.6px;margin-bottom:2px; }}
.spf-stats {{ display:flex;gap:8px;margin-top:3px; }}
.spf-stat {{ font-size:10px;color:#555; }}
.spf-stat b {{ color:#1565C0; }}
</style>
<div class="spf-card">
  {photo_html}
  <div class="spf-info">
    <div class="spf-level">{niveau}</div>
    <div class="spf-name">{pseudo}</div>
    <div class="spf-stats">
      <span class="spf-stat">🎣 <b>{nb_sessions_saison}</b> sorties</span>
      <span class="spf-stat">🐟 <b>{nb_captures_saison}</b> prises</span>
    </div>
    {session_badge}
  </div>
</div>
<div style="font-size:10px;color:#aaa;text-align:center;margin-bottom:4px;">Saison {saison}</div>
        """, height=110 if en_session else 90)

    except Exception:
        pass  # Fail silently si la DB n'est pas encore initialisée
