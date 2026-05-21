"""
Page Mes spots — spots de pêche pré-enregistrés.
Réutilisables dans les autres pages via location_picker.
Inclut : photos à l'ajout, gestion photos (ajouter/supprimer) dans la liste.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from core.database import load_spots, load_multimedia, insert_row, update_row, delete_row
from core.storage import save_spot_photo
from core.utils import safe_str, safe_float
from ui.components import hero, section, confirm_destructive, location_picker, terrestrial_map

TYPES_FOND = ["Sable", "Sable + roche", "Roche", "Vase", "Mixte", "Inconnu"]
ACCES = ["Plage", "Jetée / digue", "Falaise", "Rochers", "Port", "Estuaire", "Autre"]


def render() -> None:
    hero("Mes spots", "Spots de pêche enregistrés",
         "Crée et consulte tes spots. Retrouve-les rapidement dans les conditions, sessions et services.")

    tab_add, tab_list = st.tabs(["📍 Ajouter un spot", "📚 Consulter"])

    with tab_add:
        _render_add()
    with tab_list:
        _render_list()


# ─────────────────────────────────────────────────────────────────────────────
# Ajout
# ─────────────────────────────────────────────────────────────────────────────

def _render_add() -> None:
    section("Nouveau spot", icon="📍")

    nom = st.text_input("Nom du spot *", placeholder="Ex: Plage de la Salie sud", key="spot_nom")
    with st.container(border=True):
        st.caption("Positionne le spot :")
        latitude, longitude = location_picker("spot_loc")

    if latitude is None or longitude is None:
        latitude, longitude = 44.656588, -1.196303

    c1, c2 = st.columns(2)
    with c1:
        type_fond  = st.selectbox("Type de fond",    TYPES_FOND, key="spot_fond")
        profondeur = st.text_input("Profondeur",      placeholder="Ex: 3–8 m", key="spot_prof")
    with c2:
        acces   = st.selectbox("Accès", ACCES, key="spot_acces")
        especes = st.text_input("Espèces cibles",    placeholder="Bar, daurade, sole...", key="spot_especes")

    commentaire = st.text_area("Notes / conseils",   placeholder="Courant fort à marée descendante...", key="spot_com")
    favori = st.checkbox("⭐ Spot favori", key="spot_fav")

    # ── Photos (hors formulaire) ──────────────────────────────────────
    with st.container(border=True):
        st.markdown("**📸 Photos du spot** *(optionnel)*")
        col_cam, col_up = st.columns(2)
        cam = col_cam.camera_input("Prendre une photo", key="spot_add_cam")
        upl = col_up.file_uploader("Importer une photo",
                                   type=["jpg","jpeg","png","webp"],
                                   key="spot_add_upl")
        add_photo = upl if upl is not None else cam

    if st.button("💾 Enregistrer le spot", use_container_width=True, key="spot_save"):
        if not nom.strip():
            st.error("Le nom du spot est obligatoire.")
        else:
            spot_id = insert_row("spots", {
                "nom": nom.strip(),
                "latitude": latitude,
                "longitude": longitude,
                "type_fond": type_fond,
                "profondeur": profondeur,
                "acces": acces,
                "especes_cibles": especes,
                "commentaire": commentaire,
                "favori": int(favori),
                "created_at": datetime.now().isoformat(timespec="seconds"),
            })
            # Sauvegarder la photo si fournie
            if add_photo and spot_id:
                pp = save_spot_photo(add_photo, spot_id)
                if pp:
                    insert_row("multimedia", {
                        "categorie":  "Spot",
                        "titre":      nom.strip(),
                        "photo_path": pp,
                        "espece":     f"spot_{spot_id}",
                        "favori":     0,
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                    })
            st.cache_data.clear()
            st.success(f"✅ Spot « {nom} » enregistré.")
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Liste
# ─────────────────────────────────────────────────────────────────────────────

def _render_list() -> None:
    df = load_spots()

    if df.empty:
        st.info("Aucun spot enregistré. Commence par en ajouter un dans l'onglet ci-dessus.")
        return

    c1, c2 = st.columns(2)
    search   = c1.text_input("Rechercher", placeholder="Nom, espèce, fond...", key="spot_search")
    fav_only = c2.checkbox("⭐ Favoris uniquement", key="spot_fav_only")

    if search:
        s = search.lower()
        mask = df.astype(str).apply(lambda c: c.str.lower().str.contains(s, na=False)).any(axis=1)
        df = df[mask]
    if fav_only:
        df = df[df["favori"].fillna(0).astype(int) == 1]

    if df.empty:
        st.info("Aucun résultat.")
        return

    st.caption(f"{len(df)} spot(s)")

    for _, row in df.iterrows():
        spot_id = int(row["id"])
        nom     = safe_str(row.get("nom")) or "—"
        lat     = safe_float(row.get("latitude"))
        lon     = safe_float(row.get("longitude"))
        is_fav  = bool(row.get("favori"))

        with st.container(border=True):
            col_info, col_map, col_act = st.columns([2.5, 2, 0.8])

            with col_info:
                st.markdown(f"{'⭐ ' if is_fav else ''}**{nom}**")
                details = []
                for lbl, k in [("Fond","type_fond"),("Profondeur","profondeur"),
                                ("Accès","acces"),("Espèces","especes_cibles")]:
                    v = safe_str(row.get(k))
                    if v: details.append(f"{lbl} : {v}")
                if details:
                    st.caption("  ·  ".join(details))
                st.caption(f"📍 {lat:.5f}, {lon:.5f}")
                com = safe_str(row.get("commentaire"))
                if com:
                    st.caption(f"💬 {com}")

            with col_map:
                with st.expander("🗺️ Voir carte", expanded=False):
                    terrestrial_map(lat, lon, height=200)

            with col_act:
                fav_btn = "💛" if is_fav else "☆"
                if st.button(fav_btn, key=f"spot_fav_{spot_id}",
                             use_container_width=True, help="Basculer favori"):
                    update_row("spots", spot_id, {"favori": 0 if is_fav else 1})
                    st.cache_data.clear()
                    st.rerun()

                # Toggle photos
                photos_key = f"spot_photos_open_{spot_id}"
                photos_lbl = "📸✕" if st.session_state.get(photos_key) else "📸"
                if st.button(photos_lbl, key=f"spot_photos_btn_{spot_id}",
                             use_container_width=True, help="Gérer les photos"):
                    st.session_state[photos_key] = not st.session_state.get(photos_key, False)
                    st.rerun()

                if st.button("🗑️ Supprimer", key=f"spot_del_{spot_id}", use_container_width=True):
                    st.session_state[f"spot_confirm_{spot_id}"] = True

            # ── Section photos ──────────────────────────────────────
            if st.session_state.get(f"spot_photos_open_{spot_id}"):
                _render_spot_photos(spot_id, nom)

            if st.session_state.get(f"spot_confirm_{spot_id}"):
                if confirm_destructive(f"spot_{spot_id}", f"Supprimer le spot « {nom} » ?"):
                    delete_row("spots", spot_id)
                    st.session_state[f"spot_confirm_{spot_id}"] = False
                    st.cache_data.clear()
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Gestion photos d'un spot
# ─────────────────────────────────────────────────────────────────────────────

def _render_spot_photos(spot_id: int, nom: str) -> None:
    with st.container(border=True):
        st.markdown(f"**📸 Photos — {nom}**")

        # Charger photos existantes
        try:
            mm = load_multimedia()
        except Exception:
            mm = None

        photos = []
        if mm is not None and not mm.empty and "espece" in mm.columns:
            photos = mm[mm["espece"].astype(str) == f"spot_{spot_id}"].to_dict("records")

        # Afficher photos existantes avec bouton supprimer
        if photos:
            cols = st.columns(min(len(photos), 4))
            for j, p in enumerate(photos):
                pp      = safe_str(p.get("photo_path"))
                pid     = int(p.get("id", 0))
                titre   = safe_str(p.get("titre")) or f"Photo {j+1}"
                with cols[j % 4]:
                    if pp and Path(pp).exists():
                        st.image(pp, caption=titre, use_container_width=True)
                    else:
                        st.caption(f"_{titre} (fichier manquant)_")
                    if st.button("🗑️ Supprimer", key=f"del_spot_photo_{pid}_{spot_id}",
                                  use_container_width=True, help="Supprimer cette photo"):
                        # Supprimer le fichier et l'entrée DB
                        if pp and Path(pp).exists():
                            try: Path(pp).unlink()
                            except Exception: pass
                        delete_row("multimedia", pid)
                        st.cache_data.clear()
                        st.success("Photo supprimée.")
                        st.rerun()
        else:
            st.caption("Aucune photo pour ce spot.")

        # Ajouter une photo (hors form)
        st.markdown("**Ajouter une photo :**")
        col_cam, col_up = st.columns(2)
        cam = col_cam.camera_input("Prendre",   key=f"sp_cam_{spot_id}")
        upl = col_up.file_uploader("Importer",  type=["jpg","jpeg","png","webp"],
                                    key=f"sp_upl_{spot_id}")
        new_photo = upl if upl is not None else cam
        titre_ph  = st.text_input("Titre / légende",
                                   placeholder="Ex : Vue générale, Setup, Coucher de soleil…",
                                   key=f"sp_titre_{spot_id}")
        if new_photo:
            if st.button("💾 Enregistrer cette photo",
                          key=f"sp_save_photo_{spot_id}",
                          type="primary", use_container_width=True):
                pp = save_spot_photo(new_photo, spot_id)
                if pp:
                    insert_row("multimedia", {
                        "categorie":  "Spot",
                        "titre":      titre_ph or nom,
                        "photo_path": pp,
                        "espece":     f"spot_{spot_id}",
                        "favori":     0,
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                    })
                    st.cache_data.clear()
                    st.success("✅ Photo ajoutée !")
                    st.rerun()
