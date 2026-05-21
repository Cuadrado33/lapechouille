"""Page Webcams plages."""
from __future__ import annotations
import pandas as pd
import streamlit as st
from data.webcams import get_all_webcams
from ui.components import hero, section

def render() -> None:
    hero("Axe 4 · Divers", "Webcams plages", "Regarde les conditions en direct sur les plages.")
    all_cams = get_all_webcams()
    df = pd.DataFrame(all_cams)
    c1, c2, c3 = st.columns(3)
    pays_options = ["Tous"] + sorted(df["Pays"].unique().tolist())
    with c1:
        sel_pays = st.selectbox("Pays", pays_options, key="wc_pays")
    if sel_pays != "Tous":
        df = df[df["Pays"] == sel_pays]
    region_options = ["Toutes"] + sorted(df["Région / Zone"].unique().tolist())
    with c2:
        sel_region = st.selectbox("Région", region_options, key="wc_region")
    if sel_region != "Toutes":
        df = df[df["Région / Zone"] == sel_region]
    with c3:
        search = st.text_input("Recherche", placeholder="Arcachon, Lacanau...", key="wc_search")
    if search:
        s = search.lower()
        df = df[df.astype(str).apply(lambda c: c.str.lower().str.contains(s, na=False)).any(axis=1)]
    st.caption(f"{len(df)} webcam(s) trouvée(s)")
    cols = st.columns(3)
    for idx, row in df.reset_index(drop=True).iterrows():
        with cols[idx % 3]:
            with st.container(border=True):
                st.markdown(f"**{row['Nom']}**")
                st.caption(f"{row['Pays']} · {row['Région / Zone']} · {row['Type']}")
                st.link_button("🌐 Ouvrir la webcam", row["URL"], use_container_width=True)
