import streamlit as st
import pandas as pd
import numpy as np

@st.cache_data
def load_data():
    xls = pd.ExcelFile("naeringsdata.xlsx")  # Endret sti til root
    data = []
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        df["Produkt"] = df["Produkt"].ffill()
        df["Kategori"] = sheet
        df = df.ffill()
        data.append(df)
    return pd.concat(data, ignore_index=True)

def generer_vurdering_liste(df):
    kilder = df[df["Kilde til?"].str.contains("Ja", na=False)]["Næringsstoff"].tolist()
    rik = df[df["Rik på?"].str.contains("Ja", na=False)]["Næringsstoff"].tolist()

    vurdering = ""
    if kilder:
        vurdering += "✅ Kilde til:\n"
        vurdering += "\n".join(f"- {k}" for k in kilder) + "\n"
    if rik:
        vurdering += "\n🌟 Rik på:\n"
        vurdering += "\n".join(f"- {r}" for r in rik) + "\n"
    if not vurdering:
        vurdering = "🔎 Ingen ernæringspåstander kan fremmes basert på dataene."
    return vurdering

def legg_emoji(tekst, kolonne):
    if pd.isna(tekst):
        return ""
    tekst = str(tekst)
    if kolonne == "Kilde til?" and tekst.lower().startswith("ja"):
        return f"✅ {tekst}"
    elif kolonne == "Rik på?" and tekst.lower().startswith("ja"):
        return f"🌟 {tekst}"
    return tekst

def style_tabell(df):
    def highlight_na(val):
        if pd.isna(val) or val == "":
            return 'color: #a0a0a0; font-style: italic;'
        return ''

    styles = [
        {'selector': 'th', 'props': [
            ('font-weight', 'bold'),
            ('background-color', '#f0f0f0'),
            ('text-align', 'left')
        ]},
        {'selector': 'td', 'props': [('text-align', 'left')]}
    ]

    styled = (df.style
              .apply(lambda x: ['background-color: #f9f9f9' if i % 2 == 1 else '' for i in range(len(x))], axis=1)
              .set_table_styles(styles)
              #.applymap(highlight_na)
              .format({
                  "Mengde per 100 gram": "{:.1f}",
                  "Referanseverdi per 100 g": "{:.1f}",
                  "Utregning %": "{:.0f}"
              }, na_rep="N/A")
              .set_properties(**{'max-width': '120px'})
    )
    return styled

# --- App start ---
st.set_page_config(page_title="🧀🥛 Ernæringspåstander for meieriprodukter", layout="wide", page_icon="icon.png")
st.markdown("<h2 style='font-size:28px;'>🧀🥛 Ernæringspåstander for meieriprodukter</h2>", unsafe_allow_html=True)
st.caption("Datakilder oppgitt. Referanseverdier hentet fra Matinformasjonsforskriften. Produktmengde: 100 gram.")

df = load_data()

kategori_valg = ["Alle kategorier"] + sorted(df["Kategori"].unique())
kategori = st.sidebar.radio("Velg kategori", kategori_valg)

if kategori != "Alle kategorier":
    df_kategori = df[df["Kategori"] == kategori]

    # Sjekk variasjon i 'Kilde til?' og 'Rik på?' per næringsstoff i valgt kategori
    variabler = [
        "Protein", "Kalsium", "Jod", "Vitamin B12", "Vitamin B2",
        "Fosfor", "Kalium", "Magnesium", "Vitamin A", "Vitamin D"
    ]

    variasjoner = []
    for næring in variabler:
        df_næring = df_kategori[df_kategori["Næringsstoff"] == næring]
        if not df_næring.empty:
            kilde_til_var = df_næring["Kilde til?"].str.contains("Ja", na=False).nunique()
            rik_på_var = df_næring["Rik på?"].str.contains("Ja", na=False).nunique()
            if kilde_til_var > 1 or rik_på_var > 1:
                variasjoner.append(næring)

    if variasjoner:
        st.info(f"💡 Merk: Det er variasjon mellom produktene innen innhold av næringsstoff {', '.join(variasjoner)} med tanke på hvilke ernæringspåstander som kan brukes.")

else:
    df_kategori = df

søk = st.sidebar.text_input("Søk i produkter innen valgt kategori").strip().lower()

produkter = df_kategori["Produkt"].dropna().unique()
if søk:
    produkter = [p for p in produkter if søk in p.lower()]

for produktnavn in produkter:
    st.markdown(f"<h5>{produktnavn}</h5>", unsafe_allow_html=True)
    produktdata = df_kategori[df_kategori["Produkt"] == produktnavn].copy()

    produktdata = produktdata[produktdata["Næringsstoff"].notna()]
    produktdata = produktdata[produktdata["Næringsstoff"].str.lower() != produktnavn.lower()]

    visning = produktdata[[
        "Næringsstoff",
        "Mengde per 100 gram",
        "Referanseverdi per 100 g",
        "Utregning %",
        "Kilde til?",
        "Rik på?"
    ]]

    visning["Kilde til?"] = visning["Kilde til?"].apply(lambda x: legg_emoji(x, "Kilde til?"))
    visning["Rik på?"] = visning["Rik på?"].apply(lambda x: legg_emoji(x, "Rik på?"))

    stylet_df = style_tabell(visning.reset_index(drop=True))
    st.dataframe(stylet_df, use_container_width=True)

    vurdering_tekst = generer_vurdering_liste(produktdata)
    st.info(vurdering_tekst)
