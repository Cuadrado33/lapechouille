"""
Annuaire de webcams plage : France et international.

Structure standardisée pour faciliter l'affichage et le filtrage.
"""

from typing import Dict, List


# ---------------------------------------------------------------------------
# Webcams France (par région)
# ---------------------------------------------------------------------------

WEBCAMS_FRANCE: Dict[str, List[Dict[str, str]]] = {
    "Hauts-de-France": [
        {"nom": "Zuydcoote", "url": "https://viewsurf.com/univers/plage/vue/18184-france-nord-pas-de-calais-zuydcoote-photo-ch-zuydcoote", "type": "direct"},
        {"nom": "Annuaire Hauts-de-France", "url": "https://viewsurf.com/univers/plage/liste", "type": "annuaire"},
    ],
    "Normandie": [
        {"nom": "Le Havre", "url": "https://www.viewsurf.com/univers/plage/vue/18840-france-haute-normandie-le-havre-live", "type": "direct"},
        {"nom": "Dieppe", "url": "https://www.viewsurf.com/univers/plage/vue/19440-france-haute-normandie-dieppe-live", "type": "direct"},
        {"nom": "Étretat", "url": "https://www.viewsurf.com/univers/plage/vue/17578-1192072544-france-haute-normandie-etretat-etretat-sud", "type": "direct"},
        {"nom": "Cherbourg-Octeville", "url": "https://m.viewsurf.com/univers/plage/vue/19376-france-basse-normandie-cherbourg-octeville-plage-de-collignon", "type": "direct"},
        {"nom": "Courseulles-sur-Mer", "url": "https://www.viewsurf.com/univers/plage/vue/19412-france-basse-normandie-courseulles-sur-mer-port-de-courseulles-sur-mer-capitainerie", "type": "direct"},
        {"nom": "Trouville-sur-Mer", "url": "https://viewsurf.com/univers/plage/vue/19416-france-basse-normandie-trouville-sur-mer-port-de-deauville", "type": "direct"},
    ],
    "Bretagne": [
        {"nom": "Bénodet", "url": "https://viewsurf.com/univers/plage/vue/14710-france-bretagne-benodet-live", "type": "direct"},
        {"nom": "Carnac - Saint-Colomban", "url": "https://viewsurf.com/univers/plage/vue/18728-france-bretagne-carnac-pointe-de-st-colomban", "type": "direct"},
        {"nom": "Crozon-Morgat", "url": "https://viewsurf.com/univers/plage/vue/13734-france-bretagne-crozon-morgat-panoramique-hd", "type": "direct"},
        {"nom": "Dinard", "url": "https://viewsurf.com/univers/plage/vue/18324-france-bretagne-dinard-la-plage", "type": "direct"},
        {"nom": "Guilvinec", "url": "https://viewsurf.com/univers/plage/vue/16060-france-bretagne-guilvinec-panoramique-hd", "type": "direct"},
        {"nom": "La Trinité-sur-Mer", "url": "https://viewsurf.com/univers/plage/vue/6586-france-bretagne-la-trinite-sur-mer-panovideo", "type": "direct"},
        {"nom": "Paimpol", "url": "https://viewsurf.com/univers/plage/vue/16958-france-bretagne-paimpol-panoramique-hd", "type": "direct"},
        {"nom": "Saint-Brieuc", "url": "https://viewsurf.com/univers/plage/vue/17652-france-bretagne-saint-brieuc-le-port", "type": "direct"},
    ],
    "Pays de la Loire": [
        {"nom": "Annuaire Pays de la Loire", "url": "https://viewsurf.com/univers/plage/liste", "type": "annuaire"},
    ],
    "Nouvelle-Aquitaine": [
        {"nom": "Lacanau - Plage centrale", "url": "https://m.viewsurf.com/univers/plage/vue/656-1208132642-france-aquitaine-lacanau-plage-centrale", "type": "direct"},
        {"nom": "Lacanau - Surf Club", "url": "https://mobile.viewsurf.com/univers/plage/vue/658-france-aquitaine-lacanau-lacanau-surf-club", "type": "direct"},
        {"nom": "Arcachon - Panoramique", "url": "https://viewsurf.com/univers/plage/vue/13338-france-aquitaine-arcachon-panoramique-hd", "type": "direct"},
        {"nom": "Andernos-les-Bains", "url": "https://viewsurf.com/univers/plage/vue/6764-france-aquitaine-andernos-les-bains-cabanees-tchanquees", "type": "direct"},
        {"nom": "La Teste-de-Buch - Salie Sud", "url": "https://viewsurf.com/univers/plage/vue/18464-france-aquitaine-la-teste-de-buch-plage-de-la-salie-sud", "type": "direct"},
        {"nom": "Biscarrosse Sud", "url": "https://viewsurf.com/univers/plage/vue/13396-france-aquitaine-biscarrosse-sud", "type": "direct"},
        {"nom": "Capbreton - Port", "url": "https://viewsurf.com/univers/plage/vue/3362-france-aquitaine-capbreton-entree-du-port", "type": "direct"},
        {"nom": "Anglet", "url": "https://viewsurf.com/univers/plage/vue/7154-france-aquitaine-anglet-live", "type": "direct"},
        {"nom": "Biarritz - Grande Plage", "url": "https://viewsurf.com/univers/plage/vue/13894-france-aquitaine-biarritz-grande-plage", "type": "direct"},
        {"nom": "Hendaye - Plage des Jumeaux", "url": "https://www.viewsurf.com/univers/plage/vue/7194-france-aquitaine-hendaye-plage-des-jumeaux-live", "type": "direct"},
        {"nom": "Soorts-Hossegor", "url": "https://viewsurf.com/univers/plage/vue/14376-france-aquitaine-soorts-hossegor-plage", "type": "direct"},
        {"nom": "Soulac-sur-Mer", "url": "https://viewsurf.com/univers/plage/vue/15742-france-aquitaine-soulac-sur-mer-panoramique-hd", "type": "direct"},
    ],
    "Occitanie": [
        {"nom": "Annuaire Occitanie", "url": "https://viewsurf.com/univers/plage/liste", "type": "annuaire"},
    ],
    "Provence-Alpes-Côte d'Azur": [
        {"nom": "Le Lavandou - Grande Plage", "url": "https://mobile.viewsurf.com/univers/plage/vue/800-france-provence-alpes-cote-dazur-le-lavandou-grande-plage", "type": "direct"},
        {"nom": "Nice - Promenade des Anglais", "url": "https://viewsurf.com/univers/plage/vue/14280-france-provence-alpes-cote-dazur-nice-promenade-des-anglais", "type": "direct"},
        {"nom": "La Ciotat", "url": "https://m.viewsurf.com/univers/plage/vue/6804-france-provence-alpes-cote-dazur-la-ciotat-les-3-tetes", "type": "direct"},
    ],
    "Corse": [
        {"nom": "Annuaire Corse", "url": "https://www.webcams-de-france.fr/corse", "type": "annuaire"},
    ],
    "La Réunion": [
        {"nom": "Annuaire La Réunion", "url": "https://viewsurf.com/univers/plage/liste", "type": "annuaire"},
    ],
}


# ---------------------------------------------------------------------------
# Webcams International
# ---------------------------------------------------------------------------

WEBCAMS_INTERNATIONAL: Dict[str, List[Dict[str, str]]] = {
    "Espagne": [
        {"nom": "Tenerife - Los Cristianos", "url": "https://www.skylinewebcams.com/en/webcam/espana/canarias/santa-cruz-de-tenerife/playa-los-cristianos.html", "type": "direct"},
        {"nom": "Gran Canaria - Las Canteras", "url": "https://www.skylinewebcams.com/en/webcam/espana/canarias/las-palmas/las-canteras.html", "type": "direct"},
        {"nom": "Marbella", "url": "https://www.skylinewebcams.com/en/webcam/espana/andalucia/malaga/marbella.html", "type": "direct"},
    ],
    "Portugal": [
        {"nom": "Nazaré - Praia do Norte", "url": "https://www.skylinewebcams.com/en/webcam/portugal/leiria/nazare/praia-do-norte.html", "type": "direct"},
        {"nom": "Costa da Caparica", "url": "https://beachcam.meo.pt/livecams/costa-da-caparica-praia-do-tarquínio/", "type": "direct"},
        {"nom": "Ericeira", "url": "https://beachcam.meo.pt/livecams/ericeira-praia-dos-pescadores/", "type": "direct"},
    ],
    "Maroc": [
        {"nom": "Essaouira", "url": "https://www.skylinewebcams.com/en/webcam/morocco/marrakech-safi/essaouira/essaouira-beach.html", "type": "direct"},
        {"nom": "Agadir", "url": "https://www.skylinewebcams.com/en/webcam/morocco/souss-massa/agadir/agadir-beach.html", "type": "direct"},
    ],
    "Royaume-Uni": [
        {"nom": "Cornwall - St Ives", "url": "https://www.skylinewebcams.com/en/webcam/united-kingdom/england/cornwall/st-ives.html", "type": "direct"},
        {"nom": "Brighton", "url": "https://www.skylinewebcams.com/en/webcam/united-kingdom/england/brighton-and-hove/brighton.html", "type": "direct"},
    ],
    "Italie": [
        {"nom": "Gênes - Boccadasse", "url": "https://www.skylinewebcams.com/en/webcam/italia/liguria/genova/boccadasse.html", "type": "direct"},
        {"nom": "Sicile - Mondello", "url": "https://www.skylinewebcams.com/en/webcam/italia/sicilia/palermo/mondello.html", "type": "direct"},
    ],
    "Grèce": [
        {"nom": "Santorin", "url": "https://www.skylinewebcams.com/en/webcam/ellada/south-aegean/thira/santorini.html", "type": "direct"},
        {"nom": "Mykonos", "url": "https://www.skylinewebcams.com/en/webcam/ellada/south-aegean/mykonos/mykonos.html", "type": "direct"},
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_all_webcams() -> List[Dict[str, str]]:
    """Aplatit toutes les webcams en une liste enrichie."""
    out = []
    for region, items in WEBCAMS_FRANCE.items():
        for w in items:
            out.append({
                "Pays": "France",
                "Région / Zone": region,
                "Nom": w["nom"],
                "URL": w["url"],
                "Type": w["type"],
            })
    for country, items in WEBCAMS_INTERNATIONAL.items():
        for w in items:
            out.append({
                "Pays": country,
                "Région / Zone": "International",
                "Nom": w["nom"],
                "URL": w["url"],
                "Type": w["type"],
            })
    return out
