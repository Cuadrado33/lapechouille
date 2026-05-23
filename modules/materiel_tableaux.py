"""
Page « Références & tableaux » — identification des poissons, tableaux colorés Nylon/Tresse/Fluoro,
tailles minimales, quotas de prises.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from core.utils import line_resistance_interval, safe_str, safe_float, format_date_fr
from core.database import load_captures, load_sessions
from data.regulations import get_minimum_sizes_table, get_catch_limits_table
from data.fish_data import FISH_SVG
from ui.components import hero, section


def render() -> None:
    hero("Axe 3 · Matériel", "Références & tableaux",
         "Résistance des fils (Nylon, Tresse, Fluorocarbone), tailles minimales et quotas de prises.")

    tab_nylon, tab_tresse, tab_fluo, tab_tailles, tab_quotas, tab_records = st.tabs([
        "🔵 Nylon", "🟠 Tresse", "🟣 Fluorocarbone",
        "📏 Tailles autorisées", "🔢 Quotas de prises", "🏆 Mes records",
    ])

    with tab_nylon:
        section("Tableau de résistance — Nylon", icon="🔵")
        st.markdown("""
        > **Nylon monofilament** — fil classique, polyvalent, bonne élasticité (~25%).
        > Résistance réelle variable selon marque, âge, nœuds et abrasion (±15%).
        """)
        _render_colored_table("Nylon", header_color="#1E6FBD", row_colors=("#DBEAFE","#EFF6FF"))

    with tab_tresse:
        section("Tableau de résistance — Tresse", icon="🟠")
        st.markdown("""
        > **Tresse** — faible élasticité, diamètre réduit, résistance élevée.
        > Sensibilité supérieure. Résistance plus variable (±20%) selon le nombre de brins.
        """)
        _render_colored_table("Tresse", header_color="#C2410C", row_colors=("#FFEDD5","#FFF7ED"))

    with tab_fluo:
        section("Tableau de résistance — Fluorocarbone", icon="🟣")
        st.markdown("""
        > **Fluorocarbone** — quasi-invisible sous l'eau, dense (coule), résistance légèrement
        > inférieure au nylon (~90%). Idéal pour les empiles.
        """)
        _render_colored_table("Fluorocarbone", header_color="#7C3AED", row_colors=("#EDE9FE","#F5F3FF"))

    with tab_tailles:
        section("Tailles minimales par zone", icon="📏")
        st.caption("Valeurs indicatives — à vérifier avec les textes officiels en vigueur.")
        zone = st.selectbox("Zone / façade", [
            "Atlantique", "Manche / Atlantique", "Manche",
            "Manche / Mer du Nord", "Méditerranée",
        ], key="tab_zone_tailles")
        df = get_minimum_sizes_table(zone)
        srch = st.text_input("Filtrer", key="tab_srch_tailles")
        if srch:
            df = df[df["Espèce"].str.lower().str.contains(srch.lower(), na=False)]
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("📥 CSV", df.to_csv(index=False).encode("utf-8-sig"),
                           f"tailles_{zone.lower().replace(' ','_')}.csv", "text/csv")

    with tab_quotas:
        section("Quotas de prises par zone", icon="🔢")
        st.caption("Nombre de prises autorisées par jour — vérifier les arrêtés locaux.")
        zone_q = st.selectbox("Zone / façade", [
            "Atlantique", "Manche / Atlantique", "Manche",
            "Manche / Mer du Nord", "Méditerranée",
        ], key="tab_zone_quotas")
        df_q = get_catch_limits_table(zone_q)
        st.dataframe(df_q, use_container_width=True, hide_index=True)
        st.info("Données indicatives — source : mer.gouv.fr et textes réglementaires France. Toujours vérifier les arrêtés locaux avant de sortir.")

    with tab_records:
        _render_records()


def _build_resistance_df(fil_type: str) -> pd.DataFrame:
    rows = []
    for d in range(6, 101):
        diametre = f"{d}/100"
        interval = line_resistance_interval(fil_type, diametre)
        if interval:
            diam_mm = d / 100
            rows.append({
                "Diamètre (mm)": f"{diam_mm:.2f}",
                "Résistance min (kg)": interval[0],
                "Résistance max (kg)": interval[1],
                "Résistance moy (kg)": round((interval[0] + interval[1]) / 2, 1),
            })
    return pd.DataFrame(rows)


def _render_colored_table(fil_type: str, header_color: str, row_colors: tuple) -> None:
    df = _build_resistance_df(fil_type)
    if df.empty:
        st.info(f"Pas de données pour {fil_type}.")
        return

    plage = st.slider("Plage de diamètres (centièmes)", 6, 100, (10, 60),
                       key=f"res_slider_{fil_type}")
    df_f = df.iloc[plage[0] - 6: plage[1] - 5].copy()

    # Générer HTML coloré
    rows_html = ""
    for i, (_, row) in enumerate(df_f.iterrows()):
        bg = row_colors[i % 2]
        moy = float(row["Résistance moy (kg)"])
        # Barre de résistance proportionnelle (max 40 kg = 100%)
        bar_pct = min(int(moy / 40 * 100), 100)
        bar_color = header_color
        rows_html += f"""
        <tr style="background:{bg};">
          <td style="padding:6px 12px;font-weight:600;color:#1e293b;">{row['Diamètre (mm)']} mm</td>
          <td style="padding:6px 12px;text-align:center;">{row['Résistance min (kg)']} kg</td>
          <td style="padding:6px 12px;text-align:center;">
            <span style="font-weight:700;color:{header_color};">{row['Résistance moy (kg)']} kg</span>
            <div style="background:#e2e8f0;border-radius:4px;height:6px;margin-top:4px;">
              <div style="background:{bar_color};width:{bar_pct}%;height:6px;border-radius:4px;"></div>
            </div>
          </td>
          <td style="padding:6px 12px;text-align:center;">{row['Résistance max (kg)']} kg</td>
        </tr>"""

    table_html = f"""
    <style>table.sc-res{{width:100%;border-collapse:collapse;font-family:sans-serif;font-size:14px;}}
    table.sc-res th{{background:{header_color};color:white;padding:10px 12px;text-align:left;}}
    table.sc-res td{{border-bottom:1px solid #e2e8f0;}}
    </style>
    <table class="sc-res">
      <thead>
        <tr>
          <th>Diamètre</th>
          <th style="text-align:center;">Min (kg)</th>
          <th style="text-align:center;">Moyen (kg)</th>
          <th style="text-align:center;">Max (kg)</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    """
    estimated_h = min(len(df_f) * 38 + 60, 700)
    components.html(table_html, height=estimated_h, scrolling=True)

    st.download_button(
        f"📥 Télécharger CSV ({fil_type})",
        df_f.to_csv(index=False).encode("utf-8-sig"),
        f"resistance_{fil_type.lower()}.csv", "text/csv",
        key=f"dl_{fil_type}",
    )




# ─────────────────────────────────────────────────────────────────────────────
# Mes records personnels — par espèce
# ─────────────────────────────────────────────────────────────────────────────

def _render_records() -> None:
    section("Mes records personnels", icon="🏆")
    st.caption("Tes meilleures prises par espèce, comparées aux records officiels.")

    captures = load_captures()
    if captures.empty:
        st.info("Aucune capture enregistrée. Tes records apparaîtront ici après tes premières prises.")
        return

    sessions = load_sessions()
    sess_idx = {}
    if not sessions.empty:
        for _, s in sessions.iterrows():
            sess_idx[int(s["id"])] = s

    # Imports différés (évite cycles)
    from data.fish_data import FISH_META, FISH_EMOJI_FALLBACK
    from data.fish_records import get_official_record
    from modules.identification import _capture_matches_fish
    import base64
    from pathlib import Path

    # Nettoyer les colonnes
    cap = captures.copy()
    if "espece" not in cap.columns:
        st.warning("Données de capture incomplètes.")
        return
    cap["espece"] = cap["espece"].fillna("").astype(str)
    cap = cap[cap["espece"].str.strip() != ""]
    if cap.empty:
        st.info("Aucune capture avec espèce identifiée.")
        return

    if "taille_cm" in cap.columns:
        cap["taille_cm"] = pd.to_numeric(cap["taille_cm"], errors="coerce")
    if "poids_g" in cap.columns:
        cap["poids_g"]   = pd.to_numeric(cap["poids_g"], errors="coerce")
    if "poids_estime_g" in cap.columns:
        cap["poids_estime_g"] = pd.to_numeric(cap["poids_estime_g"], errors="coerce")

    def _meta(row):
        if row is None:
            return ("—", "—")
        sid = row.get("session_id")
        if pd.notna(sid) and int(sid) in sess_idx:
            s = sess_idx[int(sid)]
            d    = format_date_fr(s.get("date_session")) or "—"
            lieu = safe_str(s.get("lieu")) or "—"
            return (d, lieu)
        return ("—", "—")

    # Construire les records par espèce
    records = []
    for espece, group in cap.groupby("espece"):
        nb_total = len(group)

        # Record taille (préférence : ligne avec photo si possible)
        best_t_row = None
        if "taille_cm" in group.columns:
            valid_t = group.dropna(subset=["taille_cm"])
            valid_t = valid_t[valid_t["taille_cm"] > 0]
            if not valid_t.empty:
                best_t_row = valid_t.loc[valid_t["taille_cm"].idxmax()]

        # Record poids (mesuré, sinon estimé)
        best_p_row = None
        poids_was_estimated = False
        if "poids_g" in group.columns:
            valid_p = group.dropna(subset=["poids_g"])
            valid_p = valid_p[valid_p["poids_g"] > 0]
            if not valid_p.empty:
                best_p_row = valid_p.loc[valid_p["poids_g"].idxmax()]
        # Fallback poids estimé si pas de poids mesuré
        if best_p_row is None and "poids_estime_g" in group.columns:
            valid_pe = group.dropna(subset=["poids_estime_g"])
            valid_pe = valid_pe[valid_pe["poids_estime_g"] > 0]
            if not valid_pe.empty:
                best_p_row = valid_pe.loc[valid_pe["poids_estime_g"].idxmax()]
                poids_was_estimated = True

        date_t, lieu_t = _meta(best_t_row)
        date_p, lieu_p = _meta(best_p_row)

        # Photo du record (trophée > taille max)
        photo_path = ""
        trophee_row = None
        if "poisson_trophee" in group.columns:
            tr = group[group["poisson_trophee"].fillna(0).astype(int) == 1]
            if not tr.empty and "photo_path" in tr.columns:
                # Le trophée avec une photo
                tr_p = tr[tr["photo_path"].astype(str).str.len() > 0]
                if not tr_p.empty:
                    trophee_row = tr_p.iloc[0]
                    p = safe_str(trophee_row.get("photo_path"))
                    if p and str(p).startswith("http"):
                        photo_path = p
        # Sinon photo du best_t_row
        if not photo_path and best_t_row is not None:
            p = safe_str(best_t_row.get("photo_path"))
            if p and str(p).startswith("http"):
                photo_path = p
        # Sinon n'importe quelle photo de la group
        if not photo_path and "photo_path" in group.columns:
            with_photo = group[group["photo_path"].astype(str).str.len() > 0]
            if not with_photo.empty:
                p = safe_str(with_photo.iloc[0].get("photo_path"))
                if p and str(p).startswith("http"):
                    photo_path = p

        # Identifier la fiche poisson correspondante
        fish_match = None
        for f in FISH_META:
            if _capture_matches_fish(espece, f):
                fish_match = f
                break

        # Record officiel
        official = get_official_record(fish_match["id"]) if fish_match else None

        # Poids du best_p_row : mesuré ou estimé ?
        poids_value = None
        if best_p_row is not None:
            if poids_was_estimated:
                poids_value = float(best_p_row["poids_estime_g"])
            else:
                poids_value = float(best_p_row["poids_g"])

        records.append({
            "espece":       espece,
            "fish_match":   fish_match,
            "nb_total":     nb_total,
            "taille_cm":    float(best_t_row["taille_cm"]) if best_t_row is not None else None,
            "date_t":       date_t,
            "lieu_t":       lieu_t,
            "poids_g":      poids_value,
            "poids_estime": poids_was_estimated,
            "date_p":       date_p,
            "lieu_p":       lieu_p,
            "photo_path":   photo_path,
            "trophee_row":  trophee_row,
            "official":     official,
        })

    # Tri par taille décroissante
    records.sort(key=lambda r: -(r["taille_cm"] or 0))

    st.markdown(f"**{len(records)} espèce(s) capturée(s)** · {len(cap)} prises totales")
    st.markdown("---")

    for r in records:
        espece    = r["espece"]
        nb_total  = r["nb_total"]
        taille    = r["taille_cm"]
        poids     = r["poids_g"]
        fish      = r["fish_match"]
        photo     = r["photo_path"]
        official  = r["official"]
        has_trophy = r["trophee_row"] is not None

        # SVG correct via la fiche matchée
        svg_html = ""
        if fish:
            svg = FISH_SVG.get(fish["id"], "")
            if svg:
                svg_html = (
                    f'<div style="width:100%;height:100%;display:flex;'
                    f'align-items:center;justify-content:center;padding:6px;">'
                    f'<div style="width:100%;max-width:100px;">{svg}</div></div>'
                )
        if not svg_html:
            # Fallback emoji depuis fish_data ou générique
            emoji = "🐟"
            if fish:
                emoji = FISH_EMOJI_FALLBACK.get(fish["id"], "🐟")
            svg_html = (f'<div style="font-size:48px;width:100%;height:100%;'
                        f'display:flex;align-items:center;justify-content:center;">'
                        f'{emoji}</div>')

        # Photo personnelle (vignette) — URL Supabase + lightbox
        photo_html = ""
        if photo and str(photo).startswith("http"):
            tag = "🏆" if has_trophy else "📸"
            lb_id = f"lb_troph_{r.get('espece','').replace(' ','_')}_{hash(photo)%10000}"
            photo_html = (
                f'<div style="position:relative;width:100%;height:100%;">'
                f'<img src="{photo}" onclick="document.getElementById(\'{lb_id}\').style.display=\'flex\'"'
                f'style="width:100%;height:100%;object-fit:cover;cursor:pointer;'
                f'border-radius:8px;border:2px solid #FFB300;">'
                f'<div style="position:absolute;top:4px;right:4px;background:#FFB300;'
                f'color:#fff;font-size:11px;font-weight:700;padding:2px 6px;'
                f'border-radius:6px;">{tag}</div>'
                f'<div id="{lb_id}" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);'
                f'z-index:9999;align-items:center;justify-content:center;flex-direction:column;">'
                f'<img src="{photo}" style="max-width:90vw;max-height:85vh;object-fit:contain;border-radius:8px;">'
                f'<button onclick="document.getElementById(\'{lb_id}\').style.display=\'none\'"'
                f'style="margin-top:14px;background:rgba(255,255,255,.2);color:#fff;border:none;'
                f'padding:10px 24px;border-radius:8px;font-size:14px;cursor:pointer;">Fermer</button>'
                f'</div>'
                f'</div>'
            )

        # Format poids
        def _fmt_poids(p, suffix=""):
            if p is None: return "—"
            txt = f"{p/1000:.2f} kg" if p >= 1000 else f"{p:.0f} g"
            return f"{txt}{suffix}"

        poids_txt_perso = _fmt_poids(poids, " (estimé)" if r["poids_estime"] else "")
        taille_txt      = f"{taille:.0f} cm" if taille is not None else "—"

        with st.container(border=True):
            # ── En-tête : nom + nb prises ──────────────────────────
            badge_trophy = ('<span style="background:#FFD54F;color:#5d4f1a;'
                             'font-size:11px;font-weight:700;padding:3px 10px;'
                             'border-radius:10px;margin-left:8px;">🏆 TROPHÉE</span>'
                             ) if has_trophy else ""
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'align-items:baseline;flex-wrap:wrap;margin-bottom:10px;">'
                f'<div><span style="font-size:20px;font-weight:800;color:#0c2340;">'
                f'{espece}</span>{badge_trophy}</div>'
                f'<div style="font-size:11px;color:#546E7A;">'
                f'🎣 {nb_total} prise(s) au total</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # ── 1ère ligne : photo perso + SVG + record perso ──────
            col_photo, col_svg, col_t, col_p = st.columns([1, 0.8, 1.3, 1.3])

            with col_photo:
                if photo_html:
                    components.html(
                        f'<div style="display:flex;align-items:center;justify-content:center;'
                        f'height:120px;">{photo_html}</div>',
                        height=130, scrolling=False,
                    )
                else:
                    st.markdown(
                        '<div style="height:120px;background:#f5f7f9;border:2px dashed #bbb;'
                        'border-radius:8px;display:flex;align-items:center;justify-content:center;'
                        'color:#999;font-size:11px;text-align:center;">'
                        'Aucune photo<br>de capture</div>',
                        unsafe_allow_html=True,
                    )

            with col_svg:
                components.html(
                    f'<div style="display:flex;align-items:center;justify-content:center;'
                    f'height:120px;background:#f5f7f9;border-radius:8px;">{svg_html}</div>',
                    height=130, scrolling=False,
                )

            with col_t:
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,#FFB300,#E65100);'
                    f'color:#fff;border-radius:8px;padding:10px 12px;text-align:center;'
                    f'height:120px;display:flex;flex-direction:column;justify-content:center;">'
                    f'<div style="font-size:9px;font-weight:700;letter-spacing:1px;'
                    f'opacity:.9;">📏 MA TAILLE MAX</div>'
                    f'<div style="font-size:24px;font-weight:900;line-height:1.1;'
                    f'margin:4px 0;">{taille_txt}</div>'
                    f'<div style="font-size:10px;opacity:.9;">{r["date_t"]}</div>'
                    f'<div style="font-size:10px;opacity:.9;">📍 {r["lieu_t"][:22]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            with col_p:
                est_tag = ('<span style="background:rgba(255,255,255,.2);font-size:8px;'
                            'font-weight:700;padding:1px 5px;border-radius:4px;'
                            'margin-left:4px;">EST.</span>') if r["poids_estime"] else ""
                poids_no_suffix = _fmt_poids(poids)
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,#42A5F5,#1565C0);'
                    f'color:#fff;border-radius:8px;padding:10px 12px;text-align:center;'
                    f'height:120px;display:flex;flex-direction:column;justify-content:center;">'
                    f'<div style="font-size:9px;font-weight:700;letter-spacing:1px;'
                    f'opacity:.9;">⚖️ MON POIDS MAX{est_tag}</div>'
                    f'<div style="font-size:24px;font-weight:900;line-height:1.1;'
                    f'margin:4px 0;">{poids_no_suffix}</div>'
                    f'<div style="font-size:10px;opacity:.9;">{r["date_p"]}</div>'
                    f'<div style="font-size:10px;opacity:.9;">📍 {r["lieu_p"][:22]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # ── 2e ligne : record officiel si dispo ────────────────
            if official:
                off_taille = official.get("taille_cm")
                off_poids  = official.get("poids_g")
                off_lieu   = official.get("lieu") or "—"
                off_annee  = official.get("annee") or ""

                off_taille_txt = f"{off_taille:.0f} cm" if off_taille else "—"
                off_poids_txt  = (f"{off_poids/1000:.1f} kg" if off_poids and off_poids >= 1000
                                    else (f"{off_poids:.0f} g" if off_poids else "—"))

                # Pourcentage du record perso vs officiel (taille)
                pct_taille = (taille / off_taille * 100) if (taille and off_taille) else 0
                pct_color = "#2E7D32" if pct_taille >= 80 else \
                             ("#E65100" if pct_taille >= 50 else "#9E9E9E")

                st.markdown(
                    f'<div style="background:linear-gradient(135deg,#0c2340,#1565C0);'
                    f'color:#fff;border-radius:8px;padding:10px 14px;margin-top:8px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;'
                    f'flex-wrap:wrap;gap:8px;">'
                    f'<div style="font-size:11px;font-weight:700;letter-spacing:1px;'
                    f'opacity:.85;">🌍 RECORD OFFICIEL CONNU</div>'
                    f'<div style="font-size:10px;opacity:.85;">'
                    f'{("📅 " + off_annee) if off_annee else ""}</div>'
                    f'</div>'
                    f'<div style="display:flex;gap:14px;align-items:center;margin-top:4px;flex-wrap:wrap;">'
                    f'<div><strong style="font-size:16px;">📏 {off_taille_txt}</strong></div>'
                    f'<div><strong style="font-size:16px;">⚖️ {off_poids_txt}</strong></div>'
                    f'<div style="opacity:.9;font-size:12px;">📍 {off_lieu}</div>'
                    + (f'<div style="margin-left:auto;background:{pct_color};font-size:11px;'
                        f'font-weight:700;padding:2px 10px;border-radius:10px;">'
                        f'Mon score : {pct_taille:.0f}% du record</div>'
                        if pct_taille > 0 else "") +
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

    # Export CSV
    st.markdown("---")
    df_export = pd.DataFrame([{
        "Espèce":           r["espece"],
        "Nb prises":        r["nb_total"],
        "Taille max (cm)":  r["taille_cm"],
        "Date taille":      r["date_t"],
        "Lieu taille":      r["lieu_t"],
        "Poids max (g)":    r["poids_g"],
        "Poids estimé":     "oui" if r["poids_estime"] else "non",
        "Date poids":       r["date_p"],
        "Lieu poids":       r["lieu_p"],
        "Trophée":          "oui" if r["trophee_row"] is not None else "non",
        "Record off. (cm)": r["official"].get("taille_cm") if r["official"] else None,
        "Record off. (g)":  r["official"].get("poids_g")   if r["official"] else None,
        "Record off. lieu": r["official"].get("lieu")      if r["official"] else None,
    } for r in records])
    st.download_button("📥 Exporter mes records (CSV)",
                        df_export.to_csv(index=False).encode("utf-8-sig"),
                        "mes_records.csv", "text/csv")
