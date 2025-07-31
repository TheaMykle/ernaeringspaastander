import streamlit as st
import pandas as pd
import numpy as np

@st.cache_data
def load_data():
    xls = pd.ExcelFile("naeringsdata.xlsx")
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
        vurdering += "✅ Kilde til:  \n"
        vurdering += "\n".join(f"- {k}" for k in kilder) + "\n"
    if rik:
        vurdering += "  🌟 Rik på:  \n"
        vurdering += "\n".join(f"- {r}" for r in rik) + "\n"
    if not vurdering:
        vurdering = "🔎 Ingen ernæringspåstander kan fremmes basert på dataene."
    return vurdering

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
            ('position', 'sticky'),
            ('top', '0'),
            ('z-index', '100'),
            ('text-align', 'left')
        ]},
        {'selector': 'td', 'props': [('text-align', 'left')]}
    ]

    styled = (df.style
              .apply(lambda x: ['background-color: #f9f9f9' if i % 2 == 1 else '' for i in range(len(x))], axis=1)
              .set_table_styles(styles)
              .applymap(highlight_na)
              .format({
                  "Mengde per 100 gram": "{:.1f}",
                  "Referanseverdi per 100 g": "{:.1f}",
                  "Utregning %": "{:.0f}"
              }, na_rep="N/A")
              .set_properties(**{'max-width': '120px'})
    )
    return styled

def variasjon_melding(df_kategori):
    naeringsstoff_liste = [
        "Protein", "Kalsium", "Jod", "Vitamin B12", "Vitamin B2", 
        "Fosfor", "Kalium", "Magnesium", "Vitamin A", "Vitamin D"
    ]

    variasjon_naringsstoff = []
    for n in naeringsstoff_liste:
        df_n = df_kategori[df_kategori["Næringsstoff"] == n]
        if df_n.empty:
            continue
        andeler_kilde = df_n["Kilde til?"].str.contains("Ja", na=False).mean()
        andeler_rik = df_n["Rik på?"].str.contains("Ja", na=False).mean()
        # vurderer stor variasjon om andel ligger mellom 0.25 og 0.75
        if 0.25 < andeler_kilde < 0.75 or 0.25 < andeler_rik < 0.75:
            variasjon_naringsstoff.append(n)

    if variasjon_naringsstoff:
        tekst = "💡 Merk: Det er variasjon mellom produktene innen innhold av næringsstoff " + \
                ", ".join(variasjon_naringsstoff) + " med tanke på hvilke ernæringspåstander som kan brukes."
        st.info(tekst)

# --- App start ---
st.set_page_config(page_title="🧀🥛 Ernæringspåstander for meieriprodukter", layout="wide", page_icon="icon.png")
st.title("🧀🥛 Ernæringspåstander for meieriprodukter")
st.caption("Datakilder oppgitt. Referanseverdier hentet fra Matinformasjonsforskriften. Produktmengde: 100 gram.")

df = load_data()

kategori_valg = ["Alle kategorier"] + sorted(df["Kategori"].unique())
kategori = st.sidebar.radio("Velg kategori", kategori_valg)

df_kategori = df if kategori == "Alle kategorier" else df[df["Kategori"] == kategori]

if kategori != "Alle kategorier":
    variasjon_melding(df_kategori)

søk = st.sidebar.text_input("Søk i produkter innen valgt kategori").strip().lower()

produkter = df_kategori["Produkt"].dropna().unique()
if søk:
    produkter = [p for p in produkter if søk in p.lower()]

grupper = [(p, df_kategori[df_kategori["Produkt"] == p]) for p in produkter]

for produktnavn, df_gruppe in grupper:
    st.markdown(f"<h4 style='margin-bottom:0.3em;'>{produktnavn}</h4>", unsafe_allow_html=True)

    produktdata = df_gruppe.copy()
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
