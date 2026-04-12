import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import json
import io
from docx import Document
from datetime import datetime

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="GMAO Dashboard", layout="wide")

# --- FONCTION POUR GÉNÉRER LE RAPPORT DE MAINTENANCE WORD ---
def generate_maintenance_report(df):
    doc = Document()
    
    # Titre principal
    doc.add_heading('Rapport Quotidien de Maintenance (GMAO)', 0)
    
    # Date de génération
    date_generation = datetime.now().strftime("%d/%m/%Y à %H:%M")
    doc.add_paragraph(f"Rapport généré automatiquement le : {date_generation}")
    
    # --- 1. Résumé Global ---
    doc.add_heading('1. Résumé Global du Parc Machine', level=1)
    
    total_machines = df['ID_machine'].nunique()
    total_pannes = len(df[df['Statut'] == 'Panne'])
    
    interventions = df[df['Durée_Intervention_min'] > 0]
    mttr = interventions['Durée_Intervention_min'].mean() if not interventions.empty else 0
    
    p = doc.add_paragraph()
    p.add_run(f"Nombre total de machines surveillées : ").bold = True
    p.add_run(f"{total_machines}\n")
    p.add_run(f"Nombre total d'incidents (Pannes) : ").bold = True
    p.add_run(f"{total_pannes}\n")
    p.add_run(f"MTTR (Temps Moyen de Réparation) : ").bold = True
    p.add_run(f"{mttr:.1f} minutes")

    # --- 2. État Actuel des Machines ---
    doc.add_heading('2. État Actuel des Équipements', level=1)
    
    # On récupère le dernier état connu pour chaque machine
    dernier_etat = df.sort_values('Date_Heure').groupby('ID_machine').tail(1)
    
    for index, row in dernier_etat.iterrows():
        machine = row['ID_machine']
        statut = row['Statut']
        temp = row['Température']
        
        p = doc.add_paragraph(style='List Bullet')
        p.add_run(f"Machine {machine} : ").bold = True
        
        if statut == "Panne":
            p.add_run(f"EN PANNE ").bold = True
            p.add_run(f"(Cause : {row['Type_Panne']}, Température : {temp}°C)")
        else:
            p.add_run(f"Opérationnelle (Température : {temp}°C)")

    # --- 3. Historique Récent des Interventions ---
    doc.add_heading('3. Dernières Interventions Réalisées', level=1)
    
    if not interventions.empty:
        # On prend les 5 dernières interventions
        dernieres_interventions = interventions.sort_values('Date_Heure', ascending=False).head(5)
        
        for index, row in dernieres_interventions.iterrows():
            date_str = row['Date_Heure'].strftime("%d/%m/%Y %H:%M") if pd.notnull(row['Date_Heure']) else "Date inconnue"
            doc.add_paragraph(f"- Le {date_str} sur {row['ID_machine']} : {row['Type_Panne']} (Durée : {row['Durée_Intervention_min']} min)")
    else:
        doc.add_paragraph("Aucune intervention enregistrée récemment.")

    # Sauvegarde en mémoire
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 2. CONNEXION SÉCURISÉE ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["google_credentials"])
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# --- 3. LECTURE DES DONNÉES ---
@st.cache_data(ttl=10)
def load_data():
    sheet = client.open("GMAO_IoT_Data").sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    if not df.empty:
        df['Date_Heure'] = pd.to_datetime(df['Date_Heure'], format='mixed', dayfirst=True, errors='coerce')
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
        # --- BARRE LATÉRALE (SIDEBAR) ---
        st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2043/2043074.png", width=100)
        st.sidebar.header("📄 Rapport de Maintenance")
        st.sidebar.write("Générez un rapport Word résumant l'état actuel du parc machine.")
        
        # Bouton de téléchargement Word (Généré à partir des vraies données)
        word_file = generate_maintenance_report(df)
        st.sidebar.download_button(
            label="📥 Télécharger le rapport (Word)",
            data=word_file,
            file_name=f"Rapport_Maintenance_{datetime.now().strftime('%Y%m%d')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        # --- SECTION 1 : KPIs ---
        st.header("📊 Indicateurs de Performance (KPIs)")
        col1, col2, col3 = st.columns(3)
        
        last_temp = df.iloc[-1]['Température']
        last_status = df.iloc[-1]['Statut']
        temp_color = "inverse" if last_status == "Panne" else "normal"
        col1.metric("Température Actuelle", f"{last_temp} °C", last_status, delta_color=temp_color)
        
        interventions = df[df['Durée_Intervention_min'] > 0]
        mttr = interventions['Durée_Intervention_min'].mean() if not interventions.empty else 0
        col2.metric("MTTR (Temps moyen réparation)", f"{mttr:.1f} min")
        
        total_pannes = len(df[df['Statut'] == 'Panne'])
        col3.metric("Total Pannes Enregistrées", total_pannes)
        
        st.markdown("---")
        
        # --- SECTION 2 : GRAPHIQUES ---
        st.header("📈 Évolution de la Température")
        chart_data = df.dropna(subset=['Date_Heure']).set_index('Date_Heure')[['Température']]
        st.line_chart(chart_data)
        
        st.markdown("---")
        
        # --- SECTION 3 : TABLEAU DES DONNÉES ---
        st.header("📋 Historique des Données Brutes")
        st.dataframe(df.iloc[::-1], use_container_width=True)
        
except Exception as e:
    st.error(f"Erreur lors de l'affichage : {e}")
