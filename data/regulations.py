"""
Données de référence : tailles minimales indicatives par espèce et région.

ATTENTION : ces tailles sont des valeurs indicatives et doivent être vérifiées
avec les textes officiels (Mer.gouv, Légifrance, arrêtés préfectoraux).
"""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

from core.utils import safe_str


# ---------------------------------------------------------------------------
# Mapping régions / façade maritime
# ---------------------------------------------------------------------------

REGION_TO_ZONE = {
    "atlantique sud-ouest": "Atlantique",
    "atlantique centre-ouest": "Atlantique",
    "bretagne": "Manche / Atlantique",
    "normandie": "Manche",
    "manche": "Manche",
    "mer du nord": "Mer du Nord",
    "méditerranée": "Méditerranée",
    "corse": "Méditerranée",
}


def estimate_region(address: Dict[str, str]) -> Dict[str, str]:
    """Déduit une région de pêche à partir d'une adresse OSM."""
    city = (
        address.get("city") or address.get("town")
        or address.get("village") or address.get("municipality") or ""
    )
    county = address.get("county") or address.get("state_district") or ""
    state = address.get("state") or address.get("region") or ""
    country = address.get("country") or ""
    haystack = " ".join([city, county, state, country]).lower()

    if "arcachon" in haystack or "gironde" in haystack:
        return {
            "region": "Atlantique Sud-Ouest — Gironde",
            "zone": "Atlantique",
            "profil": "Bar, daurades, maigre, marbré, mulet, sole, raies, tacaud.",
            "city": city, "county": county, "state": state, "country": country,
        }
    if "landes" in haystack or "pyrénées-atlantiques" in haystack:
        return {
            "region": "Atlantique Sud-Ouest — Landes / Pays basque",
            "zone": "Atlantique",
            "profil": "Bar, maigre, daurades, marbré, raies, sole, mulet.",
            "city": city, "county": county, "state": state, "country": country,
        }
    if "charente-maritime" in haystack or "vendée" in haystack:
        return {
            "region": "Atlantique Centre-Ouest",
            "zone": "Atlantique",
            "profil": "Bar, daurades, maigre, sole, plie, raies, tacaud.",
            "city": city, "county": county, "state": state, "country": country,
        }
    if any(k in haystack for k in ["bretagne", "finistère", "morbihan", "côtes-d'armor", "ille-et-vilaine"]):
        return {
            "region": "Bretagne",
            "zone": "Manche / Atlantique",
            "profil": "Bar, lieu jaune, tacaud, dorades, raies, plie, sole.",
            "city": city, "county": county, "state": state, "country": country,
        }
    if any(k in haystack for k in ["normandie", "calvados", "manche", "seine-maritime"]):
        return {
            "region": "Manche / Normandie",
            "zone": "Manche",
            "profil": "Bar, plie, sole, tacaud, merlan, raies, lieu.",
            "city": city, "county": county, "state": state, "country": country,
        }
    if any(k in haystack for k in ["hauts-de-france", "pas-de-calais", "nord", "somme"]):
        return {
            "region": "Manche Est / Mer du Nord",
            "zone": "Manche / Mer du Nord",
            "profil": "Bar, plie, sole, merlan, tacaud, raies.",
            "city": city, "county": county, "state": state, "country": country,
        }
    if any(k in haystack for k in ["occitanie", "provence", "côte d'azur", "corse", "méditerranée"]):
        return {
            "region": "Méditerranée française",
            "zone": "Méditerranée",
            "profil": "Loup, dorade royale, marbré, sar, mulet, pageot, sole.",
            "city": city, "county": county, "state": state, "country": country,
        }
    return {
        "region": "Région à confirmer",
        "zone": "À confirmer",
        "profil": "Espèces probables à vérifier selon le littoral.",
        "city": city, "county": county, "state": state, "country": country,
    }


# ---------------------------------------------------------------------------
# Tailles minimales indicatives
# ---------------------------------------------------------------------------

_COMMON_SIZES: List[Dict[str, str]] = [
    {"Espèce": "Bar / Loup", "Taille mini indicative": "42 cm", "Remarque": "Règles très variables selon façade et période — vérifier impérativement."},
    {"Espèce": "Daurade royale", "Taille mini indicative": "23 cm", "Remarque": "Espèce majeure plages, estuaires, bassins."},
    {"Espèce": "Daurade grise / Griset", "Taille mini indicative": "23 cm", "Remarque": "À vérifier selon zone."},
    {"Espèce": "Daurade rose / Pageot", "Taille mini indicative": "33 cm", "Remarque": "Variable selon façade."},
    {"Espèce": "Sar commun", "Taille mini indicative": "23 cm", "Remarque": "Surtout zones rocheuses / mixtes."},
    {"Espèce": "Marbré", "Taille mini indicative": "20 cm", "Remarque": "Très courant en Méditerranée."},
    {"Espèce": "Muge / Mulet", "Taille mini indicative": "30 cm", "Remarque": "Famille complexe — vérifier l'espèce exacte."},
    {"Espèce": "Maigre", "Taille mini indicative": "45 cm", "Remarque": "Espèce importante en Atlantique Sud-Ouest."},
    {"Espèce": "Sole commune", "Taille mini indicative": "24 cm", "Remarque": "Attention aux confusions avec autres poissons plats."},
    {"Espèce": "Plie", "Taille mini indicative": "27 cm", "Remarque": "Manche / Atlantique Nord surtout."},
    {"Espèce": "Turbot", "Taille mini indicative": "30 cm", "Remarque": "Vérifier règles locales."},
    {"Espèce": "Merlan", "Taille mini indicative": "27 cm", "Remarque": "Plutôt Manche / Atlantique Nord."},
    {"Espèce": "Tacaud", "Taille mini indicative": "À vérifier", "Remarque": "Réglementation très variable."},
    {"Espèce": "Lieu jaune", "Taille mini indicative": "30 cm", "Remarque": "Secteurs rocheux / côtiers."},
    {"Espèce": "Congre", "Taille mini indicative": "60 cm", "Remarque": "Espèce puissante, souvent de nuit."},
    {"Espèce": "Raie bouclée", "Taille mini indicative": "45 cm", "Remarque": "Identifier l'espèce de raie avant toute conservation."},
    {"Espèce": "Maquereau", "Taille mini indicative": "20 cm", "Remarque": "Plus fréquent au lancer."},
]

_MED_EXTRA: List[Dict[str, str]] = [
    {"Espèce": "Oblade", "Taille mini indicative": "12 cm", "Remarque": "Fréquente Méditerranée."},
    {"Espèce": "Saupe", "Taille mini indicative": "12 cm", "Remarque": "Fréquente Méditerranée."},
    {"Espèce": "Bogue", "Taille mini indicative": "10 cm", "Remarque": "Fréquente Méditerranée."},
    {"Espèce": "Rouget barbet", "Taille mini indicative": "15 cm", "Remarque": "À vérifier localement."},
]

_ATL_EXTRA: List[Dict[str, str]] = [
    {"Espèce": "Lieu noir", "Taille mini indicative": "35 cm", "Remarque": "Surtout Manche / Atlantique Nord."},
    {"Espèce": "Flet", "Taille mini indicative": "20 cm", "Remarque": "Estuaires."},
    {"Espèce": "Émissole", "Taille mini indicative": "À vérifier", "Remarque": "Espèce à identifier précisément."},
]


def get_minimum_sizes_table(region_zone: str) -> pd.DataFrame:
    """Retourne un DataFrame des tailles minimales adaptées à la zone."""
    rows = list(_COMMON_SIZES)
    if "méditerranée" in safe_str(region_zone).lower():
        rows.extend(_MED_EXTRA)
    else:
        rows.extend(_ATL_EXTRA)
    df = pd.DataFrame(rows)
    df["À confirmer"] = "Vérifier l'arrêté local en vigueur"
    return df


# ---------------------------------------------------------------------------
# Sources réglementaires
# ---------------------------------------------------------------------------

def get_regulation_sources(country: str = "France") -> pd.DataFrame:
    """Liens vers les sources réglementaires officielles."""
    sources = [
        {"Source": "Mer.gouv — Pêche de loisir en mer", "Type": "Réglementation nationale",
         "Vérifier": "Tailles minimales, marquage, espèces sensibles.",
         "Lien": "https://www.mer.gouv.fr/peche-de-loisir-en-mer"},
        {"Source": "Légifrance — Tailles et poids minimaux", "Type": "Texte officiel consolidé",
         "Vérifier": "Tailles/poids par espèce et zone.",
         "Lien": "https://www.legifrance.gouv.fr/loda/id/JORFTEXT000026582115/"},
        {"Source": "Légifrance — Marquage des captures", "Type": "Texte officiel",
         "Vérifier": "Espèces soumises au marquage.",
         "Lien": "https://www.legifrance.gouv.fr/loda/id/JORFTEXT000024167951/"},
        {"Source": "Vigilance Météo-France", "Type": "Sécurité",
         "Vérifier": "Vent, vagues-submersion, orages, pluie.",
         "Lien": "https://vigilance.meteofrance.fr/fr"},
        {"Source": "Vigicrues", "Type": "Sécurité",
         "Vérifier": "Crues, estuaires, zones basses.",
         "Lien": "https://www.vigicrues.gouv.fr/"},
    ]
    return pd.DataFrame(sources)


# ---------------------------------------------------------------------------
# Quotas de prises par zone (indicatif)
# ---------------------------------------------------------------------------

_CATCH_LIMITS_COMMON = [
    {"Espèce": "Bar / Loup", "Quota journalier": "2 (Atlantique) / 3 (Méditerranée)", "Période": "Restrictions saisonnières — vérifier", "Marquage": "Oui (coupure caudale)"},
    {"Espèce": "Daurade royale", "Quota journalier": "Pas de quota spécifique", "Période": "Toute l'année", "Marquage": "Non"},
    {"Espèce": "Maigre", "Quota journalier": "1 par pêcheur", "Période": "Vérifier localement", "Marquage": "Oui"},
    {"Espèce": "Sole commune", "Quota journalier": "Pas de quota spécifique", "Période": "Toute l'année", "Marquage": "Non"},
    {"Espèce": "Lieu jaune", "Quota journalier": "Pas de quota spécifique", "Période": "Toute l'année", "Marquage": "Non"},
    {"Espèce": "Congre", "Quota journalier": "Pas de quota spécifique", "Période": "Toute l'année", "Marquage": "Non"},
    {"Espèce": "Maquereau", "Quota journalier": "Pas de quota spécifique", "Période": "Toute l'année", "Marquage": "Non"},
]

_CATCH_LIMITS_ATLANTIQUE = [
    {"Espèce": "Bar / Loup", "Quota journalier": "2 par pêcheur/jour", "Période": "Restrictions fév-mars (no-kill)", "Marquage": "Oui"},
    {"Espèce": "Cabillaud / Morue", "Quota journalier": "Interdit en récréatif (certaines zones)", "Période": "Vérifier", "Marquage": "—"},
]

_CATCH_LIMITS_MANCHE = [
    {"Espèce": "Bar / Loup", "Quota journalier": "2 par pêcheur/jour", "Période": "Restrictions fév-mars (no-kill)", "Marquage": "Oui"},
    {"Espèce": "Cabillaud / Morue", "Quota journalier": "Restrictions sévères", "Période": "Vérifier CIEM", "Marquage": "—"},
]

_CATCH_LIMITS_MED = [
    {"Espèce": "Bar / Loup", "Quota journalier": "3 par pêcheur/jour", "Période": "Toute l'année (vérifier)", "Marquage": "Oui"},
    {"Espèce": "Thon rouge", "Quota journalier": "Interdit en récréatif (sauf dérogation)", "Période": "—", "Marquage": "—"},
    {"Espèce": "Sar commun", "Quota journalier": "Pas de quota spécifique", "Période": "Toute l'année", "Marquage": "Non"},
]


def get_catch_limits_table(region_zone: str) -> pd.DataFrame:
    """Retourne un DataFrame des quotas de prises adaptés à la zone."""
    rows = list(_CATCH_LIMITS_COMMON)
    zone = safe_str(region_zone).lower()
    if "méditerranée" in zone:
        rows.extend(_CATCH_LIMITS_MED)
    elif "manche" in zone:
        rows.extend(_CATCH_LIMITS_MANCHE)
    else:
        rows.extend(_CATCH_LIMITS_ATLANTIQUE)

    # Dédoublonner (garder la version spécifique zone)
    seen = {}
    for r in reversed(rows):
        seen[r["Espèce"]] = r
    unique = list(reversed(seen.values()))

    df = pd.DataFrame(unique)
    df["À vérifier"] = "Arrêté local en vigueur"
    return df
