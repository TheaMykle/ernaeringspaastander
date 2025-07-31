import streamlit as st
import pandas as pd

@st.cache_data
def load_data():
    xls = pd.ExcelFile("naeringsdata.xlsx")
    data = []
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        df["Produkt"] = df["Produkt"].ffill()
        df["Kategori"] = sheet
        df = df.ffill()
        # Fjern rader der næringsstoffet er lik produktnavnet (case-insensitivt)
        df = df[df["Næringsstoff"].str.lower() != df["Produkt"].str.lower()]
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
        vurdering += "\n🌟 Rik på:  \n"  
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
                  "Utregning %": "{:.1f}"
              }, na_rep="N/A")
              .set_properties(**{'max-width': '120px'})
    )
    return styled

def sjekk_varians_ai(df, kategori):
    if kategori == "Alle kategorier":
        return None

    # Faste næringsstoffer å sjekke
    naeringsstoffer = [
        "Protein", "Kalsium", "Jod", "Vitamin B12", "Vitamin B2",
        "Fosfor", "Kalium", "Magnesium", "Vitamin A", "Vitamin D"
    ]

    variasjon_næring = []

    for n in naeringsstoffer:
        df_n = df[(df["Kategori"] == kategori) & (df["Næringsstoff"].str.lower() == n.lower())]
        if len(df_n) < 2:
            continue

        rik_ja = df_n["Rik på?"].str.contains("Ja", na=False).astype(int)
        kilde_ja = df_n["Kilde til?"].str.contains("Ja", na=False).astype(int)

        # Regn variasjon som andel produkter med/uten påstanden, dersom stor variasjon, ta med
        # Threshold kan justeres, her sier vi 20-80% er stor variasjon
        rik_andel = rik_ja.mean()
        kilde_andel = kilde_ja.mean()

        if 0.2 < rik_andel < 0.8 or 0.2 < kilde_andel < 0.8:
            variasjon_næring.append(n)

    if variasjon_næring:
        tekst = "💡 Merk: Det er variasjon mellom produktene innen innhold av næringsstoff " + ", ".join(variasjon_næring) + " med tanke på hvilke ernæringspåstander som kan brukes."
        return tekst
    return None

# --- App start ---
st.set_page_config(page_title="🧀🥛 Ernæringspåstander for meieriprodukter", layout="wide")
st.title("🧀🥛 Ernæringspåstander for meieriprodukter")
st.caption("Datakilder oppgitt. Referanseverdier hentet fra Matinformasjonsforskriften. Produktmengde: 100 gram.")

df = load_data()

kategori_valg = ["Alle kategorier"] + sorted(df["Kategori"].unique())
kategori = st.sidebar.radio("Velg kategori", kategori_valg)

# Vis AI-varsel om variasjon først i kategori
ai_tekst = sjekk_varians_ai(df, kategori)
if ai_tekst:
    st.info(ai_tekst)

df_kategori = df if kategori == "Alle kategorier" else df[df["Kategori"] == kategori]

søk = st.sidebar.text_input("Søk i produkter innen valgt kategori").strip().lower()

produkter = df_kategori["Produkt"].dropna().unique()
if søk:
    produkter = [p for p in produkter if søk in p.lower()]

for produktnavn in produkter:
    st.subheader(produktnavn)
    produktdata = df_kategori[df_kategori["Produkt"] == produktnavn].copy()

    produktdata = produktdata[produktdata["Næringsstoff"].notna()]
    # Fjern næringsstoff lik produktnavnet for å unngå feil tolking
    produktdata = produktdata[produktdata["Næringsstoff"].str.lower() != produktnavn.lower()]

    visning = produktdata[[
        "Næringsstoff",
        "Mengde per 100 gram",
        "Benevning",
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
