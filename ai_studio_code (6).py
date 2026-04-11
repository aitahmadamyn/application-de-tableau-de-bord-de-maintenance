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
        # On s'assure que les colonnes ont les bons noms (selon votre capture d'écran)
        # Si vos colonnes s'appellent différemment dans Google Sheets, modifiez les noms ici
        df.rename(columns={
            'ID_machine': 'Machine_ID', 
            'Température': 'Temperature',
            'Statut': 'Status',
            'Type_Panne': 'Type_Panne',
            'Durée_Intervention_min': 'Duree_Intervention_min'
        }, inplace=True, errors='ignore')
        
        # Convertir la date pour le graphique
        df['Date_Heure'] = pd.to_datetime(df['Date_Heure'])
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
        
        # On crée 3 colonnes pour afficher les chiffres clés
        col1, col2, col3 = st.columns(3)
        
        # KPI 1 : Dernière température enregistrée
        last_temp = df.iloc[-1]['Temperature']
        last_status = df.iloc[-1]['Status']
        # On met en rouge si c'est en panne
        temp_color = "normal" if last_status == "En marche" else "inverse"
        col1.metric("Température Actuelle", f"{last_temp} °C", last_status, delta_color=temp_color)
        
        # KPI 2 : Calcul du MTTR (Temps moyen de réparation)
        # On filtre pour ne garder que les lignes où il y a eu une panne
        pannes_df = df[df['Status'] == 'Panne']
        
        if not pannes_df.empty:
            mttr = pannes_df['Duree_Intervention_min'].mean()
            total_pannes = len(pannes_df)
        else:
            mttr = 0
            total_pannes = 0
            
        col2.metric("MTTR (Temps moyen réparation)", f"{mttr:.1f} min")
        
        # KPI 3 : Nombre total de pannes
        col3.metric("Total Pannes Enregistrées", total_pannes)
        
        st.markdown("---") # Ligne de séparation
        
        # --- SECTION 2 : GRAPHIQUES ---
        st.header("📈 Évolution de la Température")
        
        # On prépare les données pour le graphique (Date en X, Température en Y)
        chart_data = df.set_index('Date_Heure')[['Temperature']]
        st.line_chart(chart_data)
        
        st.markdown("---")
        
        # --- SECTION 3 : TABLEAU DES DONNÉES ---
        st.header("📋 Historique des Données Brutes")
        # On affiche les données dans l'ordre inverse (les plus récentes en haut)
        st.dataframe(df.iloc[::-1], use_container_width=True)
        
except Exception as e:
    st.error(f"Erreur lors de l'affichage : {e}")