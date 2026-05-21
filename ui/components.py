"""Composants d'interface réutilisables — tout en Streamlit natif."""
from __future__ import annotations
from typing import Iterable, Optional
import streamlit as st
import streamlit.components.v1 as components


# ---------------------------------------------------------------------------
# Hero & sections
# ---------------------------------------------------------------------------

def hero(kicker: str, title: str, subtitle: str = "") -> None:
    st.caption(kicker.upper())
    st.title(title)
    if subtitle:
        st.markdown(subtitle)


def section(title: str, subtitle: str = "", icon: str = "", anchor_id: str = "") -> None:
    if anchor_id:
        st.markdown(
            f'<div id="{anchor_id}" style="position:relative;top:-80px;visibility:hidden;"></div>',
            unsafe_allow_html=True,
        )
    header = f"{icon} {title}" if icon else title
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        f'color:#fff;padding:8px 14px;border-radius:8px;margin:12px 0 8px;">'
        f'<span style="font-size:14px;font-weight:800;">{header}</span>'
        + (f'<div style="font-size:11px;opacity:.85;margin-top:2px;">{subtitle}</div>' if subtitle else '') +
        f'</div>',
        unsafe_allow_html=True,
    )


def scroll_to_anchor(anchor_id: str) -> None:
    """
    Scroll vers une section de la page conditions.
    Utilise window.parent.document pour accéder au DOM Streamlit depuis l'iframe components.html.
    Retry agressif car le DOM peut mettre du temps à se construire après un rerun.
    """
    if not anchor_id:
        return
    components.html(
        f"""
        <script>
        (function() {{
            var TARGET = '{anchor_id}';
            var attempts = 0;
            var maxAttempts = 20;

            function doScroll() {{
                attempts++;
                try {{
                    var doc = window.parent.document;
                    var el = doc.getElementById(TARGET);
                    if (el) {{
                        // Scroll natif
                        el.scrollIntoView({{behavior: 'smooth', block: 'start'}});
                        // Léger offset vers le bas pour compenser le header Streamlit
                        setTimeout(function() {{
                            window.parent.scrollBy({{top: -80, behavior: 'smooth'}});
                        }}, 400);
                        return; // succès
                    }}
                }} catch(e) {{}}

                if (attempts < maxAttempts) {{
                    setTimeout(doScroll, 200);
                }}
            }}

            // Premier essai après 500ms pour laisser le DOM se construire
            setTimeout(doScroll, 500);
        }})();
        </script>
        """,
        height=0,
        scrolling=False,
    )


# ---------------------------------------------------------------------------
# Métriques
# ---------------------------------------------------------------------------

def metric_grid(items: Iterable[dict]) -> None:
    items_list = list(items)
    if not items_list:
        return
    cols = st.columns(len(items_list))
    for col, item in zip(cols, items_list):
        with col:
            with st.container(border=True):
                st.metric(label=f"{item.get('icon','')} {item.get('label','')}", value=item.get("value","—"))
                if item.get("sub"):
                    st.caption(item["sub"])


def status_card(title: str, icon: str, main: str, sub: str = "") -> None:
    with st.container(border=True):
        st.markdown(f"**{icon} {title}**")
        st.markdown(f"### {main}")
        if sub:
            st.caption(sub)


# ---------------------------------------------------------------------------
# Confirmation destructive
# ---------------------------------------------------------------------------

def confirm_destructive(key: str, message: str) -> bool:
    st.warning(message)
    col_yes, col_no = st.columns(2)
    confirmed = col_yes.button("🗑️ OUI — Supprimer", key=f"confirm_yes_{key}", use_container_width=True)
    cancelled = col_no.button("↩️ Annuler", key=f"confirm_no_{key}", use_container_width=True)
    if cancelled:
        st.session_state[f"confirm_{key}"] = False
        st.rerun()
    return confirmed


# ---------------------------------------------------------------------------
# Photo helpers
# ---------------------------------------------------------------------------

def photo_placeholder(label: str = "Aucune photo") -> None:
    st.info(label)


def photo_inputs(prefix: str, title: str = "Photo") -> Optional[object]:
    st.markdown(f"**{title}**")
    col_camera, col_upload = st.columns(2)
    with col_camera:
        camera = st.camera_input("📸 Prendre une photo", key=f"{prefix}_camera")
    with col_upload:
        uploaded = st.file_uploader("📁 Importer", type=["jpg","jpeg","png","webp"],
                                     key=f"{prefix}_uploader")
    return uploaded if uploaded is not None else camera


# ---------------------------------------------------------------------------
# Localisation partagée — recherche live + carte cliquable
# ---------------------------------------------------------------------------

def location_picker(prefix: str, default_lat: float = 44.656588,
                    default_lon: float = -1.196303,
                    spots_shortcut: bool = True):
    """
    Localisation complète pour Nouveau spot (GPS + adresse + carte + manuel).
    Retourne (lat, lon) stables via session_state.
    """
    from core.external_apis import geocode_candidates
    try:
        from streamlit_js_eval import get_geolocation
    except ImportError:
        get_geolocation = None

    # ── Spot actif (raccourci sessions) ─────────────────────────────
    if spots_shortcut:
        try:
            from core.database import load_spots
            spots_df = load_spots()
            if not spots_df.empty:
                active_nom = st.session_state.get("active_spot_nom")
                if active_nom and active_nom in spots_df["nom"].values:
                    row = spots_df[spots_df["nom"] == active_nom].iloc[0]
                    lat, lon = float(row["latitude"]), float(row["longitude"])
                    st.success(f"⭐ **{active_nom}** — {lat:.5f}, {lon:.5f}")
                    if st.button("🔄 Changer", key=f"{prefix}_spot_change", type="primary"):
                        st.session_state.pop("active_spot_nom", None)
                        st.rerun()
                    return lat, lon
                names = ["— Choisir un spot enregistré —"] + spots_df["nom"].tolist()
                chosen = st.selectbox("⭐ Utiliser un spot enregistré", names, key=f"{prefix}_spot_quick")
                if chosen != "— Choisir un spot enregistré —":
                    row = spots_df[spots_df["nom"] == chosen].iloc[0]
                    lat, lon = float(row["latitude"]), float(row["longitude"])
                    st.session_state["active_spot_lat"] = lat
                    st.session_state["active_spot_lon"] = lon
                    st.session_state["active_spot_nom"] = chosen
                    st.success(f"📍 {chosen} — {lat:.5f}, {lon:.5f}")
                    return lat, lon
        except Exception:
            pass

    lat_key = f"{prefix}_lat_stored"
    lon_key = f"{prefix}_lon_stored"
    if lat_key not in st.session_state or st.session_state.get(lat_key) is None:
        # Utiliser le spot actif comme valeur initiale si disponible
        active_lat = st.session_state.get("active_spot_lat")
        active_lon = st.session_state.get("active_spot_lon")
        st.session_state[lat_key] = float(active_lat) if active_lat else default_lat
        st.session_state[lon_key] = float(active_lon) if active_lon else default_lon
    if lon_key not in st.session_state or st.session_state.get(lon_key) is None:
        active_lon = st.session_state.get("active_spot_lon")
        st.session_state[lon_key] = float(active_lon) if active_lon else default_lon

    mode = st.radio(
        "Mode de localisation",
        ["📍 GPS auto", "🔎 Recherche adresse", "✏️ Coordonnées manuelles"],
        horizontal=True,
        key=f"{prefix}_mode",
    )

    # ── GPS auto ─────────────────────────────────────────────────────
    if mode == "📍 GPS auto":
        if get_geolocation is None:
            st.warning("`streamlit-js-eval` non installé.")
        else:
            gps_lat_k = f"{prefix}_gps_lat"
            gps_lon_k = f"{prefix}_gps_lon"
            try:
                loc = get_geolocation(component_key=f"{prefix}_geoloc")
            except TypeError:
                loc = get_geolocation()
            if loc:
                coords = loc.get("coords", {})
                glat = coords.get("latitude")
                glon = coords.get("longitude")
                if glat and glon:
                    st.session_state[gps_lat_k] = float(glat)
                    st.session_state[gps_lon_k] = float(glon)
            clat = st.session_state.get(gps_lat_k)
            clon = st.session_state.get(gps_lon_k)
            if clat and clon:
                st.success(f"📍 GPS — {clat:.5f}, {clon:.5f}")
                if st.button("✅ Utiliser cette position", key=f"{prefix}_gps_ok", type="primary"):
                    st.session_state[lat_key] = float(clat)
                    st.session_state[lon_key] = float(clon)
                    st.rerun()
                if st.button("🔄 Actualiser", key=f"{prefix}_gps_refresh"):
                    st.session_state.pop(gps_lat_k, None)
                    st.session_state.pop(gps_lon_k, None)
                    st.rerun()
            else:
                st.info("⏳ En attente du GPS… Autorise la géolocalisation dans le navigateur.")

    # ── Recherche adresse ────────────────────────────────────────────
    elif mode == "🔎 Recherche adresse":
        def _search():
            q = st.session_state.get(f"{prefix}_addr_q", "").strip()
            st.session_state[f"{prefix}_addr_res"] = geocode_candidates(q, limit=6) if len(q) >= 3 else []
        st.text_input("🔎 Adresse, plage, ville…",
                       placeholder="Ex : Plage de la Salie, Capbreton…",
                       key=f"{prefix}_addr_q", on_change=_search)
        results = st.session_state.get(f"{prefix}_addr_res", [])
        if results:
            labels = [r["display_name"] for r in results]
            idx = st.selectbox("Choisir :", range(len(labels)),
                                format_func=lambda i: labels[i], key=f"{prefix}_addr_sel")
            clat, clon = float(results[idx]["latitude"]), float(results[idx]["longitude"])
            if st.button("✅ Valider cette adresse", key=f"{prefix}_addr_ok",
                          use_container_width=True, type="primary"):
                st.session_state[lat_key] = clat
                st.session_state[lon_key] = clon
                st.rerun()
            st.caption(f"Sélectionné : {clat:.5f}, {clon:.5f}")
        elif st.session_state.get(f"{prefix}_addr_q", ""):
            q = st.session_state[f"{prefix}_addr_q"].strip()
            st.warning("Aucun résultat.") if len(q) >= 3 else st.caption("3 caractères min…")

    # ── Coordonnées manuelles ────────────────────────────────────────
    else:
        clat = float(st.session_state[lat_key])
        clon = float(st.session_state[lon_key])
        st.caption("💡 Copie les coordonnées depuis Google Maps (clic droit → coordonnées).")
        c1, c2 = st.columns(2)
        lat_in = c1.number_input("Latitude",  value=clat, format="%.6f",
                                  step=0.0001, key=f"{prefix}_lat_input")
        lon_in = c2.number_input("Longitude", value=clon, format="%.6f",
                                  step=0.0001, key=f"{prefix}_lon_input")
        st.markdown(
            f'<a href="https://www.google.com/maps?q={lat_in},{lon_in}&z=14" '
            f'target="_blank" style="font-size:12px;">🗺️ Vérifier sur Google Maps</a>',
            unsafe_allow_html=True,
        )
        if st.button("✅ Valider ces coordonnées", key=f"{prefix}_manual_ok",
                      use_container_width=True, type="primary"):
            st.session_state[lat_key] = float(lat_in)
            st.session_state[lon_key] = float(lon_in)
            st.success(f"📍 {lat_in:.5f}, {lon_in:.5f}")
            st.rerun()

    st.caption(f"📍 Position : **{st.session_state[lat_key]:.5f}, {st.session_state[lon_key]:.5f}**")
    return float(st.session_state[lat_key]), float(st.session_state[lon_key])

def _return_confirmed(confirmed_lat, confirmed_lon, default_lat, default_lon):
    if confirmed_lat and confirmed_lon:
        return float(confirmed_lat), float(confirmed_lon)
    return float(default_lat), float(default_lon)


# ---------------------------------------------------------------------------
# Maps
# ---------------------------------------------------------------------------

def terrestrial_map(latitude: float, longitude: float, height: int = 320) -> None:
    iframe = f"https://maps.google.com/maps?q={latitude},{longitude}&z=14&output=embed"
    components.html(
        f'<iframe width="100%" height="{height}" frameborder="0" '
        f'src="{iframe}" style="border-radius:12px;"></iframe>',
        height=height + 20,
    )
    st.markdown(f"[🗺️ Ouvrir Google Maps](https://www.google.com/maps?q={latitude:.6f},{longitude:.6f})")


def maritime_map(latitude: float, longitude: float, height: int = 420) -> None:
    """
    Carte maritime Leaflet : fond OSM + balises OpenSeaMap + lien bathymétrie.
    """
    openseamap_url = f"https://map.openseamap.org/?zoom=12&lat={latitude}&lon={longitude}"
    components.html(f"""
        <div id="sf_maritime_{int(latitude*1000)}" style="width:100%;height:{height}px;border-radius:12px;overflow:hidden;"></div>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
        (function() {{
            const mapId = 'sf_maritime_{int(latitude*1000)}';
            const lat = {latitude};
            const lon = {longitude};

            const map = L.map(mapId, {{zoomControl: true}}).setView([lat, lon], 12);

            // Fond principal OpenStreetMap (fiable partout)
            const osm = L.tileLayer(
                'https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
                {{attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>', maxZoom: 19}}
            ).addTo(map);

            // Fond nautique Esri Ocean (profondeurs colorées, sans CORS)
            const esriOcean = L.tileLayer(
                'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{{z}}/{{y}}/{{x}}',
                {{attribution: '© Esri Ocean', maxZoom: 13}}
            );

            // Overlay référence Esri (isobathes, textes)
            const esriRef = L.tileLayer(
                'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{{z}}/{{y}}/{{x}}',
                {{attribution: '© Esri', maxZoom: 13}}
            );

            // Balises & feux OpenSeaMap (overlay)
            const seamarks = L.tileLayer(
                'https://tiles.openseamap.org/seamark/{{z}}/{{x}}/{{y}}.png',
                {{attribution: '© <a href="https://openseamap.org">OpenSeaMap</a>', maxZoom: 18, opacity: 1}}
            ).addTo(map);

            // Contrôle de couches
            L.control.layers(
                {{'🗺️ OpenStreetMap': osm, '🌊 Esri Océan (bathymétrie)': esriOcean}},
                {{'⚓ Balises / feux OpenSeaMap': seamarks, '📍 Références marines': esriRef}},
                {{collapsed: false, position: 'topright'}}
            ).addTo(map);

            // Marqueur du spot
            L.marker([lat, lon])
                .addTo(map)
                .bindPopup('<b>📍 Mon spot</b>')
                .openPopup();
        }})();
        </script>
    """, height=height + 20)
    st.caption("⚓ Balises : OpenSeaMap · 🌊 Bathymétrie : Esri Ocean · Carte indicative — ne pas utiliser pour la navigation.")
    st.markdown(f"[⚓ Ouvrir OpenSeaMap en plein écran]({openseamap_url})")


def overpass_poi_map(latitude: float, longitude: float,
                     overpass_query: str, label: str,
                     color: str = "#0078FF", height: int = 400) -> None:
    """
    Carte Leaflet avec POIs récupérés depuis Overpass API.
    """
    import json, requests as _req
    radius_m = 15000
    ov_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:15];
    (
      {overpass_query.format(lat=latitude, lon=longitude, r=radius_m)}
    );
    out body;
    """
    pois = []
    try:
        resp = _req.post(ov_url, data=query, timeout=15)
        elements = resp.json().get("elements", [])
        for el in elements[:40]:
            tags = el.get("tags", {})
            name = (tags.get("name") or tags.get("brand") or
                    tags.get("operator") or label)
            if el.get("type") == "node":
                pois.append({"lat": el["lat"], "lon": el["lon"], "name": name})
            elif el.get("type") == "way" and el.get("center"):
                pois.append({"lat": el["center"]["lat"], "lon": el["center"]["lon"], "name": name})
    except Exception:
        pass

    pois_js = json.dumps(pois)
    maps_url = f"https://www.google.com/maps/search/?api=1&query={_req.utils.quote(label + ' ' + str(latitude) + ',' + str(longitude))}"

    components.html(
        f"""
        <div id="poi_map" style="width:100%;height:{height}px;border-radius:12px;"></div>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
        var map = L.map('poi_map').setView([{latitude},{longitude}], 12);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
            {{attribution:'© OpenStreetMap',maxZoom:19}}).addTo(map);

        var pois = {pois_js};
        var icon = L.divIcon({{
            html:'<div style="background:{color};width:14px;height:14px;border-radius:50%;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.5)"></div>',
            className:'', iconSize:[14,14], iconAnchor:[7,7]
        }});
        var meIcon = L.divIcon({{
            html:'<div style="background:#FF3B30;width:18px;height:18px;border-radius:50%;border:3px solid #fff;box-shadow:0 1px 6px rgba(0,0,0,.6)"></div>',
            className:'', iconSize:[18,18], iconAnchor:[9,9]
        }});

        L.marker([{latitude},{longitude}], {{icon:meIcon}})
            .bindPopup('<b>📍 Ma position</b>').addTo(map);

        pois.forEach(function(p) {{
            L.marker([p.lat,p.lon], {{icon:icon}})
                .bindPopup('<b>'+p.name+'</b>')
                .addTo(map);
        }});

        if (pois.length > 0) {{
            var group = L.featureGroup(pois.map(p => L.marker([p.lat,p.lon])));
            map.fitBounds(group.getBounds().pad(0.2));
        }}
        </script>
        """,
        height=height + 20,
    )
    if not pois:
        st.caption("Aucun résultat Overpass — essaie Google Maps ci-dessous.")
    else:
        st.caption(f"{len(pois)} lieu(x) trouvé(s) dans un rayon de 15 km")
    st.markdown(f"[🗺️ Ouvrir Google Maps]({maps_url})")


# ---------------------------------------------------------------------------
# Partage de localisation — avec carte + boutons harmonisés
# ---------------------------------------------------------------------------

def share_location_widget(latitude: float, longitude: float, nom: str = "") -> None:
    """Widget partage : grande carte Leaflet + adresse + coordonnées GPS + 6 boutons."""
    from urllib.parse import quote as _q

    lat6 = f"{latitude:.6f}"
    lon6 = f"{longitude:.6f}"
    nom_safe = nom.strip() or "Mon spot de pêche"
    gmap_url  = f"https://www.google.com/maps?q={lat6},{lon6}"
    msg_text  = f"{nom_safe} — {lat6}, {lon6} — {gmap_url}"
    map_id    = f"sw_{abs(hash(nom_safe + lat6)) % 999999}"

    wa_url   = f"https://wa.me/?text={_q(msg_text)}"
    sms_url  = f"sms:?body={_q(msg_text)}"
    mail_url = f"mailto:?subject={_q(nom_safe)}&body={_q(msg_text)}"
    fb_url   = f"https://www.facebook.com/sharer/sharer.php?u={_q(gmap_url)}&quote={_q(msg_text)}"
    nom_js   = nom_safe.replace("'", "\\'")

    # Reverse geocoding pour l'adresse
    try:
        from core.external_apis import reverse_geocode
        geo  = reverse_geocode(latitude, longitude) or {}
        addr = geo.get("address", {})
        parts = []
        place = (addr.get("beach") or addr.get("natural") or addr.get("amenity")
                 or addr.get("village") or addr.get("hamlet") or addr.get("suburb"))
        if place: parts.append(place)
        if addr.get("road"): parts.append(addr["road"])
        city = addr.get("town") or addr.get("city") or addr.get("municipality")
        if city and city not in parts: parts.append(city)
        if addr.get("postcode"): parts.append(addr["postcode"])
        addr_txt = ", ".join(p for p in parts if p) or geo.get("display_name", "")
    except Exception:
        addr_txt = ""

    components.html(f"""
<style>
.sw-wrap {{
  font-family:system-ui,sans-serif;background:#1a2332;
  border-radius:12px;padding:14px 14px 10px;margin:4px 0;
}}
.sw-title {{ color:#90CAF9;font-size:11px;font-weight:700;
  letter-spacing:1.2px;text-transform:uppercase;margin-bottom:8px; }}
.sw-map {{ width:100%;height:280px;border-radius:8px;overflow:hidden;margin-bottom:10px; }}
.sw-addr {{
  color:#fff;font-size:12px;font-weight:600;margin-bottom:4px;
  padding:6px 10px;background:rgba(255,255,255,.08);border-radius:6px;
}}
.sw-coords {{
  color:#90CAF9;font-size:11px;font-family:monospace;margin-bottom:10px;
  padding:4px 10px;background:rgba(255,255,255,.05);border-radius:6px;
}}
.sw-grid {{ display:grid;grid-template-columns:repeat(3,1fr);gap:7px; }}
.sw-btn {{
  display:flex;align-items:center;justify-content:center;gap:5px;
  padding:10px 4px;border-radius:8px;font-size:12px;font-weight:700;
  text-decoration:none;cursor:pointer;border:none;transition:opacity .15s;
  white-space:nowrap;
}}
.sw-btn:hover {{ opacity:.85; }}
.sw-copy {{ background:#fff;color:#1565C0; }}
.sw-wa   {{ background:#25D366;color:#fff; }}
.sw-sms  {{ background:#007AFF;color:#fff; }}
.sw-mail {{ background:#EA4335;color:#fff; }}
.sw-fb   {{ background:#1877F2;color:#fff; }}
.sw-maps {{ background:#34A853;color:#fff; }}
.sw-ok   {{ display:none;font-size:10px;margin-left:2px; }}
</style>
<div class="sw-wrap">
  <div class="sw-title">📤 Partager ce spot</div>
  <div class="sw-map" id="{map_id}"></div>
  {'<div class="sw-addr">📍 ' + addr_txt + '</div>' if addr_txt else ''}
  <div class="sw-coords">🛰️ {lat6}, {lon6}</div>
  <div class="sw-grid">
    <button class="sw-btn sw-copy" onclick="swCopy_{map_id}()">📋 Copier <span class="sw-ok" id="ok_{map_id}">✓</span></button>
    <a class="sw-btn sw-wa"   href="{wa_url}"   target="_blank">💬 WhatsApp</a>
    <a class="sw-btn sw-sms"  href="{sms_url}">📱 SMS</a>
    <a class="sw-btn sw-mail" href="{mail_url}">✉️ E-mail</a>
    <a class="sw-btn sw-fb"   href="{fb_url}"   target="_blank">👥 Facebook</a>
    <a class="sw-btn sw-maps" href="{gmap_url}" target="_blank">🗺️ Maps</a>
  </div>
</div>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
(function(){{
  var el = document.getElementById('{map_id}');
  if (!el || el._leaflet_id) return;
  var m = L.map(el,{{zoomControl:true,attributionControl:false}}).setView([{latitude},{longitude}],14);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(m);
  L.marker([{latitude},{longitude}]).addTo(m).bindPopup('<b>{nom_js}</b>').openPopup();
}})();
function swCopy_{map_id}(){{
  if(navigator.clipboard){{
    navigator.clipboard.writeText({repr(msg_text)}).then(function(){{
      var el=document.getElementById('ok_{map_id}');
      if(el){{el.style.display='inline';setTimeout(()=>el.style.display='none',2000);}}
    }});
  }}
}}
</script>
    """, height=490, scrolling=False)
