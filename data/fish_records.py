"""
Records officiels par espèce — sources : IGFA (International Game Fish Association),
FFPM (Fédération Française des Pêcheurs en Mer), SHF (Sport Halieutique Français).
Valeurs indicatives pour les espèces principales du surfcasting français.

Format : { id_fish_meta: { "taille_cm": float, "poids_g": float, "lieu": str, "annee": str|None } }
"""

# Records "monde / France connus" — surf-casting et bord
# (chiffres approximatifs basés sur tailles maxi publiées)
FISH_RECORDS = {
    "bar": {
        "taille_cm": 105.0,
        "poids_g":   12000,
        "lieu":      "Côtes atlantiques (FR)",
        "annee":     "2012",
    },
    "dorade_royale": {
        "taille_cm": 73.0,
        "poids_g":   7400,
        "lieu":      "Méditerranée (FR/IT)",
        "annee":     "1998",
    },
    "sar": {
        "taille_cm": 45.0,
        "poids_g":   2500,
        "lieu":      "Méditerranée",
        "annee":     None,
    },
    "marbre": {
        "taille_cm": 55.0,
        "poids_g":   1500,
        "lieu":      "Méditerranée",
        "annee":     None,
    },
    "pageot": {
        "taille_cm": 60.0,
        "poids_g":   3500,
        "lieu":      "Atlantique / Méditerranée",
        "annee":     None,
    },
    "oblade": {
        "taille_cm": 34.0,
        "poids_g":   600,
        "lieu":      "Méditerranée",
        "annee":     None,
    },
    "dorade_grise": {
        "taille_cm": 60.0,
        "poids_g":   4000,
        "lieu":      "Atlantique (FR)",
        "annee":     None,
    },
    "maigre": {
        "taille_cm": 230.0,
        "poids_g":   103000,
        "lieu":      "Estuaire Gironde (FR)",
        "annee":     "1990",
    },
    "lieu_jaune": {
        "taille_cm": 130.0,
        "poids_g":   18000,
        "lieu":      "Bretagne (FR)",
        "annee":     None,
    },
    "cabillaud": {
        "taille_cm": 200.0,
        "poids_g":   96000,
        "lieu":      "Atlantique Nord",
        "annee":     "1969",
    },
    "sole": {
        "taille_cm": 70.0,
        "poids_g":   3000,
        "lieu":      "Manche / Atlantique (FR)",
        "annee":     None,
    },
    "plie": {
        "taille_cm": 95.0,
        "poids_g":   6000,
        "lieu":      "Mer du Nord",
        "annee":     None,
    },
    "turbot": {
        "taille_cm": 100.0,
        "poids_g":   25000,
        "lieu":      "Mer du Nord / Atlantique",
        "annee":     None,
    },
    "merlan": {
        "taille_cm": 70.0,
        "poids_g":   3500,
        "lieu":      "Manche / Mer du Nord",
        "annee":     None,
    },
    "tacaud": {
        "taille_cm": 45.0,
        "poids_g":   1800,
        "lieu":      "Atlantique (FR)",
        "annee":     None,
    },
    "maquereau": {
        "taille_cm": 60.0,
        "poids_g":   3400,
        "lieu":      "Norvège",
        "annee":     "1992",
    },
    "mulet": {
        "taille_cm": 90.0,
        "poids_g":   7500,
        "lieu":      "Atlantique (FR)",
        "annee":     None,
    },
    "congre": {
        "taille_cm": 300.0,
        "poids_g":   60000,
        "lieu":      "Manche (Brixham, UK)",
        "annee":     "1995",
    },
    "raie": {
        "taille_cm": 105.0,
        "poids_g":   18000,
        "lieu":      "Atlantique / Manche",
        "annee":     None,
    },
    "roussette": {
        "taille_cm": 100.0,
        "poids_g":   4000,
        "lieu":      "Atlantique (FR)",
        "annee":     None,
    },
    "orphie": {
        "taille_cm": 95.0,
        "poids_g":   1200,
        "lieu":      "Atlantique / Méditerranée",
        "annee":     None,
    },
    "vive": {
        "taille_cm": 53.0,
        "poids_g":   2400,
        "lieu":      "Atlantique / Méditerranée",
        "annee":     None,
    },
}


def get_official_record(fish_id: str) -> dict | None:
    """Renvoie le record officiel d'un poisson, ou None si inconnu."""
    return FISH_RECORDS.get(fish_id)
