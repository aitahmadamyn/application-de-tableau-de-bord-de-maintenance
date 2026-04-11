import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 1. CONNEXION SÉCURISÉE ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# On récupère le secret qu'on vient de coller dans Streamlit
creds_dict = json.loads(st.secrets["google_credentials"])
creds = ServiceAccountCredentials.from_service_account_info(creds_dict, scope)
client = gspread.authorize(creds)

# --- 2. LECTURE DES DONNÉES ---
@st.cache_data(ttl=60)
def load_data():
    # ATTENTION : Remplacez "GMAO_IoT_Data" par le nom exact de votre fichier Google Sheets si besoin
    sheet = client.open("GMAO_IoT_Data").sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# --- 3. AFFICHAGE ---
st.title("⚙️ Dashboard GMAO & IoT")

try:
    df = load_data()
    if df.empty:
        st.warning("Le Google Sheet est vide pour le moment.")
    else:
        st.success("Connecté au Google Sheet avec succès !")
        st.dataframe(df)
        
except Exception as e:
    st.error(f"Erreur de connexion : {e}")
