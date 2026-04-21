import pandas as pd
import matplotlib.pyplot as plt

# Charger les données
df = pd.read_csv("benchmark.csv")

print("Aperçu des données :")
print(df.head())

# ── 1. Sélection intelligente des colonnes de durée ───────────────
# On garde uniquement les colonnes qui commencent par "t_"
time_columns = [col for col in df.columns if col.startswith("t_")]

time_df = df[time_columns]

print("\nColonnes de temps détectées :")
print(time_columns)

# ── 2. Moyennes des temps ─────────────────────────────────────────
mean_times = time_df.mean()

print("\nTemps moyens (en secondes) :")
print(mean_times)

# ── 3. Graphique des temps moyens ─────────────────────────────────
plt.figure()
mean_times.plot(kind='bar')
plt.title("Temps moyen par étape du traitement")
plt.ylabel("Temps (secondes)")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# ── 4. Temps total par segment ────────────────────────────────────
if "t_total_s" in df.columns:
    plt.figure()
    plt.plot(df["t_total_s"])
    plt.title("Temps total par segment")
    plt.xlabel("Segment")
    plt.ylabel("Temps (s)")
    plt.tight_layout()
    plt.show()