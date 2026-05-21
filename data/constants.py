"""
Constantes de référence : poissons, appâts, montages, hameçons, fils, matériel.

Centralisées ici pour éviter les duplications et faciliter les mises à jour.
"""

# ---------------------------------------------------------------------------
# Espèces de poissons (Atlantique + Méditerranée)
# ---------------------------------------------------------------------------

ESPECES = [
    "Aiguillette", "Aiguillat", "Anchois", "Anguille", "Baliste",
    "Bar / Loup", "Barbue", "Bogue", "Bonite", "Chinchard", "Congre",
    "Daurade grise / Griset", "Daurade rose / Pageot", "Daurade royale",
    "Dorade coryphène", "Émissole", "Éperlan", "Flet",
    "Grande vive", "Grondin perlon", "Grondin rouge",
    "Lançon", "Leerfish / Liche", "Liche amie", "Liche glauque",
    "Lieu jaune", "Lieu noir", "Limande", "Maigre", "Maquereau",
    "Marbré", "Merlan", "Mostelle", "Muge / Mulet", "Murène",
    "Oblade", "Orphie", "Pélamide", "Petite vive", "Plie",
    "Poisson-lézard", "Raie bouclée", "Raie brunette",
    "Raie pastenague", "Raie torpille", "Rascasse",
    "Requin hâ", "Rouget barbet", "Roussette",
    "Saint-Pierre", "Sar à tête noire", "Sar commun", "Sar tambour",
    "Sardine", "Saupe", "Serran chevrette", "Serran écriture",
    "Serre / Tassergal", "Sole commune", "Tacaud", "Turbot", "Vive",
    "Autre",
]


# ---------------------------------------------------------------------------
# Appâts (organisés par familles)
# ---------------------------------------------------------------------------

APPATS = [
    "Non renseigné",
    # Vers
    "Américain", "Arénicole", "Bibi", "Bibi ligaturé", "Cordelle",
    "Demi-dure", "Dure", "Gravette blanche", "Gravette rouge",
    "Jumbo", "Machotte", "Mille-pattes / Néréide", "Mouron", "Pistiche",
    "Ver de chalut", "Ver de sable", "Ver de tube", "Ver de vase", "Ver miracle",
    # Crustacés
    "Bernard-l'hermite", "Crabe dur", "Crabe mou", "Crabe vert",
    "Crabe vivant", "Crabe congelé", "Crevette grise", "Crevette rose",
    "Crevette crue décortiquée", "Gambas crue", "Langoustine", "Petit crabe entier",
    # Coquillages
    "Coque", "Couteau", "Couteau ligaturé", "Moule", "Moule ligaturée",
    "Palourde", "Praire", "Telline", "Lavagnon", "Amande de mer",
    # Céphalopodes
    "Calamar", "Encornet", "Lanière de calamar", "Lanière de seiche",
    "Seiche", "Tentacule de calamar", "Tentacule de seiche",
    # Poissons / morceaux
    "Anchois", "Éperlan", "Filet de maquereau", "Filet de sardine",
    "Lançon", "Maquereau entier", "Morceau de maquereau",
    "Morceau de poisson", "Sardine", "Sardine ligaturée",
    "Vif", "Poisson mort manié",
    # Combos / divers
    "Combo bibi + crabe", "Combo arénicole + crabe", "Combo ver + coquillage",
    "Pâte odorante", "Attractant", "Maïs", "Pain",
    "Autre",
]


# ---------------------------------------------------------------------------
# Montages
# ---------------------------------------------------------------------------

MONTAGES = [
    "Traînard simple", "Traînard double", "Empile haute",
    "Pulley rig", "Wishbone", "Montage coulissant",
    "Montage clipé distance", "Montage compétition",
    "Autre",
]


# ---------------------------------------------------------------------------
# Hameçons
# ---------------------------------------------------------------------------

MARQUES_HAMECONS = [
    "Asari", "BKK", "Daiwa", "Decoy", "Flashmer", "Gamakatsu",
    "Hayabusa", "Kamasan", "Maruto", "Mustad", "Owner", "Sasame",
    "Sunset", "VMC", "Yuki", "Autre",
]

TYPES_HAMECONS = [
    "Aberdeen", "Assist hook", "Baitholder", "Chinu", "Circle hook",
    "Crystal", "J-hook", "Long shank", "Octopus", "Short shank",
    "Simple", "Wide gape", "Autre",
]

MODELES_HAMECONS = [
    "Asari Chinu", "BKK Chinu", "Daiwa Chinu",
    "Flashmer Impact", "Flashmer Pro Surfcasting",
    "Flashmer Special Mediterranee", "Flashmer Special Surf",
    "Gamakatsu LS3310F", "Hayabusa CHN018",
    "Kamasan B940", "Maruto Chinu", "Mustad Chinu",
    "Owner Chinu 50355", "Owner Cut Chinu 50339",
    "Sasame Chinu Dark Black", "Sasame Chinu Ringed",
    "Sunset RS Competition Special Surfcasting",
    "Sunset RS Competition Special Vers",
    "Sunset RS Competition Special Daurade",
    "VMC 7126 Chinu Palette", "VMC 7136 Chinu Oeillet",
    "VMC 9291 NI", "VMC 9291 PS",
    "Yuki AX61", "Yuki AX63", "Yuki AX78",
    "Yuki BX75", "Yuki CX01", "Yuki CX05",
    "Autre",
]

TAILLES_HAMECONS = [
    "N° 12", "N° 10", "N° 9", "N° 8", "N° 7", "N° 6", "N° 5", "N° 4",
    "N° 3", "N° 2", "N° 1",
    "1/0", "2/0", "3/0", "4/0", "5/0", "6/0",
    "Autre",
]


# ---------------------------------------------------------------------------
# Fils
# ---------------------------------------------------------------------------

FILS_BOBINE = ["Nylon", "Tresse", "Fluorocarbone", "Autre"]
FILS_CORPS = ["Nylon", "Tresse", "Fluorocarbone", "Autre"]
FILS_EMPILE = ["Nylon", "Fluorocarbone", "Tresse", "Autre"]
TAILLES_LIGNE = [f"{i}/100" for i in range(6, 101)] + ["Autre"]
LONGUEURS_CM = [f"{i} cm" for i in range(10, 401, 10)] + ["Autre"]


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

TYPES_SESSION = ["Loisir", "Entraînement", "Compétition"]
PHASES_MAREE = ["Montante", "Descendante", "Étale haute", "Étale basse", "Inconnue"]
CLARTE_EAU = ["Claire", "Moyenne", "Trouble", "Très trouble"]


# ---------------------------------------------------------------------------
# Matériel
# ---------------------------------------------------------------------------

MARQUES_MATERIEL = [
    "Anyfish Anywhere", "Colmic", "Daiwa", "Drennan", "Flashmer",
    "Garbolino", "Grauvell", "Leoni", "Mitchell", "Okuma", "Penn",
    "Preston", "Sakura", "Sensas", "Shimano", "Sunset",
    "Tuberti", "Vercelli", "VMC", "Yuki", "Autre",
]

CATEGORIES_MATERIEL = [
    "Canne", "Moulinet", "Bobine", "Fil", "Hameçon",
    "Montage", "Plomb", "Pique / support", "Sac / rangement",
    "Lampe", "Waders / vêtements", "Accessoire", "Autre",
]

ETATS_MATERIEL = ["Neuf", "Très bon", "Bon", "Usé", "À réparer", "À remplacer"]
TYPES_SCION = ["Hybride", "Tubulaire", "Plein", "Non concerné", "Autre"]
ACTIONS_CANNE = ["Fast", "Regular Fast", "Regular", "Slow", "Progressive", "Non concerné", "Autre"]
TYPES_MOULINET = ["Surfcasting", "Long cast", "Frein avant", "Frein arrière", "Débrayable", "Spinning", "Autre"]
TYPES_PLOMBS = [
    "Grappin fixe", "Grappin débrayable", "Plomb bombe",
    "Plomb portugais", "Plomb montre", "Plomb pyramide",
    "Plomb étoile", "Plomb olive", "Plomb coulissant",
    "Autre",
]


# ---------------------------------------------------------------------------
# Spots
# ---------------------------------------------------------------------------

TYPES_FOND = [
    "Non renseigné", "Sable", "Sable + galets", "Galets", "Roche",
    "Sable + roche", "Vase", "Posidonies", "Mixte", "Autre",
]

PROFONDEURS = [
    "Non renseigné", "Très faible (< 1 m)", "Faible (1-3 m)",
    "Moyenne (3-6 m)", "Importante (6-10 m)", "Grande (> 10 m)",
    "Variable", "Autre",
]

ACCES_TYPES = [
    "Non renseigné", "Voiture (parking proche)", "Voiture + marche",
    "Marche uniquement", "Sentier difficile", "Accès technique",
    "Bateau", "Autre",
]


# ---------------------------------------------------------------------------
# Limites globales
# ---------------------------------------------------------------------------

MAX_BOBINES = 10
MAX_EMPILES = 4
MAX_CANNES_SESSION = 10
