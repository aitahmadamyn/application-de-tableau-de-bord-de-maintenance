import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# --- 1. Configuration de la page ---
st.set_page_config(page_title="Dashboard Maintenance", page_icon="⚙️", layout="wide")


# --- 2. Fonctions de traitement des données ---
@st.cache_data  # Permet de garder les données en mémoire pour que l'app soit rapide
def charger_et_preparer_donnees(fichier):
    """Charge et nettoie le fichier Excel uploadé."""
    try:
        df_inter = pd.read_excel(fichier, sheet_name='interventions')
        df_mach = pd.read_excel(fichier, sheet_name='machines')
    except Exception as e:
        st.error(
            f"Erreur de lecture du fichier. Vérifiez que les feuilles 'interventions' et 'machines' existent. Détail : {e}")
        return None

    df_inter.columns = df_inter.columns.str.lower().str.strip()
    df_mach.columns = df_mach.columns.str.lower().str.strip()

    df = pd.merge(df_inter, df_mach, left_on='machine_id', right_on='id', how='left')

    for col in ['reported_at', 'end_at']:
        df[col] = pd.to_datetime(df[col])

    df['duree_arret_heures'] = (df['end_at'] - df['reported_at']).dt.total_seconds() / 3600
    df = df[df['duree_arret_heures'] > 0].sort_values('reported_at').reset_index(drop=True)

    df['temps_fonctionnement_heures'] = df['reported_at'].diff().dt.total_seconds() / 3600
    df.loc[0, 'temps_fonctionnement_heures'] = 0

    return df


def calculer_indicateurs(df):
    """Calcule les KPIs globaux."""
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
    """Calcule les KPIs par machine."""
    result = df.groupby('name').agg(
        pannes=('name', 'count'),
        downtime_total=('duree_arret_heures', 'sum'),
        operating_total=('temps_fonctionnement_heures', 'sum')
    )
    result['MTTR'] = (result['downtime_total'] / result['pannes']).round(2)
    result['MTBF'] = (result['operating_total'] / result['pannes']).round(2)
    return result.reset_index()


def verifier_alertes(df):
    """Compare la première moitié des données avec la seconde pour générer des alertes."""
    moitie = len(df) // 2
    df_p1 = df.iloc[:moitie]
    df_p2 = df.iloc[moitie:]

    if len(df_p1) > 0 and len(df_p2) > 0:
        mtbf_p1 = df_p1['temps_fonctionnement_heures'].sum() / len(df_p1)
        mtbf_p2 = df_p2['temps_fonctionnement_heures'].sum() / len(df_p2)

        mttr_p1 = df_p1['duree_arret_heures'].sum() / len(df_p1)
        mttr_p2 = df_p2['duree_arret_heures'].sum() / len(df_p2)

        if mtbf_p2 < mtbf_p1:
            st.warning(
                f"⚠️ **Alerte Fiabilité :** Le MTBF global a diminué récemment (de {mtbf_p1:.1f}h à {mtbf_p2:.1f}h). Une inspection préventive est recommandée.")
        if mttr_p2 > mttr_p1:
            st.error(
                f"🚨 **Alerte Inefficacité :** Le MTTR global a augmenté (de {mttr_p1:.1f}h à {mttr_p2:.1f}h). Les temps de réparation s'allongent.")


# --- 3. Interface Utilisateur (UI) ---
st.title("📊 Tableau de Bord de Maintenance Industrielle")
st.markdown(
    "Analysez automatiquement vos indicateurs de performance (MTBF, MTTR, Disponibilité) à partir de vos exports Excel.")

# Widget d'upload de fichier
fichier_upload = st.file_uploader("Uploadez votre fichier Excel (.xlsx)", type=['xlsx'])

if fichier_upload is not None:
    # Le fichier est chargé, on lance l'analyse
    with st.spinner('Analyse des données en cours...'):
        df = charger_et_preparer_donnees(fichier_upload)

    if df is not None:
        # Affichage des alertes intelligentes
        verifier_alertes(df)

        # Affichage des KPIs Globaux sous forme de cartes
        st.header("Indicateurs Globaux")
        kpis = calculer_indicateurs(df)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Interventions", kpis["Total Pannes"])
        col2.metric("MTBF Global", f"{kpis['MTBF (h)']} h")
        col3.metric("MTTR Global", f"{kpis['MTTR (h)']} h")
        col4.metric("Disponibilité", f"{kpis['Disponibilité (%)']} %")

        st.divider()

        # Préparation des données par machine
        df_machines = calculer_mtbf_mttr_par_machine(df)

        # Affichage des graphiques côte à côte
        st.header("Analyse par Équipement")
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.subheader("MTTR par Machine (Heures)")
            fig_mttr, ax_mttr = plt.subplots(figsize=(8, 5))
            sns.barplot(data=df_machines, x='name', y='MTTR', palette='rocket', ax=ax_mttr)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            st.pyplot(fig_mttr)  # Affiche le graphique dans Streamlit

        with col_chart2:
            st.subheader("MTBF par Machine (Heures)")
            fig_mtbf, ax_mtbf = plt.subplots(figsize=(8, 5))
            sns.barplot(data=df_machines, x='name', y='MTBF', palette='mako', ax=ax_mtbf)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            st.pyplot(fig_mtbf)

        # Tendance mensuelle
        st.subheader("Tendance Mensuelle des Pannes")
        df_mensuel = df.set_index('reported_at').resample('ME').size().reset_index(name='Nombre_pannes')
        fig_trend, ax_trend = plt.subplots(figsize=(10, 3))
        ax_trend.plot(df_mensuel['reported_at'], df_mensuel['Nombre_pannes'], marker='o', color='#4f46e5', linewidth=2)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        st.pyplot(fig_trend)

        st.divider()

        # Tableau récapitulatif
        st.header("Tableau Récapitulatif")
        # On renomme les colonnes pour que ce soit plus joli
        df_affichage = df_machines[['name', 'pannes', 'MTTR', 'MTBF']].rename(columns={
            'name': 'Machine',
            'pannes': 'Nombre de pannes'
        })
        st.dataframe(df_affichage, use_container_width=True, hide_index=True)

else:
    # Message affiché quand aucun fichier n'est encore uploadé
    st.info("👋 Bienvenue ! Veuillez uploader un fichier Excel pour commencer l'analyse.")