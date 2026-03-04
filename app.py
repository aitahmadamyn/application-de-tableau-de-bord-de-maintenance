import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Dashboard Maintenance", page_icon="⚙️", layout="wide")

# --- 1. Fonctions de calcul ---
def calculer_indicateurs(df):
    if df.empty: return {}
    total_pannes = len(df)
    temps_arret_total = df['duree_arret_heures'].sum()
    temps_fonctionnement_total = df['temps_fonctionnement_heures'].sum()
    
    mttr = temps_arret_total / total_pannes if total_pannes else 0
    mtbf = temps_fonctionnement_total / total_pannes if total_pannes else 0
    periode_totale = (df['end_at'].max() - df['reported_at'].min()).total_seconds() / 3600
    disponibilite = (temps_fonctionnement_total / periode_totale) * 100 if periode_totale else 0
    
    return {
        "Total Pannes": total_pannes,
        "MTTR (h)": round(mttr, 2),
        "MTBF (h)": round(mtbf, 2),
        "Disponibilité (%)": round(disponibilite, 2)
    }

def calculer_mtbf_mttr_par_machine(df):
    result = df.groupby('name').agg(
        pannes=('name', 'count'),
        downtime_total=('duree_arret_heures', 'sum'),
        operating_total=('temps_fonctionnement_heures', 'sum')
    )
    result['MTTR'] = (result['downtime_total'] / result['pannes']).round(2)
    result['MTBF'] = (result['operating_total'] / result['pannes']).round(2)
    return result.reset_index()

def verifier_alertes(df):
    moitie = len(df) // 2
    df_p1 = df.iloc[:moitie]
    df_p2 = df.iloc[moitie:]
    
    if len(df_p1) > 0 and len(df_p2) > 0:
        mtbf_p1 = df_p1['temps_fonctionnement_heures'].sum() / len(df_p1) if len(df_p1) else 0
        mtbf_p2 = df_p2['temps_fonctionnement_heures'].sum() / len(df_p2) if len(df_p2) else 0
        mttr_p1 = df_p1['duree_arret_heures'].sum() / len(df_p1) if len(df_p1) else 0
        mttr_p2 = df_p2['duree_arret_heures'].sum() / len(df_p2) if len(df_p2) else 0
        
        if mtbf_p2 < mtbf_p1 and mtbf_p1 > 0:
            st.warning(f"⚠️ **Alerte Fiabilité :** Le MTBF a diminué récemment (de {mtbf_p1:.1f}h à {mtbf_p2:.1f}h).")
        if mttr_p2 > mttr_p1 and mttr_p1 > 0:
            st.error(f"🚨 **Alerte Inefficacité :** Le MTTR a augmenté (de {mttr_p1:.1f}h à {mttr_p2:.1f}h).")

# --- 2. Interface Utilisateur ---
st.title("📊 Tableau de Bord de Maintenance")

fichier_upload = st.file_uploader("Uploadez votre fichier Excel (.xlsx)", type=['xlsx'])

if fichier_upload is not None:
    # Lecture des noms des feuilles
    xls = pd.ExcelFile(fichier_upload)
    feuilles = xls.sheet_names
    
    st.sidebar.header("1. Sélection des feuilles")
    feuille_inter = st.sidebar.selectbox("Feuille des interventions", feuilles, index=0)
    feuille_mach = st.sidebar.selectbox("Feuille des machines", feuilles, index=min(1, len(feuilles)-1))
    
    # Chargement brut des feuilles sélectionnées
    df_inter_brut = pd.read_excel(fichier_upload, sheet_name=feuille_inter)
    df_mach_brut = pd.read_excel(fichier_upload, sheet_name=feuille_mach)
    
    cols_inter = df_inter_brut.columns.tolist()
    cols_mach = df_mach_brut.columns.tolist()
    
    st.sidebar.header("2. Correspondance des colonnes")
    st.sidebar.markdown("**Interventions**")
    col_inter_id = st.sidebar.selectbox("ID Machine", cols_inter)
    col_inter_debut = st.sidebar.selectbox("Date de début (panne)", cols_inter)
    col_inter_fin = st.sidebar.selectbox("Date de fin (réparation)", cols_inter)
    
    st.sidebar.markdown("**Machines**")
    col_mach_id = st.sidebar.selectbox("ID Machine (Machines)", cols_mach)
    col_mach_nom = st.sidebar.selectbox("Nom de la machine", cols_mach)
    
    if st.sidebar.button("Lancer l'analyse 🚀", type="primary"):
        with st.spinner('Analyse et calculs en cours...'):
            try:
                # Renommer les colonnes avec les noms standards attendus par le script
                df_inter = df_inter_brut.rename(columns={
                    col_inter_id: 'machine_id',
                    col_inter_debut: 'reported_at',
                    col_inter_fin: 'end_at'
                })
                
                df_mach = df_mach_brut.rename(columns={
                    col_mach_id: 'id',
                    col_mach_nom: 'name'
                })
                
                # Fusion et préparation
                df = pd.merge(df_inter, df_mach, left_on='machine_id', right_on='id', how='left')
                
                # Conversion des dates
                df['reported_at'] = pd.to_datetime(df['reported_at'])
                df['end_at'] = pd.to_datetime(df['end_at'])
                
                # Calcul des durées
                df['duree_arret_heures'] = (df['end_at'] - df['reported_at']).dt.total_seconds() / 3600
                df = df[df['duree_arret_heures'] > 0].sort_values('reported_at').reset_index(drop=True)
                
                df['temps_fonctionnement_heures'] = df['reported_at'].diff().dt.total_seconds() / 3600
                df.loc[0, 'temps_fonctionnement_heures'] = 0
                
                # --- Affichage des résultats ---
                verifier_alertes(df)
                
                st.header("Indicateurs Globaux")
                kpis = calculer_indicateurs(df)
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Interventions", kpis["Total Pannes"])
                col2.metric("MTBF Global", f"{kpis['MTBF (h)']} h")
                col3.metric("MTTR Global", f"{kpis['MTTR (h)']} h")
                col4.metric("Disponibilité", f"{kpis['Disponibilité (%)']} %")
                
                st.divider()
                
                df_machines = calculer_mtbf_mttr_par_machine(df)
                
                st.header("Analyse par Équipement")
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    st.subheader("MTTR par Machine")
                    fig_mttr, ax_mttr = plt.subplots(figsize=(8, 5))
                    sns.barplot(data=df_machines, x='name', y='MTTR', palette='rocket', ax=ax_mttr)
                    plt.xticks(rotation=45, ha='right')
                    st.pyplot(fig_mttr)
                    
                with col_chart2:
                    st.subheader("MTBF par Machine")
                    fig_mtbf, ax_mtbf = plt.subplots(figsize=(8, 5))
                    sns.barplot(data=df_machines, x='name', y='MTBF', palette='mako', ax=ax_mtbf)
                    plt.xticks(rotation=45, ha='right')
                    st.pyplot(fig_mtbf)
                
                st.subheader("Tableau Récapitulatif")
                df_affichage = df_machines[['name', 'pannes', 'MTTR', 'MTBF']].rename(columns={'name': 'Machine', 'pannes': 'Nombre de pannes'})
                st.dataframe(df_affichage, use_container_width=True, hide_index=True)
                
            except Exception as e:
                st.error(f"Une erreur s'est produite lors du calcul. Vérifiez que les colonnes sélectionnées sont correctes. Détail : {e}")
else:
    st.info("👋 Veuillez uploader un fichier Excel, puis configurer les colonnes dans le menu de gauche.")
