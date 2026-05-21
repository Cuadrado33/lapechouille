"""Styles CSS globaux — thème marine/cuivre, inspiration maquettes validées."""
import streamlit as st

CSS_GLOBAL = """
<style>
:root {
    --sf-blue-deep: #0c2340;
    --sf-blue-mid:  #1565C0;
    --sf-blue-light: #62b6cb;
    --sf-copper:    #c9712b;
    --sf-orange:    #E65100;
    --sf-green:     #2E7D32;
    --sf-sand:      #f4e4c1;
    --sf-border:    rgba(15,23,42,0.10);
    --sf-card-bg:   #ffffff;
    --sf-alt-bg:    #f5f7fb;
    --sf-text:      #0f172a;
    --sf-muted:     #546e7a;
}

/* ── Sidebar ────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0c2340 0%, #1b4965 100%);
    border-right: none;
}
section[data-testid="stSidebar"] * { color: rgba(255,255,255,0.90); }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #fff !important; }

/* boutons sidebar */
section[data-testid="stSidebar"] button[kind="secondary"] {
    background: rgba(255,255,255,0.08) !important;
    border: 0.5px solid rgba(255,255,255,0.18) !important;
    border-radius: 8px !important;
    color: rgba(255,255,255,0.92) !important;
    text-align: left !important;
    padding: 7px 10px !important;
    font-size: 12px !important;
    transition: background 0.12s;
}
section[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.16) !important;
}

/* ── Contenu principal ──────────────────────────────────────────── */
.main .block-container { padding-top: 1.5rem; max-width: 1100px; }

/* ── Métriques ──────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--sf-alt-bg);
    border-radius: 8px;
    padding: 10px 14px;
}
[data-testid="stMetricLabel"] { font-size: 10px !important; color: var(--sf-muted) !important; text-transform: uppercase; letter-spacing: .7px; }
[data-testid="stMetricValue"] { font-size: 22px !important; font-weight: 500 !important; }
[data-testid="stMetricDelta"] { font-size: 11px !important; }

/* ── Encadrés st.container(border=True) ─────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 0.5px solid rgba(15,23,42,0.12) !important;
    border-radius: 12px !important;
    padding: 14px 16px !important;
    background: var(--sf-card-bg);
}

/* ── Alternance fond ─────────────────────────────────────────────── */
.sf-alt { background: var(--sf-alt-bg) !important; }

/* ── Badges ──────────────────────────────────────────────────────── */
.sf-badge {
    display: inline-block; padding: 2px 8px; border-radius: 20px;
    font-size: 10px; font-weight: 600; line-height: 1.6;
}
.sf-badge-blue   { background: #E3F2FD; color: #1565C0; }
.sf-badge-orange { background: #FFF3E0; color: #E65100; }
.sf-badge-green  { background: #E8F5E9; color: #2E7D32; }
.sf-badge-purple { background: #F3E5F5; color: #6A1B9A; }
.sf-badge-grey   { background: #ECEFF1; color: #546E7A; }
.sf-badge-live   {
    background: #E65100; color: #fff; font-size: 9px; letter-spacing: .8px;
    text-transform: uppercase; padding: 3px 8px; border-radius: 20px;
    animation: sf-pulse 1.5s infinite;
}
@keyframes sf-pulse { 0%,100%{opacity:1} 50%{opacity:.65} }

/* ── Session active (encadré bleu) ───────────────────────────────── */
.sf-session-active {
    border: 2px solid #1565C0 !important;
    border-radius: 12px !important;
}

/* ── Capture row ─────────────────────────────────────────────────── */
.sf-cap-row {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 12px; border-radius: 8px;
    background: var(--sf-alt-bg);
    margin-bottom: 6px;
}

/* ── Tabs style pill ─────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    gap: 4px; background: transparent;
    border-bottom: 0.5px solid rgba(15,23,42,0.10);
}
[data-testid="stTabs"] [role="tab"] {
    border-radius: 20px !important;
    font-size: 12px !important;
    padding: 5px 14px !important;
    border: 0.5px solid rgba(15,23,42,0.12) !important;
    background: transparent !important;
    color: var(--sf-muted) !important;
    transition: all 0.12s;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    background: #1565C0 !important;
    color: #fff !important;
    border-color: #1565C0 !important;
}

/* ── Tableaux ────────────────────────────────────────────────────── */
.sf-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.sf-table th {
    padding: 5px 10px; text-align: left;
    font-size: 9px; text-transform: uppercase; letter-spacing: .8px;
    color: var(--sf-muted); background: var(--sf-alt-bg);
    border-bottom: 0.5px solid var(--sf-border);
}
.sf-table td { padding: 9px 10px; border-bottom: 0.5px solid var(--sf-border); }
.sf-table tr:last-child td { border-bottom: none; }
.sf-table tr:nth-child(even) td { background: var(--sf-alt-bg); }

/* ── Résistance fil ──────────────────────────────────────────────── */
.res-nylon  { color: #1565C0; font-weight: 700; }
.res-tresse { color: #E65100; font-weight: 700; }
.res-fluoro { color: #6A1B9A; font-weight: 700; }

/* ── Bouton ajout dashed ─────────────────────────────────────────── */
.sf-add-dashed {
    width: 100%; padding: 10px; text-align: center;
    border: 1.5px dashed rgba(15,23,42,0.20);
    border-radius: 8px; background: transparent;
    color: var(--sf-muted); font-size: 12px; cursor: pointer;
    transition: all 0.12s;
}
.sf-add-dashed:hover {
    border-color: #1565C0; color: #1565C0;
    background: rgba(21,101,192,0.04);
}

/* ── Titres de section ───────────────────────────────────────────── */
.sf-section-title {
    font-size: 9px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 1px; color: var(--sf-muted); margin-bottom: 8px;
}

/* ── Boutons Éditer (VERT) / Supprimer (ROUGE) — global ─────────── */
/* Streamlit ajoute une classe `st-key-{key}` sur le wrapper du widget.
   On cible UNIQUEMENT les vraies clés de boutons Éditer/Supprimer
   (sans toucher aux clés de formulaires d'édition comme ec_esp_42). */

/* VERT — boutons Éditer */
.stApp [class*="st-key-edit_"] button,
.stApp [class*="st-key-"][class*="_edit_btn"] button,
.stApp [class*="st-key-"][class*="_close_edit"] button,
.stApp [class*="st-key-em_save_"] button,
.stApp [class*="st-key-ba_edit_btn_"] button,
.stApp [class*="st-key-sp_edit_btn_"] button,
.stApp [class*="st-key-cap_edit_btn_"] button,
.stApp [class*="st-key-edit_mont_"] button,
.stApp [class*="st-key-edit_btn_"] button,
.stApp [class*="st-key-mon_close_edit_"] button,
.stApp [class*="st-key-mon_edit_"] button {
    background-color: #2E7D32 !important;
    border-color: #2E7D32 !important;
    color: #fff !important;
    font-weight: 700 !important;
}
.stApp [class*="st-key-edit_"] button:hover,
.stApp [class*="st-key-"][class*="_edit_btn"] button:hover,
.stApp [class*="st-key-"][class*="_close_edit"] button:hover,
.stApp [class*="st-key-em_save_"] button:hover,
.stApp [class*="st-key-ba_edit_btn_"] button:hover,
.stApp [class*="st-key-sp_edit_btn_"] button:hover,
.stApp [class*="st-key-cap_edit_btn_"] button:hover,
.stApp [class*="st-key-edit_mont_"] button:hover,
.stApp [class*="st-key-edit_btn_"] button:hover,
.stApp [class*="st-key-mon_close_edit_"] button:hover,
.stApp [class*="st-key-mon_edit_"] button:hover {
    background-color: #1B5E20 !important;
    border-color: #1B5E20 !important;
}

/* ROUGE — boutons Supprimer */
.stApp [class*="st-key-del_"] button,
.stApp [class*="st-key-"][class*="_del_"] button,
.stApp [class*="st-key-"][class*="_del_btn"] button,
.stApp [class*="st-key-comp_del_"] button,
.stApp [class*="st-key-cap_del_"] button,
.stApp [class*="st-key-sp_del_"] button,
.stApp [class*="st-key-ba_del_"] button,
.stApp [class*="st-key-spot_del_"] button,
.stApp [class*="st-key-ss_del_"] button {
    background-color: #C62828 !important;
    border-color: #C62828 !important;
    color: #fff !important;
    font-weight: 700 !important;
}
.stApp [class*="st-key-del_"] button:hover,
.stApp [class*="st-key-"][class*="_del_"] button:hover,
.stApp [class*="st-key-"][class*="_del_btn"] button:hover,
.stApp [class*="st-key-comp_del_"] button:hover,
.stApp [class*="st-key-cap_del_"] button:hover,
.stApp [class*="st-key-sp_del_"] button:hover,
.stApp [class*="st-key-ba_del_"] button:hover,
.stApp [class*="st-key-spot_del_"] button:hover,
.stApp [class*="st-key-ss_del_"] button:hover {
    background-color: #B71C1C !important;
    border-color: #B71C1C !important;
}

/* Tous les boutons ont au moins font-weight 600 pour le texte */
.stApp button p {
    font-weight: 600 !important;
}

</style>
"""

def inject_global_styles() -> None:
    st.markdown(CSS_GLOBAL, unsafe_allow_html=True)
