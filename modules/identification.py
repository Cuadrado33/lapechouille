"""
Page Identification des poissons.
- Grille cliquable → page détail par espèce
- SVG homogène (boîte fixe 180×90 avec preserveAspectRatio)
- Photos de référence + mes captures + zone observations
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

from data.fish_data import FISH_META, FISH_SVG, FISH_EMOJI_FALLBACK, FISH_BY_ID
from data.emojis import fish_svg_box
from core.database import load_captures, load_profil, save_profil, load_multimedia, insert_row, delete_row
from core.storage import save_multimedia_photo
from core.utils import safe_str, safe_float
from ui.components import hero, section

REGION_COLORS = {"atlantique":"#1565C0","manche":"#00695C","mediterranee":"#C62828"}
REGION_LABELS = {"atlantique":"Atlantique","manche":"Manche","mediterranee":"Méditerranée"}


def _norm_fish_name(s: str) -> str:
    """Normalise un nom de poisson : minuscules, sans accents, daurade↔dorade."""
    if not s:
        return ""
    out = s.lower().strip()
    out = out.replace("daurade", "dorade")
    # Accents → sans accent
    accents = str.maketrans("éèêëàâäîïôöûüç", "eeeeaaaiioouuc")
    out = out.translate(accents)
    return out


def _word_set(s: str) -> set[str]:
    """Découpe un nom en mots significatifs (>= 3 lettres), nettoyés."""
    import re
    n = _norm_fish_name(s)
    # Remplace tout séparateur (/, -, espace, virgule, tiret cadratin) par espace
    n = re.sub(r"[\/\-,–—]", " ", n)
    return {w for w in n.split() if len(w) >= 3}


def _capture_matches_fish(capture_espece: str, fish: dict) -> bool:
    """Vrai si l'espèce d'une capture correspond à la fiche poisson.

    Règle stricte : un mot significatif (≥3 lettres) de la fiche
    doit être présent comme MOT ENTIER dans le nom de la capture,
    et le mot doit être suffisamment spécifique (les mots génériques
    comme « commune », « grand », « petit » ne suffisent pas seuls).
    """
    cap_words = _word_set(capture_espece)
    if not cap_words:
        return False

    # Mots trop génériques pour matcher seuls
    GENERIC = {"commune", "commun", "grande", "grand", "petite", "petit",
               "rouge", "noir", "jaune", "blanc", "rose", "gris", "grise",
               "perle", "perlon", "bouclee", "royale", "comune"}

    # Mots à matcher dans la fiche
    fish_words = _word_set(fish.get("name", ""))
    for alias in (fish.get("aliases") or "").split(","):
        fish_words |= _word_set(alias)

    # Mots spécifiques (non génériques)
    specific = fish_words - GENERIC
    if not specific:
        # Fiche sans mot spécifique : fallback sur tous les mots
        specific = fish_words

    # Match si AU MOINS UN mot spécifique de la fiche est présent dans la capture
    common = specific & cap_words
    if not common:
        return False

    # Cas spécial : si plusieurs fiches partagent un mot spécifique
    # (« dorade » dans Dorade royale et Dorade grise), il faut un mot
    # discriminant supplémentaire.
    DISCRIMINATORS = {
        # Pour distinguer les dorades / daurades
        "dorade": ["royale", "grise", "griset", "rose", "pageot", "coryphene"],
        # Sars
        "sar":    ["commun", "tete", "noire", "tambour"],
        # Lieus
        "lieu":   ["jaune", "noir"],
        # Raies
        "raie":   ["bouclee", "brunette", "torpille", "pastenague"],
        # Vives
        "vive":   ["grande", "petite"],
    }
    # Si la fiche a un mot ambigu, vérifier qu'un discriminateur match aussi
    for shared, discrim_list in DISCRIMINATORS.items():
        if shared in fish_words:
            # La fiche est concernée par cette ambiguïté
            fish_discrim = {d for d in discrim_list if d in fish_words}
            cap_discrim  = {d for d in discrim_list if d in cap_words}
            if fish_discrim and cap_discrim:
                # Les deux ont un discriminant → ils doivent partager au moins un
                if not (fish_discrim & cap_discrim):
                    return False
            elif fish_discrim and not cap_discrim:
                # La fiche est spécifique, mais la capture est générique → match permissif
                # (ex: capture "Dorade" → matche Dorade royale et Dorade grise, on accepte)
                pass
            elif cap_discrim and not fish_discrim:
                # La capture est précise mais la fiche générique → pas de match strict
                return False

    return True


# Hauteur fixe des boîtes SVG dans la grille (px)
SVG_W, SVG_H = 200, 95


def render() -> None:
    selected = st.session_state.get("fish_detail_id")
    if selected and selected in FISH_BY_ID:
        _render_detail(FISH_BY_ID[selected])
        return
    _render_grid()


# ─────────────────────────────────────────────────────────────────────────────
# Grille homogène
# ─────────────────────────────────────────────────────────────────────────────

def _render_grid() -> None:
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:14px 20px;border-radius:8px;margin:8px 0 18px;">'
        '<span style="font-size:18px;font-weight:800;">🐟 Identification des poissons</span>'
        '<div style="font-size:12px;opacity:.85;margin-top:3px;">'
        'Clique sur une espèce pour la fiche complète — illustrations, tailles, observations.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    cf1, cf2 = st.columns([2, 2])
    with cf1:
        region_filter = st.selectbox("Façade maritime",
            ["Toutes","Atlantique","Manche","Méditerranée"], key="fishid_region")
    with cf2:
        search = st.text_input("Rechercher", placeholder="bar, dorade, sole…", key="fishid_search")

    reg_map = {"toutes":None,"atlantique":"atlantique","manche":"manche","méditerranée":"mediterranee"}
    reg_key = reg_map.get(region_filter.lower())

    fishes = [
        f for f in FISH_META
        if (reg_key is None or reg_key in f.get("regions",[]))
        and (not search or any(
            search.lower() in (f.get(k) or "").lower()
            for k in ("name","aliases","latin","notes")
        ))
    ]

    st.caption(f"**{len(fishes)} espèce(s)** — clique sur une fiche pour le détail")
    if not fishes:
        st.info("Aucune espèce trouvée.")
        return

    captures_df = load_captures()

    cols = st.columns(3)
    for i, fish in enumerate(fishes):
        fid     = fish["id"]
        svg_raw = FISH_SVG.get(fid, "")
        tmin    = fish.get("taille_min","—")
        tmax    = fish.get("taille_max","—")
        notes   = fish.get("notes","")
        venimous = "⚠️" in notes

        badges = "".join(
            f'<span style="background:{REGION_COLORS.get(r,"#555")};color:#fff;'
            f'font-size:9px;font-weight:700;letter-spacing:.5px;padding:2px 6px;'
            f'border-radius:10px;margin-right:3px;">{REGION_LABELS.get(r,"").upper()}</span>'
            for r in fish.get("regions",[])
        )
        alias_html = (f' <span style="color:#888;font-size:11px;">'
                      f'· {fish.get("aliases","")}</span>') if fish.get("aliases") else ""

        # SVG dans boîte fixe
        if svg_raw:
            svg_rendered = fish_svg_box(svg_raw, SVG_W, SVG_H)
            svg_block = (
                f'<div style="background:#f5f7f9;border-radius:8px;'
                f'display:flex;align-items:center;justify-content:center;'
                f'width:{SVG_W}px;height:{SVG_H}px;margin:0 auto 8px;">'
                f'{svg_rendered}</div>'
            )
        else:
            emoji = FISH_EMOJI_FALLBACK.get(fid,"🐟")
            svg_block = f'<div style="text-align:center;font-size:48px;padding:12px 0 10px;">{emoji}</div>'

        # Miniatures de mes captures de cette espèce
        my_photos_html = ""
        if not captures_df.empty and "espece" in captures_df.columns:
            mask = captures_df["espece"].apply(
                lambda s: _capture_matches_fish(str(s), fish)
            )
            my_caps = captures_df[mask]
            photos_with_file = [
                safe_str(r.get("photo_path"))
                for _, r in my_caps.iterrows()
                if safe_str(r.get("photo_path")) and Path(safe_str(r.get("photo_path"))).exists()
            ][:4]  # max 4 miniatures
            if photos_with_file:
                thumbs = ""
                for pp in photos_with_file:
                    # Encoder en base64 pour l'injecter inline dans le HTML
                    try:
                        import base64 as _b64
                        with open(pp, "rb") as f:
                            b64 = _b64.b64encode(f.read()).decode()
                        ext = Path(pp).suffix.lower().lstrip(".")
                        mime = "jpeg" if ext in ("jpg","jpeg") else ext
                        thumbs += (
                            f'<img src="data:image/{mime};base64,{b64}" '
                            f'style="width:36px;height:36px;object-fit:cover;'
                            f'border-radius:5px;border:1.5px solid #fff;'
                            f'box-shadow:0 1px 3px rgba(0,0,0,.18);" />'
                        )
                    except Exception:
                        pass
                if thumbs:
                    my_photos_html = (
                        f'<div style="display:flex;gap:4px;align-items:center;'
                        f'margin:6px 0 4px;flex-wrap:wrap;">'
                        f'<span style="font-size:9px;color:#888;font-weight:600;'
                        f'text-transform:uppercase;letter-spacing:.5px;margin-right:2px;">Mes prises</span>'
                        f'{thumbs}</div>'
                    )
            nb_caps = int(mask.sum())
        else:
            nb_caps = 0

        danger = ('<div style="background:#B71C1C;color:#fff;padding:3px 8px;font-size:10px;'
                  'font-weight:700;border-radius:4px;margin-bottom:6px;letter-spacing:.5px;">'
                  '⚠️ VENIMEUX</div>') if venimous else ""

        nb_badge = (
            f'<div style="font-size:9px;color:#1565C0;font-weight:700;margin-top:4px;">'
            f'🎣 {nb_caps} capture{"s" if nb_caps > 1 else ""} enregistrée{"s" if nb_caps > 1 else ""}'
            f'</div>'
        ) if nb_caps > 0 else ""

        card_html = f"""
<div style="font-family:system-ui,sans-serif;border:1px solid #dde2e8;border-radius:12px;
            padding:12px;background:#fff;overflow:hidden;">
  {danger}{svg_block}{my_photos_html}
  <div style="font-weight:800;font-size:13px;margin-bottom:2px;">{fish['name']}{alias_html}</div>
  <div style="color:#888;font-size:10px;font-style:italic;margin-bottom:6px;">{fish.get('latin','')}</div>
  <div style="margin-bottom:7px;">{badges}</div>
  <div style="display:flex;gap:5px;">
    <div style="flex:1;background:#E3F2FD;border-radius:5px;padding:4px;text-align:center;">
      <div style="font-size:8px;color:#1565C0;font-weight:700;">MIN LÉGAL</div>
      <div style="font-size:15px;font-weight:900;color:#1565C0;">{tmin} cm</div>
    </div>
    <div style="flex:1;background:#E8F5E9;border-radius:5px;padding:4px;text-align:center;">
      <div style="font-size:8px;color:#2E7D32;font-weight:700;">MAX</div>
      <div style="font-size:15px;font-weight:900;color:#2E7D32;">{tmax} cm</div>
    </div>
  </div>
  {nb_badge}
</div>"""

        extra_h = 46 if my_photos_html else 0
        with cols[i % 3]:
            components.html(card_html, height=SVG_H + 175 + extra_h, scrolling=False)
            if st.button(f"🔍 {fish['name']}", key=f"open_{fid}", use_container_width=True):
                st.session_state["fish_detail_id"] = fid
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Page détail
# ─────────────────────────────────────────────────────────────────────────────

def _render_detail(fish: dict) -> None:
    fid     = fish["id"]
    name    = fish["name"]
    svg_raw = FISH_SVG.get(fid, "")

    col_b, _ = st.columns([1.5, 4])
    if col_b.button("← Retour à la liste",
                      key="fish_back",
                      use_container_width=True,
                      type="primary"):
        st.session_state.pop("fish_detail_id", None)
        st.rerun()

    # Bandeau bleu marine avec nom du poisson
    alias_html = ""
    if fish.get("aliases"):
        alias_html = (f'<div style="font-size:12px;opacity:.85;margin-top:3px;">'
                      f'Alias : {fish["aliases"]}</div>')
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        f'color:#fff;padding:14px 20px;border-radius:8px;margin:8px 0 18px;">'
        f'<span style="font-size:20px;font-weight:800;">🐟 {name}</span>'
        f'{alias_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 1. SVG grand format centré ────────────────────────────────────
    if svg_raw:
        svg_large = fish_svg_box(svg_raw, 500, 200)
        components.html(
            f'<div style="background:#f5f7f9;border-radius:12px;padding:20px;'
            f'display:flex;align-items:center;justify-content:center;">'
            f'{svg_large}</div>',
            height=240, scrolling=False,
        )
    else:
        st.markdown(
            f'<div style="text-align:center;font-size:80px;padding:20px;">'
            f'{FISH_EMOJI_FALLBACK.get(fid,"🐟")}</div>',
            unsafe_allow_html=True,
        )

    # ── 2. Encadré caractéristiques ───────────────────────────────────
    notes    = fish.get("notes", "")
    venimous = "⚠️" in notes
    tmin     = fish.get("taille_min", "—")
    tmax     = fish.get("taille_max", "—")

    # Âge max estimé (table simplifiée)
    AGE_MAX = {
        "bar": 30, "dorade_royale": 11, "maquereau": 17, "mulet": 25,
        "sole": 30, "plie": 50, "turbot": 25, "raie": 12,
        "congre": 20, "maigre": 30, "lieu_jaune": 15, "cabillaud": 25,
        "merlan": 10, "tacaud": 8, "marbre": 8, "sar": 12,
        "pageot": 12, "oblade": 8, "dorade_grise": 18, "orphie": 10,
        "vive": 12, "roussette": 12,
    }
    age_txt = f"{AGE_MAX[fid]} ans" if fid in AGE_MAX else "—"

    with st.container(border=True):
        st.markdown("**🔬 Caractéristiques**")

        # Métriques en ligne (3 colonnes au lieu de 4)
        c1, c2, c3 = st.columns(3)
        c1.metric("Taille min. légale", f"{tmin} cm")
        c2.metric("Taille max. connue", f"{tmax} cm")
        c3.metric("Âge max. estimé",    age_txt)

        # Régions
        st.markdown("**Présence géographique :**")
        region_html = " ".join(
            f'<span style="background:{REGION_COLORS.get(r,"#555")};color:#fff;'
            f'font-size:11px;font-weight:700;padding:3px 12px;border-radius:10px;'
            f'display:inline-block;margin:2px 4px 2px 0;">'
            f'{REGION_LABELS.get(r, r).upper()}</span>'
            for r in fish.get("regions", [])
        )
        st.markdown(region_html, unsafe_allow_html=True)

        # Caractères d'identification
        st.markdown("**Identification :**")
        if venimous:
            st.warning(notes)
        else:
            st.info(notes)

        # Nom latin
        st.caption(f"*{fish.get('latin','')}*")

    # ── 3. Mes prises de ce poisson ───────────────────────────────────
    captures_df = load_captures()
    my_catches  = []
    if not captures_df.empty and "espece" in captures_df.columns:
        mask = captures_df["espece"].apply(
            lambda s: _capture_matches_fish(str(s), fish)
        )
        my_catches = captures_df[mask]

    nb_prises = len(my_catches) if hasattr(my_catches, "__len__") else 0

    with st.container(border=True):
        st.markdown(f"**🎣 Mes prises — {name}** "
                    f"({'aucune' if nb_prises == 0 else str(nb_prises) + ' capture(s)'})")

        if nb_prises == 0:
            st.caption(f"Tu n'as pas encore enregistré de {name}.")
        else:
            # Stats rapides
            tailles  = my_catches["taille_cm"].dropna() if "taille_cm" in my_catches.columns else []
            poids_l  = my_catches["poids_g"].dropna()   if "poids_g"   in my_catches.columns else []
            best_t   = f"{max(tailles):.0f} cm" if len(tailles) else "—"
            best_p   = f"{max(poids_l):.0f} g"  if len(poids_l) else "—"
            relaches = int(my_catches["relache"].fillna(0).sum()) \
                       if "relache" in my_catches.columns else 0

            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Total",         nb_prises)
            s2.metric("Record taille", best_t)
            s3.metric("Record poids",  best_p)
            s4.metric("Relâchés",      relaches)

            st.markdown("---")

            # Grille de captures avec photos
            catch_cols = st.columns(3)
            for j, (_, c) in enumerate(my_catches.iterrows()):
                pp     = safe_str(c.get("photo_path"))
                taille = safe_float(c.get("taille_cm"))
                poids  = safe_float(c.get("poids_g"))
                date_c = safe_str(c.get("date_session") or
                                  safe_str(c.get("created_at", ""))[:10])
                heure  = safe_str(c.get("heure_capture") or "")
                relach = bool(c.get("relache"))
                with catch_cols[j % 3]:
                    with st.container(border=True):
                        if pp and str(pp).startswith("http"):
                            st.image(pp, use_container_width=True)
                        else:
                            st.markdown(
                                '<div style="aspect-ratio:4/3;background:#e8f4e8;'
                                'border-radius:8px;display:flex;align-items:center;'
                                'justify-content:center;font-size:28px;">🐟</div>',
                                unsafe_allow_html=True,
                            )
                        meta = []
                        if taille: meta.append(f"**{taille:.0f} cm**")
                        if poids:  meta.append(f"{poids:.0f} g")
                        if date_c: meta.append(date_c)
                        if heure:  meta.append(heure)
                        st.caption(" · ".join(meta) if meta else "—")
                        st.caption("↩️ Relâché" if relach else "📦 Gardé")

    # ── 5. Mes observations personnelles ─────────────────────────────
    section("Mes observations", icon="📝")
    st.caption("Notes personnelles — appâts, spots, saisons, comportement…")
    profil = load_profil() or {}
    import json
    try:
        obs_dict = json.loads(safe_str(profil.get("fish_observations") or "{}"))
    except Exception:
        obs_dict = {}
    new_obs = st.text_area(
        f"Observations — {name}",
        value=obs_dict.get(fid, ""),
        placeholder=f"Ex : Le {name} mord mieux au courant montant coef 70+…",
        height=120, key=f"obs_{fid}", label_visibility="collapsed",
    )
    if st.button("💾 Sauvegarder", key=f"save_obs_{fid}", type="primary"):
        obs_dict[fid] = new_obs
        profil["fish_observations"] = json.dumps(obs_dict, ensure_ascii=False)
        profil.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
        profil["updated_at"] = datetime.now().isoformat(timespec="seconds")
        save_profil(profil)
        st.success("✅ Observations sauvegardées !")

    # ── 6. Mes photos personnelles ────────────────────────────────────
    _render_fish_photos(fid, name)


# ─────────────────────────────────────────────────────────────────────────────
# Gestion photos personnelles par espèce
# ─────────────────────────────────────────────────────────────────────────────

def _render_fish_photos(fid: str, name: str) -> None:
    """Section ajout / suppression de photos personnelles pour une espèce."""
    section(f"Mes photos — {name}", icon="🖼️")

    tag = f"fish_{fid}"

    # Charger photos existantes
    try:
        mm = load_multimedia()
        photos = []
        if mm is not None and not mm.empty and "espece" in mm.columns:
            photos = mm[mm["espece"].astype(str) == tag].to_dict("records")
    except Exception:
        photos = []

    # Afficher photos existantes
    if photos:
        cols = st.columns(min(len(photos), 4))
        for j, p in enumerate(photos):
            pp    = safe_str(p.get("photo_path"))
            pid   = int(p.get("id", 0))
            titre = safe_str(p.get("titre")) or f"Photo {j+1}"
            with cols[j % 4]:
                with st.container(border=True):
                    if pp and str(pp).startswith("http"):
                        st.image(pp, use_container_width=True)
                    else:
                        st.caption("_(Pas de photo)_")
                    st.caption(titre)
                    if st.button("🗑️ Supprimer", key=f"del_fish_photo_{pid}",
                                  use_container_width=True):
                        if pp and str(pp).startswith("http"):
                            try: Path(pp).unlink()
                            except Exception: pass
                        delete_row("multimedia", pid)
                        st.cache_data.clear()
                        st.success("Photo supprimée.")
                        st.rerun()
    else:
        st.caption(f"Aucune photo personnelle pour {name}.")

    # Ajouter une photo (hors form — camera_input interdit dans st.form)
    st.markdown("**➕ Ajouter une photo :**")
    col_cam, col_up = st.columns(2)
    cam = col_cam.camera_input("Prendre une photo",  key=f"fish_cam_{fid}")
    upl = col_up.file_uploader("Importer une photo", type=["jpg","jpeg","png","webp"],
                                key=f"fish_upl_{fid}")
    new_photo = upl if upl is not None else cam
    titre_ph  = st.text_input("Titre / légende",
                               placeholder="Ex : Belle prise, Détail nageoire…",
                               key=f"fish_titre_{fid}")
    if new_photo:
        if st.button("💾 Enregistrer cette photo", key=f"fish_save_photo_{fid}",
                      type="primary", use_container_width=True):
            pp = save_multimedia_photo(new_photo, f"fish_{fid}")
            if pp:
                insert_row("multimedia", {
                    "categorie":  "Identification",
                    "titre":      titre_ph or name,
                    "photo_path": pp,
                    "espece":     tag,
                    "favori":     0,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                })
                st.cache_data.clear()
                st.success("✅ Photo ajoutée !")
                st.rerun()
