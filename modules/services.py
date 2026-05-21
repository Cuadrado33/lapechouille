"""
Page Services à proximité — carte Leaflet + Overpass API depuis le navigateur.
Toutes les requêtes Overpass sont faites côté JS (navigateur) pour les données en temps réel.
Ergonomie : tabs catégories avec compteur, carte + liste côte à côte, fiches POI enrichies.
"""
from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components
from ui.components import hero, section, location_picker

# Catégories avec icônes, couleurs et requêtes Overpass complètes
SERVICES = [
    {
        "id":    "peche",
        "icon":  "🎣",
        "label": "Pêche & outdoor",
        "color": "#0078C8",
        "bg":    "#E3F2FD",
        "overpass": """
            node["shop"~"fishing|outdoor|sports|sport"](around:{r},{lat},{lon});
            way["shop"~"fishing|outdoor|sport"](around:{r},{lat},{lon});
            node["leisure"="fishing"](around:{r},{lat},{lon});
        """,
    },
    {
        "id":    "essence",
        "icon":  "⛽",
        "label": "Stations essence",
        "color": "#FF6B00",
        "bg":    "#FFF3E0",
        "overpass": """
            node["amenity"="fuel"](around:{r},{lat},{lon});
            way["amenity"="fuel"](around:{r},{lat},{lon});
        """,
    },
    {
        "id":    "wc",
        "icon":  "🚻",
        "label": "WC publics",
        "color": "#009688",
        "bg":    "#E0F2F1",
        "overpass": """
            node["amenity"="toilets"](around:{r},{lat},{lon});
        """,
    },
    {
        "id":    "logement",
        "icon":  "🏕️",
        "label": "Logements / camping",
        "color": "#7C3AED",
        "bg":    "#F3E8FF",
        "overpass": """
            node["tourism"~"hotel|motel|camp_site|caravan_site|hostel|guest_house|chalet"](around:{r},{lat},{lon});
            way["tourism"~"hotel|camp_site|caravan_site"](around:{r},{lat},{lon});
        """,
    },
    {
        "id":    "resto",
        "icon":  "🍽️",
        "label": "Restaurants",
        "color": "#E53935",
        "bg":    "#FFEBEE",
        "overpass": """
            node["amenity"~"restaurant|fast_food|cafe|bar|pub|brasserie"](around:{r},{lat},{lon});
            way["amenity"~"restaurant|fast_food|cafe|bar"](around:{r},{lat},{lon});
        """,
    },
    {
        "id":    "parking",
        "icon":  "🅿️",
        "label": "Parkings",
        "color": "#455A64",
        "bg":    "#ECEFF1",
        "overpass": """
            node["amenity"="parking"](around:{r},{lat},{lon});
            way["amenity"="parking"](around:{r},{lat},{lon});
        """,
    },
    {
        "id":    "dechets",
        "icon":  "♻️",
        "label": "Déchets",
        "color": "#558B2F",
        "bg":    "#F1F8E9",
        "overpass": """
            node["amenity"~"waste_disposal|recycling|waste_basket"](around:{r},{lat},{lon});
            node["recycling_type"="centre"](around:{r},{lat},{lon});
        """,
    },
]


def render() -> None:
    hero("4 · Divers", "Services à proximité",
         "Carte en temps réel des services utiles — données OpenStreetMap.")

    # ── Localisation ──────────────────────────────────────────────────
    with st.container(border=True):
        lat, lon = location_picker("svc")

    if lat is None or lon is None:
        st.info("📍 Choisis une localisation pour afficher les services à proximité.")
        return

    radius_km = st.slider("Rayon de recherche", 1, 30, 10,
                          format="%d km", key="svc_radius")
    radius_m  = radius_km * 1000

    # ── Sélection catégorie par boutons visuels ───────────────────────
    st.markdown("**Catégorie**")
    cat_cols = st.columns(len(SERVICES))
    active_id = st.session_state.get("svc_active_cat", SERVICES[0]["id"])

    for i, svc in enumerate(SERVICES):
        with cat_cols[i]:
            is_active = svc["id"] == active_id
            btn_style = (
                f"background:{svc['color']};color:#fff;border:2px solid {svc['color']};"
                if is_active else
                f"background:{svc['bg']};color:{svc['color']};border:2px solid {svc['color']};"
            )
            if st.button(
                f"{svc['icon']}\n{svc['label']}",
                key=f"svc_cat_{svc['id']}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["svc_active_cat"] = svc["id"]
                st.rerun()

    # Sélection courante
    svc = next(s for s in SERVICES if s["id"] == active_id)

    # ── Carte + liste côte à côte ─────────────────────────────────────
    _render_map_and_list(lat, lon, radius_m, svc)


def _render_map_and_list(lat: float, lon: float, radius_m: int, svc: dict) -> None:
    """Rendu principal : carte Leaflet + liste POI. Overpass appelé depuis le JS navigateur."""

    query_raw = svc["overpass"].strip().replace("{r}", str(radius_m)) \
                                       .replace("{lat}", str(lat)) \
                                       .replace("{lon}", str(lon))
    overpass_query = f"[out:json][timeout:20];({query_raw});out center tags;"

    color    = svc["color"]
    icon_ch  = svc["icon"]
    label    = svc["label"]
    gmap_q   = f"{label} près de {lat:.5f},{lon:.5f}"

    from urllib.parse import quote as _q
    gmap_url = f"https://www.google.com/maps/search/?api=1&query={_q(gmap_q)}"

    components.html(f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: system-ui, sans-serif; background: #f8fafc; }}

#layout {{
  display: flex; gap: 12px; height: 520px;
}}
#map {{
  flex: 3; border-radius: 12px; overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,.15);
}}
#sidebar {{
  flex: 1.4; display: flex; flex-direction: column; min-width: 0;
}}
#status-bar {{
  background: {color}; color: #fff; border-radius: 10px;
  padding: 8px 12px; font-size: 12px; font-weight: 700;
  margin-bottom: 8px; display: flex; align-items: center; gap: 6px;
}}
#status-count {{
  background: rgba(255,255,255,.25); border-radius: 20px;
  padding: 2px 8px; font-size: 12px;
}}
#list {{
  flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 7px;
}}
#list::-webkit-scrollbar {{ width: 4px; }}
#list::-webkit-scrollbar-thumb {{ background: #ccc; border-radius: 2px; }}

.poi-card {{
  background: #fff; border: 1px solid #e5e9f0; border-radius: 10px;
  padding: 10px 12px; cursor: pointer; transition: border-color .15s, transform .1s;
}}
.poi-card:hover {{ border-color: {color}; transform: translateY(-1px); }}
.poi-card.active {{ border-color: {color}; border-width: 2px; background: {svc['bg']}; }}
.poi-name {{ font-weight: 700; font-size: 13px; color: #1a2332; margin-bottom: 3px; }}
.poi-dist {{ font-size: 11px; color: #64748b; }}
.poi-detail {{ font-size: 11px; color: #64748b; margin-top: 3px; }}
.poi-detail a {{ color: {color}; text-decoration: none; font-weight: 600; }}

#links-row {{
  margin-top: 8px; display: flex; gap: 8px; flex-wrap: wrap;
}}
.ext-link {{
  display: inline-flex; align-items: center; gap: 4px;
  padding: 6px 12px; border-radius: 7px; font-size: 11px; font-weight: 700;
  text-decoration: none; transition: opacity .15s;
}}
.ext-link:hover {{ opacity: .85; }}
.gmap-link {{ background: #34A853; color: #fff; }}
.osm-link  {{ background: #7EBC12; color: #fff; }}

#loading {{
  display: flex; align-items: center; gap: 10px;
  background: #fff; border-radius: 10px; padding: 14px;
  font-size: 13px; color: #555; border: 1px solid #e5e9f0;
}}
.spinner {{
  width: 18px; height: 18px; border: 3px solid #e5e9f0;
  border-top-color: {color}; border-radius: 50%;
  animation: spin .8s linear infinite; flex-shrink: 0;
}}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
</style>
</head>
<body>

<div id="layout">
  <div id="map"></div>
  <div id="sidebar">
    <div id="status-bar">
      {icon_ch} {label}
      <span id="status-count" style="margin-left:auto;">Chargement…</span>
    </div>
    <div id="list">
      <div id="loading">
        <div class="spinner"></div>
        Interrogation OpenStreetMap…
      </div>
    </div>
    <div id="links-row">
      <a class="ext-link gmap-link" href="{gmap_url}" target="_blank">🗺️ Google Maps</a>
      <a class="ext-link osm-link"
         href="https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=14/{lat}/{lon}"
         target="_blank">🌍 OpenStreetMap</a>
    </div>
  </div>
</div>

<script>
(function() {{
  const LAT = {lat}, LON = {lon};
  const COLOR = '{color}';
  const ICON_CHAR = '{icon_ch}';
  const QUERY = {repr(overpass_query)};

  // ── Carte Leaflet ──────────────────────────────────────────────────
  const map = L.map('map').setView([LAT, LON], 13);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>',
    maxZoom: 19
  }}).addTo(map);

  // Marqueur position
  const selfIcon = L.divIcon({{
    html: `<div style="background:#E53935;width:20px;height:20px;border-radius:50%;
           border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.4);
           display:flex;align-items:center;justify-content:center;font-size:10px;">📍</div>`,
    className:'', iconSize:[20,20], iconAnchor:[10,10]
  }});
  L.marker([LAT, LON], {{icon: selfIcon}})
   .addTo(map)
   .bindPopup('<b>📍 Ma position</b>');

  // Cercle de rayon
  L.circle([LAT, LON], {{
    radius: {radius_m}, color: COLOR, fillColor: COLOR,
    fillOpacity: 0.04, weight: 1.5, dashArray: '6,4'
  }}).addTo(map);

  // ── Helpers ────────────────────────────────────────────────────────
  function haversine(la1, lo1, la2, lo2) {{
    const R = 6371000, toR = Math.PI/180;
    const dLat = (la2-la1)*toR, dLon = (lo2-lo1)*toR;
    const a = Math.sin(dLat/2)**2 + Math.cos(la1*toR)*Math.cos(la2*toR)*Math.sin(dLon/2)**2;
    return Math.round(R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a)));
  }}

  function fmtDist(m) {{
    return m < 1000 ? m + ' m' : (m/1000).toFixed(1) + ' km';
  }}

  function makePoiIcon(ch, col) {{
    return L.divIcon({{
      html: `<div style="background:${{col}};color:#fff;border-radius:8px;
             padding:3px 5px;font-size:16px;border:2px solid #fff;
             box-shadow:0 2px 6px rgba(0,0,0,.35);white-space:nowrap;">${{ch}}</div>`,
      className:'', iconSize:[32,30], iconAnchor:[16,28]
    }});
  }}

  // ── Requête Overpass ───────────────────────────────────────────────
  const markers = [];
  let activeIdx = -1;

  function highlightCard(idx) {{
    document.querySelectorAll('.poi-card').forEach((c,i) => {{
      c.classList.toggle('active', i === idx);
    }});
    activeIdx = idx;
  }}

  fetch('https://overpass-api.de/api/interpreter', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
    body: 'data=' + encodeURIComponent(QUERY)
  }})
  .then(r => r.json())
  .then(data => {{
    const els = data.elements || [];
    const pois = [];

    els.forEach(el => {{
      const tags = el.tags || {{}};
      const name = tags.name || tags.brand || tags.operator || tags.amenity || tags.shop || tags.tourism || ICON_CHAR;
      let lat_, lon_;
      if (el.type === 'node') {{ lat_ = el.lat; lon_ = el.lon; }}
      else if (el.center) {{ lat_ = el.center.lat; lon_ = el.center.lon; }}
      else return;

      const dist = haversine(LAT, LON, lat_, lon_);

      // Infos enrichies
      const phone    = tags.phone || tags['contact:phone'] || '';
      const website  = tags.website || tags['contact:website'] || tags.url || '';
      const hours    = tags.opening_hours || '';
      const addr     = [tags['addr:housenumber'], tags['addr:street'], tags['addr:city']]
                       .filter(Boolean).join(' ');

      pois.push({{ name, lat: lat_, lon: lon_, dist, phone, website, hours, addr, tags }});
    }});

    // Trier par distance
    pois.sort((a,b) => a.dist - b.dist);
    const shown = pois.slice(0, 50);

    // Mettre à jour compteur
    const count = document.getElementById('status-count');
    if (count) count.textContent = shown.length + ' résultat' + (shown.length > 1 ? 's' : '');

    // Vider le loading
    const list = document.getElementById('list');
    list.innerHTML = '';

    if (shown.length === 0) {{
      list.innerHTML = '<div style="padding:14px;color:#888;font-size:13px;">Aucun résultat dans ce rayon. Essaie d\'élargir la zone.</div>';
      return;
    }}

    const poiIcon = makePoiIcon(ICON_CHAR, COLOR);
    const bounds = [[LAT, LON]];

    shown.forEach((p, idx) => {{
      // Marqueur
      const m = L.marker([p.lat, p.lon], {{icon: poiIcon}}).addTo(map);
      const popupContent = `
        <div style="min-width:180px;font-family:system-ui;">
          <b style="font-size:13px;">${{p.name}}</b><br>
          <span style="font-size:11px;color:#888;">${{fmtDist(p.dist)}}</span>
          ${{p.addr ? '<br><span style="font-size:11px;">📍 '+p.addr+'</span>' : ''}}
          ${{p.hours ? '<br><span style="font-size:11px;">🕐 '+p.hours+'</span>' : ''}}
          ${{p.phone ? '<br><a href="tel:'+p.phone+'" style="font-size:11px;">📞 '+p.phone+'</a>' : ''}}
          ${{p.website ? '<br><a href="'+p.website+'" target="_blank" style="font-size:11px;color:'+COLOR+';">🌐 Site web</a>' : ''}}
        </div>
      `;
      m.bindPopup(popupContent);
      markers.push(m);
      bounds.push([p.lat, p.lon]);

      // Carte cliquée → highlight liste
      m.on('click', () => {{
        highlightCard(idx);
        const cards = document.querySelectorAll('.poi-card');
        if (cards[idx]) cards[idx].scrollIntoView({{behavior:'smooth',block:'nearest'}});
      }});

      // Carte POI dans la liste
      const detailLines = [];
      if (p.hours) detailLines.push('🕐 ' + p.hours);
      if (p.addr)  detailLines.push('📍 ' + p.addr);
      if (p.phone) detailLines.push('<a href="tel:'+p.phone+'">📞 '+p.phone+'</a>');
      if (p.website) detailLines.push('<a href="'+p.website+'" target="_blank">🌐 Site web</a>');

      const card = document.createElement('div');
      card.className = 'poi-card';
      card.innerHTML = `
        <div class="poi-name">${{ICON_CHAR}} ${{p.name}}</div>
        <div class="poi-dist">📏 ${{fmtDist(p.dist)}}</div>
        ${{detailLines.length ? '<div class="poi-detail">'+detailLines.join(' · ')+'</div>' : ''}}
      `;
      card.addEventListener('click', () => {{
        map.setView([p.lat, p.lon], 16);
        markers[idx].openPopup();
        highlightCard(idx);
      }});
      list.appendChild(card);
    }});

    // Ajuster la vue
    if (bounds.length > 1) {{
      map.fitBounds(L.latLngBounds(bounds).pad(0.15));
    }}
  }})
  .catch(err => {{
    const list = document.getElementById('list');
    list.innerHTML = '<div style="padding:14px;color:#c00;font-size:12px;">Erreur Overpass : ' + err.message + '<br>Vérifie ta connexion internet.</div>';
    const count = document.getElementById('status-count');
    if (count) count.textContent = 'Erreur';
  }});
}})();
</script>
</body>
</html>
    """, height=560, scrolling=False)
