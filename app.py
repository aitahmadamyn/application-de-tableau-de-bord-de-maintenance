import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import json

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="GMAO Dashboard", layout="wide")

# --- 2. CONNEXION SÉCURISÉE ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["google_credentials"])
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# --- 3. LECTURE DES DONNÉES ---
@st.cache_data(ttl=10) # Rafraîchit toutes les 10 secondes
def load_data():
    sheet = client.open("GMAO_IoT_Data").sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    if not df.empty:
        # CORRECTION DE LA DATE ICI : On utilise un format flexible (mixed)
        df['Date_Heure'] = pd.to_datetime(df['Date_Heure'], format='mixed', dayfirst=True, errors='coerce')
        
        # S'assurer que les chiffres sont bien reconnus comme des nombres
        df['Durée_Intervention_min'] = pd.to_numeric(df['Durée_Intervention_min'], errors='coerce').fillna(0)
        df['Température'] = pd.to_numeric(df['Température'], errors='coerce').fillna(0)
        
    return df

# --- 4. AFFICHAGE DU DASHBOARD ---
st.title("⚙️ Dashboard GMAO & IoT")

try:
    df = load_data()
    
    if df.empty:
        st.warning("Le Google Sheet est vide pour le moment.")
    else:
        # --- SECTION 1 : KPIs ---
        st.header("📊 Indicateurs de Performance (KPIs)")
        
        col1, col2, col3 = st.columns(3)
        
        # KPI 1 : Dernière température enregistrée
        last_temp = df.iloc[-1]['Température']
        last_status = df.iloc[-1]['Statut']
        
        # Couleur : Rouge si "Panne", Vert/Normal si "OK" ou "Réparé"
        temp_color = "inverse" if last_status == "Panne" else "normal"
        col1.metric("Température Actuelle", f"{last_temp} °C", last_status, delta_color=temp_color)
        
        # KPI 2 : Calcul du MTTR (Temps moyen de réparation)
        interventions = df[df['Durée_Intervention_min'] > 0]
        if not interventions.empty:
            mttr = interventions['Durée_Intervention_min'].mean()
        else:
            mttr = 0
            
        col2.metric("MTTR (Temps moyen réparation)", f"{mttr:.1f} min")
        
        # KPI 3 : Nombre total de pannes
        total_pannes = len(df[df['Statut'] == 'Panne'])
        col3.metric("Total Pannes Enregistrées", total_pannes)
        
        st.markdown("---")
        
        # --- SECTION 2 : GRAPHIQUES ---
        st.header("📈 Évolution de la Température")
        
        # Graphique de température (On enlève les dates invalides pour que le graphique ne plante pas)
        chart_data = df.dropna(subset=['Date_Heure']).set_index('Date_Heure')[['Température']]
        st.line_chart(chart_data)
        
        st.markdown("---")
        
        # --- SECTION 3 : TABLEAU DES DONNÉES ---
        st.header("📋 Historique des Données Brutes")
        st.dataframe(df.iloc[::-1], use_container_width=True)
        
except Exception as e:
    st.error(f"Erreur lors de l'affichage : {e}")
