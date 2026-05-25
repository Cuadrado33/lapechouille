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
    """
    Widget photo qui stocke les bytes dans session_state pour survivre au rerun.
    Retourne un BytesIO avec .name si une photo est disponible, None sinon.
    """
    import io
    st.markdown(f"**{title}**")
    col_camera, col_upload = st.columns(2)
    with col_camera:
        camera = st.camera_input("📸 Prendre", key=f"{prefix}_camera")
    with col_upload:
        uploaded = st.file_uploader("📁 Importer", type=["jpg","jpeg","png","webp"],
                                     key=f"{prefix}_uploader")

    src = uploaded if uploaded is not None else camera
    if src is not None:
        st.session_state[f"{prefix}_bytes"] = src.getvalue()
        st.session_state[f"{prefix}_fname"] = getattr(src, "name", "photo.jpg")

    b = st.session_state.get(f"{prefix}_bytes")
    if not b:
        return None

    # Aperçu miniature
    import base64 as _b64
    fname = st.session_state.get(f"{prefix}_fname", "photo.jpg")
    ext   = fname.rsplit(".", 1)[-1].lower()
    mime  = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
    b64   = _b64.b64encode(b).decode()
    import streamlit.components.v1 as _cv1
    _cv1.html(
        f'<img src="data:{mime};base64,{b64}" '
        f'style="max-height:80px;border-radius:6px;margin:4px 0;">',
        height=90, scrolling=False,
    )

    f = io.BytesIO(b)
    f.name = fname
    return f


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
    # Hash unique des coordonnées pour forcer Streamlit ET le navigateur à régénérer l'iframe
    coord_key = f"{latitude:.6f}_{longitude:.6f}"
    coord_hash = coord_key.replace(".", "").replace("-", "n")
    # Cache-bust : ajout d'un param dans l'URL Google Maps qui change selon les coords
    iframe = f"https://maps.google.com/maps?q={latitude},{longitude}&z=14&output=embed&_k={coord_hash}"
    # Wrapper div avec id unique → Streamlit voit que c'est un nouveau composant
    html = (
        f'<div id="map_wrapper_{coord_hash}">'
        f'<iframe key="{coord_hash}" width="100%" height="{height}" frameborder="0" '
        f'src="{iframe}" style="border-radius:12px;border:none;"></iframe>'
        f'</div>'
        f'<!-- coords: {coord_key} -->'  # Commentaire HTML change le hash de components.html
    )
    components.html(html, height=height + 20)
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


def render_profile_banner() -> None:
    """Bandeau bleu de profil affiché en haut de chaque page si connecté."""
    user = st.session_state.get("reseau_user")
    if not user:
        return
    try:
        from core.database import load_profil
        from core.utils import safe_str
        profil = load_profil() or {}
        pseudo     = safe_str(profil.get("pseudo")) or user.get("pseudo","Pêcheur")
        niveau     = safe_str(profil.get("niveau")) or ""
        zone       = safe_str(profil.get("zone_peche_principale")) or ""
        photo      = safe_str(profil.get("photo_path")) or ""

        # Réseaux sociaux
        rs_links = []
        rs_map = {
            "social_instagram": ("Instagram", "#E1306C",
                '<svg viewBox="0 0 24 24" width="16" height="16" fill="#fff"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>'),
            "social_facebook": ("Facebook", "#1877F2",
                '<svg viewBox="0 0 24 24" width="16" height="16" fill="#fff"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>'),
            "social_youtube": ("YouTube", "#FF0000",
                '<svg viewBox="0 0 24 24" width="16" height="16" fill="#fff"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>'),
            "social_tiktok": ("TikTok", "#010101",
                '<svg viewBox="0 0 24 24" width="16" height="16" fill="#fff"><path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z"/></svg>'),
        }
        for key, (label, color, svg) in rs_map.items():
            url = safe_str(profil.get(key))
            if url and url.startswith("http"):
                rs_links.append(
                    f'<a href="{url}" target="_blank" style="display:inline-flex;'
                    f'align-items:center;justify-content:center;width:26px;height:26px;'
                    f'border-radius:50%;background:{color};text-decoration:none;'
                    f'margin-left:4px;" title="{label}">{svg}</a>'
                )

        # Photo ronde
        if photo and photo.startswith("http"):
            photo_html = (f'<img src="{photo}" style="width:40px;height:40px;'
                          f'border-radius:50%;object-fit:cover;border:2px solid rgba(255,255,255,.4);">')
        else:
            photo_html = '<div style="width:40px;height:40px;border-radius:50%;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;font-size:18px;">🎣</div>'

        annees     = safe_str(profil.get("annees_peche")) or ""
        esp_pref   = safe_str(profil.get("espece_preferee")) or ""

        # Poisson record depuis les captures
        record_txt = ""
        try:
            from core.database import load_captures
            import pandas as pd
            caps = load_captures()
            if not caps.empty and "taille_cm" in caps.columns:
                tt = pd.to_numeric(caps["taille_cm"], errors="coerce").dropna()
                if not tt.empty:
                    best = float(tt.max())
                    best_row = caps.loc[caps["taille_cm"].astype(float) == best].iloc[0]
                    esp_rec  = safe_str(best_row.get("espece")) or ""
                    record_txt = f"🏆 {esp_rec} {int(best)} cm" if esp_rec else f"🏆 {int(best)} cm"
        except Exception:
            pass

        rs_html = "".join(rs_links)

        # Ligne d'infos
        infos = []
        if niveau:   infos.append(f"<b>{niveau}</b>")
        if annees:   infos.append(f"🎣 {annees} ans")
        if zone:     infos.append(f"📍 {zone}")
        if record_txt: infos.append(record_txt)
        infos_html = "  ·  ".join(infos)

        st.markdown(
            f'<div style="background:linear-gradient(135deg,#0c2340,#1565C0);'
            f'color:#fff;border-radius:10px;padding:10px 16px;margin-bottom:12px;'
            f'display:flex;align-items:center;gap:12px;flex-wrap:wrap;">'
            f'{photo_html}'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="font-size:14px;font-weight:800;">{pseudo}</div>'
            f'<div style="font-size:11px;opacity:.85;margin-top:2px;">{infos_html}</div>'
            f'</div>'
            f'<div style="display:flex;align-items:center;gap:4px;">{rs_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    except Exception:
        pass


def share_button(text: str, key: str, label: str = "📤 Partager") -> None:
    """
    Affiche un bouton de partage avec menu WhatsApp / SMS / Email / Copier.
    `text` est le contenu à partager.
    """
    import urllib.parse
    encoded = urllib.parse.quote(text)
    wa_url   = f"https://wa.me/?text={encoded}"
    sms_url  = f"sms:?body={encoded}"
    mail_url = f"mailto:?body={encoded}"
    fb_url   = f"https://www.facebook.com/sharer/sharer.php?u=https%3A%2F%2Flapechouille.fr&quote={encoded}"

    sid = key.replace("-","_")
    import streamlit.components.v1 as _cv
    _cv.html(f"""
<style>
.sh-wrap-{sid} {{ margin:8px 0; }}
.sh-grid-{sid} {{ display:grid;grid-template-columns:repeat(5,1fr);gap:6px; }}
.sh-btn-{sid} {{
  display:flex;align-items:center;justify-content:center;gap:4px;
  padding:8px 6px;border-radius:8px;font-size:11px;font-weight:700;
  text-decoration:none;cursor:pointer;border:none;color:#fff;
}}
.sh-btn-{sid}:hover {{ opacity:.85; }}
.sh-cp-{sid}  {{ background:#1565C0; }}
.sh-wa-{sid}  {{ background:#25D366; }}
.sh-sms-{sid} {{ background:#007AFF; }}
.sh-ml-{sid}  {{ background:#EA4335; }}
.sh-fb-{sid}  {{ background:#1877F2; }}
.sh-ok-{sid}  {{ display:none;font-size:10px;color:#2E7D32;margin-left:6px; }}
</style>
<div class="sh-wrap-{sid}">
  <div class="sh-grid-{sid}">
    <button class="sh-btn-{sid} sh-cp-{sid}" onclick="shCopy_{sid}()">📋 Copier
      <span class="sh-ok-{sid}" id="shok_{sid}">✓</span></button>
    <a class="sh-btn-{sid} sh-wa-{sid}"  href="{wa_url}"   target="_blank">💬 WhatsApp</a>
    <a class="sh-btn-{sid} sh-sms-{sid}" href="{sms_url}">📱 SMS</a>
    <a class="sh-btn-{sid} sh-ml-{sid}"  href="{mail_url}">✉️ Email</a>
    <a class="sh-btn-{sid} sh-fb-{sid}"  href="{fb_url}"   target="_blank">👥 FB</a>
  </div>
</div>
<script>
function shCopy_{sid}(){{
  if(navigator.clipboard){{
    navigator.clipboard.writeText({repr(text)}).then(function(){{
      var e=document.getElementById('shok_{sid}');
      if(e){{e.style.display='inline';setTimeout(()=>e.style.display='none',2000);}}
    }});
  }}
}}
</script>
""", height=70, scrolling=False)


# ═══════════════════════════════════════════════════════════════════
#  Bouton de partage étendu — Réseau La Péchouille + RS externes
# ═══════════════════════════════════════════════════════════════════

def share_button_v2(
    item_type:   str,                # 'capture'|'session'|'materiel'|'spot'|'spot_appat'
    item_id:     int,
    item_label:  str,                # affichage : "Bar 52cm"
    text_external: str,              # texte pour partage WhatsApp/SMS
    metadata:    dict | None = None, # données structurées du post
    photo_url:   str = "",
    key:         str = "",
    is_spot:     bool = False,       # pour afficher l'option spot_precision
) -> None:
    """
    Bouton de partage étendu avec :
    - Onglet Réseau La Péchouille (avec visibilité + autorisation repartage + choix des infos)
    - Onglet Réseaux externes (WhatsApp, SMS, Email, FB, Copier)
    """
    import streamlit as st
    from core.social import share_to_reseau

    if not key:
        key = f"{item_type}_{item_id}"

    metadata = metadata or {}

    tab_reseau, tab_externes = st.tabs(["🌊 Réseau La Péchouille", "🔗 Réseaux externes"])

    # ── Onglet Réseau ─────────────────────────────────────────────
    with tab_reseau:
        if not st.session_state.get("reseau_user"):
            st.info("👤 Connecte-toi pour publier sur le Réseau.")
        else:
            # Champs sélectionnables selon le type d'item
            # Liste de tuples (clé_metadata, label_affiché, icone)
            FIELD_OPTIONS = {
                "capture": [
                    ("espece",    "Espèce",         "🐟"),
                    ("taille_cm", "Taille",         "📏"),
                    ("poids_g",   "Poids",          "⚖️"),
                    ("lieu",      "Lieu",           "📍"),
                    ("heure",     "Heure",          "🕐"),
                    ("appat",     "Appât",          "🪱"),
                    ("montage",   "Montage",        "🧵"),
                    ("canne",     "Canne",          "🎯"),
                    ("moulinet",  "Moulinet",       "⚙️"),
                    ("hamecon",   "Hameçon",        "🪝"),
                    ("distance",  "Distance lancer","📐"),
                ],
                "session": [
                    ("lieu",     "Lieu",            "📍"),
                    ("date",     "Date",            "📅"),
                    ("type",     "Type session",    "🎯"),
                    ("nb_caps",  "Nb captures",     "🐟"),
                    ("best",     "Meilleure taille","📏"),
                    ("meteo",    "Météo",           "🌦️"),
                    ("maree",    "Marée/Coef",      "🌊"),
                ],
                "materiel": [
                    ("marque",     "Marque",        "🏷️"),
                    ("modele",     "Modèle",        "📋"),
                    ("longueur",   "Longueur",      "📏"),
                    ("puissance",  "Puissance",     "⚡"),
                    ("etat",       "État",          "✨"),
                ],
                "spot": [
                    ("nom",        "Nom du spot",   "📍"),
                    ("type_spot",  "Type",          "🏖️"),
                    ("commentaire","Commentaire",   "💬"),
                ],
                "spot_appat": [
                    ("nom",        "Nom du spot",   "📍"),
                    ("appat",      "Appât",         "🪱"),
                    ("commentaire","Commentaire",   "💬"),
                ],
            }

            available_fields = FIELD_OPTIONS.get(item_type, [])
            # Ne montrer que les champs qui ont une valeur dans metadata
            visible_fields = [
                (k, lbl, icn) for (k, lbl, icn) in available_fields
                if metadata.get(k) not in (None, "", 0, 0.0)
            ]

            with st.form(f"share_reseau_{key}", clear_on_submit=False):
                msg = st.text_area(
                    "Ajoute un mot (optionnel)",
                    key=f"share_msg_{key}",
                    placeholder=f"Partage ton expérience sur {item_label}...",
                    height=80,
                )

                # Sélection des champs à inclure
                selected_fields = []
                if visible_fields:
                    st.markdown("**📋 Informations à publier**")
                    n_cols = min(3, len(visible_fields))
                    cols = st.columns(n_cols)
                    for i, (fk, flbl, ficn) in enumerate(visible_fields):
                        with cols[i % n_cols]:
                            checked = st.checkbox(
                                f"{ficn} {flbl}",
                                value=True,
                                key=f"share_field_{key}_{fk}",
                            )
                            if checked:
                                selected_fields.append(fk)

                col_v, col_r = st.columns(2)
                with col_v:
                    visibility = st.selectbox(
                        "👁️ Visibilité",
                        ["public", "amis", "prive"],
                        format_func=lambda x: {
                            "public": "🌍 Public",
                            "amis":   "👥 Amis seulement",
                            "prive":  "🔒 Privé (note perso)",
                        }[x],
                        key=f"share_vis_{key}",
                    )
                with col_r:
                    allow_reshare = st.checkbox(
                        "🔄 Autoriser le repartage",
                        value=True,
                        key=f"share_resh_{key}",
                    )

                spot_precision = None
                if is_spot:
                    spot_precision = st.radio(
                        "📍 Précision de la localisation",
                        ["exact", "localite"],
                        format_func=lambda x: {
                            "exact":    "📌 Adresse exacte (GPS)",
                            "localite": "🏘️ Localité étendue (ville/zone)",
                        }[x],
                        index=1,
                        key=f"share_prec_{key}",
                        horizontal=True,
                    )

                if st.form_submit_button("✅ Publier sur le Réseau",
                                           use_container_width=True, type="primary"):
                    # Filtrer metadata aux champs sélectionnés uniquement
                    filtered_meta = {k: v for k, v in metadata.items() if k in selected_fields}

                    post = share_to_reseau(
                        type_post=item_type,
                        ref_id=item_id,
                        contenu=msg,
                        metadata=filtered_meta,
                        photo_url=photo_url,
                        visibility=visibility,
                        allow_reshare=allow_reshare,
                        spot_precision=spot_precision,
                    )
                    if post:
                        st.success("🎉 Publié sur le Réseau !")
                        fish_animation()
                    # le message d'erreur est déjà affiché par share_to_reseau

    # ── Onglet Réseaux externes ───────────────────────────────────
    with tab_externes:
        share_button(text_external, key=f"ext_{key}", label="Partager")


# ═══════════════════════════════════════════════════════════════════
#  Animation poissons qui montent (remplace st.balloons)
# ═══════════════════════════════════════════════════════════════════

def fish_animation() -> None:
    """Lance une animation de poissons qui montent (façon balloons)."""
    import streamlit.components.v1 as _comp
    import random, time
    # Clé unique pour éviter la mise en cache
    nonce = int(time.time() * 1000)

    fishes = ["🐟", "🐠", "🐡", "🎣", "🦈"]
    items_html = ""
    for i in range(40):
        emoji = random.choice(fishes)
        left  = random.randint(0, 95)
        delay = random.uniform(0, 1.5)
        dur   = random.uniform(3, 5)
        size  = random.randint(28, 50)
        items_html += (
            f'<div class="fish-{nonce}" style="left:{left}%;'
            f'animation-delay:{delay:.2f}s;'
            f'animation-duration:{dur:.2f}s;'
            f'font-size:{size}px;">{emoji}</div>'
        )

    _comp.html(f"""
<style>
  .fish-container-{nonce} {{
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none;
    overflow: hidden;
    z-index: 99999;
  }}
  .fish-{nonce} {{
    position: absolute;
    bottom: -60px;
    animation-name: float-up-{nonce};
    animation-timing-function: ease-out;
    animation-fill-mode: forwards;
    will-change: transform;
  }}
  @keyframes float-up-{nonce} {{
    0%   {{ transform: translateY(0) rotate(0deg);     opacity: 1; }}
    50%  {{ transform: translateY(-50vh) rotate(15deg); opacity: 1; }}
    100% {{ transform: translateY(-120vh) rotate(-15deg); opacity: 0; }}
  }}
</style>
<div class="fish-container-{nonce}">{items_html}</div>
""", height=0, scrolling=False)
