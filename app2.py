import streamlit as st
import pandas as pd
import numpy as np

@st.cache_data
def load_data():
    xls = pd.ExcelFile("data/naeringsdata.xlsx")
    data = []
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        df["Produkt"] = df["Produkt"].ffill()
        df["Kategori"] = sheet
        df = df.ffill()
        data.append(df)
    return pd.concat(data, ignore_index=True)

def legg_emoji(tekst, kolonne):
    if pd.isna(tekst):
        return ""
    tekst = str(tekst)
    if kolonne == "Kilde til?" and tekst.lower().startswith("ja"):
        return f"{tekst} ✅"
    elif kolonne == "Rik på?" and tekst.lower().startswith("ja"):
        return f"{tekst} 🌟"
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
            ('text-align', 'left'),
        ]},
        {'selector': 'td', 'props': [('text-align', 'left')]},
    ]

    styled = (df.style
              .apply(lambda x: ['background-color: #f9f9f9' if i % 2 == 1 else '' for i in range(len(x))], axis=1)
              .set_table_styles(styles)
              .applymap(highlight_na)
              .format({
                  "Mengde per 100 gram": "{:.1f}",
                  "Referanseverdi per 100 g": "{:.1f}",
                  "Utregning %": "{:.1f}"
              }, na_rep="N/A")
              .set_properties(**{'max-width': '120px'})
    )
    return styled

def generer_vurdering_tekst(df, kolonne, emoji, tittel):
    ja_liste = df[df[kolonne].str.contains("Ja", na=False)]["Næringsstoff"].tolist()
    if not ja_liste:
        return None
    tekst = f"{emoji} {tittel}:\n" + "\n".join(f"- {ns}" for ns in ja_liste)
    return tekst

# --- App start ---
st.set_page_config(
    page_title="🧀🥛 Ernæringspåstander for meieriprodukter",
    layout="wide",
    page_icon="icon.png"
)

st.markdown("""
    <style>
    h1 {
        font-size: 1.8rem !important;
        white-space: nowrap;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🧀🥛 Ernæringspåstander for meieriprodukter")
st.caption("Datakilder oppgitt. Referanseverdier hentet fra Matinformasjonsforskriften. Produktmengde: 100 gram.")

df = load_data()

kategori_valg = ["Alle kategorier"] + sorted(df["Kategori"].unique())
kategori = st.sidebar.radio("Velg kategori", kategori_valg)

if kategori != "Alle kategorier":
    df_kat = df[df["Kategori"] == kategori]

    naeringsstoffer_fokus = [
        "Protein", "Kalsium", "Jod", "Vitamin B12", "Vitamin B2",
        "Fosfor", "Kalium", "Magnesium", "Vitamin A", "Vitamin D"
    ]

    variasjoner = []
    for ns in naeringsstoffer_fokus:
        df_ns = df_kat[df_kat["Næringsstoff"] == ns]
        if df_ns.empty:
            continue
        variasjon_kilde = df_ns["Kilde til?"].str.contains("Ja", na=False).nunique()
        variasjon_rik = df_ns["Rik på?"].str.contains("Ja", na=False).nunique()
        if variasjon_kilde > 1 or variasjon_rik > 1:
            variasjoner.append(ns)

    if variasjoner:
        tekst = "💡 Merk: Det er variasjon mellom produktene innen innhold av næringsstoff " + \
                ", ".join(variasjoner) + " med tanke på hvilke ernæringspåstander som kan brukes."
        st.info(tekst)

df_kategori = df if kategori == "Alle kategorier" else df[df["Kategori"] == kategori]

søk = st.sidebar.text_input("Søk i produkter innen valgt kategori").strip().lower()

produkter = df_kategori["Produkt"].dropna().unique()
if søk:
    produkter = [p for p in produkter if søk in p.lower()]

for produktnavn in produkter:
    st.subheader(produktnavn)
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

    kilde_tekst = generer_vurdering_tekst(produktdata, "Kilde til?", "✅", "Kilde til")
    rik_tekst = generer_vurdering_tekst(produktdata, "Rik på?", "🌟", "Rik på")

    if kilde_tekst:
        st.info(kilde_tekst)
    if rik_tekst:
        st.info(rik_tekst)
