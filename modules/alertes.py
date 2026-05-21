"""Page Alertes locales."""
from __future__ import annotations
from urllib.parse import quote
import streamlit as st
from core.external_apis import reverse_geocode
from ui.components import hero, section, location_picker

def render() -> None:
    hero("Axe 4 · Divers", "Alertes locales",
         "Points de vigilance à vérifier avant une sortie.")

    # ── Alerte orage active ──────────────────────────────────────────
    if st.session_state.get("storm_alert_2h"):
        st.error("⛈️ **ALERTE ORAGE EN COURS** — Un orage est prévu dans les 2 prochaines heures "
                  "sur ta zone de pêche. Évite de sortir ou rentre immédiatement si tu es en session.")

    section("Localisation", icon="📍")
    with st.container(border=True):
        lat, lon = location_picker("alert")

    if lat is None or lon is None:
        st.info("Choisis une localisation pour voir les alertes.")
        return

    geocode_data = reverse_geocode(lat, lon)
    address = geocode_data.get("address", {})
    city = address.get("city") or address.get("town") or address.get("village") or ""
    county = address.get("county") or ""
    query_place = f"{city} {county}".strip() or f"{lat:.5f},{lon:.5f}"

    alerts = [
        ("Arrêtés préfectoraux", "Haute",
         f"https://www.google.com/search?q={quote(f'arrêté préfectoral pêche littoral {query_place}')}"),
        ("Vigilance météo", "Haute", "https://vigilance.meteofrance.fr/fr"),
        ("Alertes crues", "Moyenne", "https://www.vigicrues.gouv.fr/"),
        ("Pollution littorale", "Moyenne",
         f"https://www.google.com/search?q={quote(f'pollution littoral plage {query_place}')}"),
        ("Qualité eaux de baignade", "Info",
         f"https://www.google.com/search?q={quote(f'qualité eau baignade {query_place}')}"),
    ]

    st.info("Aucune alerte n'est confirmée automatiquement. Vérifie chaque point ci-dessous.")

    for categorie, priorite, lien in alerts:
        with st.container(border=True):
            if priorite == "Haute":
                st.warning(f"**{categorie}** — Priorité : {priorite}")
            elif priorite == "Moyenne":
                st.info(f"**{categorie}** — Priorité : {priorite}")
            else:
                st.caption(f"**{categorie}** — {priorite}")
            st.markdown(f"[Ouvrir la vérification]({lien})")
