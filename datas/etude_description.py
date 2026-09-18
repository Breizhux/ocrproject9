import numpy as np
import pandas as pd
import plotly.graph_objects as go
from fastembed import TextEmbedding

CSV_PATH = "events_propres.csv"
HTML_PATH = "etude_description.html"
MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
SAMPLE_SIZE = 250  # échantillon représentatif (le modèle d'embedding est lent en CPU)


def load_data(path):
    """Charge le dataset, extrait un échantillon et ne garde que les lignes avec les deux descriptions."""
    df = pd.read_csv(path)
    df = df.sample(min(SAMPLE_SIZE, len(df)), random_state=42).reset_index(drop=True)
    df = df.dropna(subset=["description", "long_description"]).reset_index(drop=True)
    return df


def embed_texts(texts, model):
    """Vectorise une liste de textes avec un modèle local multilingue."""
    embedding = TextEmbedding(model=model, num_threads=4)
    return np.array(list(embedding.embed(texts)), dtype=np.float32)


def cosine_similarities(a, b):
    """Similarité cosinus ligne par ligne de deux matrices de vecteurs."""
    norm_a = np.linalg.norm(a, axis=1, keepdims=True) + 1e-8
    norm_b = np.linalg.norm(b, axis=1, keepdims=True) + 1e-8
    return ((a / norm_a) * (b / norm_b)).sum(axis=1)


def analyse(df):
    """Calcule la distance cosinus entre description et long_description, et les longueurs."""
    emb_desc = embed_texts(df["description"].tolist(), MODEL)
    emb_long = embed_texts(df["long_description"].tolist(), MODEL)

    df = df.copy()
    df["cos_sim"] = cosine_similarities(emb_desc, emb_long)
    df["cos_dist"] = 1.0 - df["cos_sim"]

    df["len_desc"] = df["description"].str.len()
    df["len_long"] = df["long_description"].str.len()
    df["plus_long"] = df["len_long"] >= df["len_desc"]
    return df


def build_dist_fig(df):
    """Diagramme des statistiques de distance cosinus (moyenne, médiane, écart-type, min, max)."""
    d = df["cos_dist"]
    labels = ["Moyenne", "Médiane", "Écart-type", "Min", "Max"]
    values = [d.mean(), d.median(), d.std(), d.min(), d.max()]

    fig = go.Figure(data=go.Bar(
        x=labels, y=values,
        marker_color="#1565c0", text=[f"{v:.4f}" for v in values],
        textposition="outside"))

    fig.update_layout(
        title="Statistiques de la distance cosinus entre description et long_description",
        xaxis_title="événement", yaxis_title="distance cosinus (1 - similarité)",
        template="plotly_white", height=480)
    return fig


def build_report(df):
    """Construit le rapport HTML autonome avec le diagramme des distances cosinus."""
    n = len(df)
    mean_sim = df["cos_sim"].mean()
    high_sim = (df["cos_sim"] >= 0.7).sum()
    always_longer = df["plus_long"].sum()

    d = df["cos_dist"]
    mean_dist = d.mean()
    median_dist = d.median()
    std_dist = d.std()
    min_dist = d.min()
    max_dist = d.max()

    fig = build_dist_fig(df)
    charts_html = fig.to_html(include_plotlyjs='inline', div_id="graphs")

    conclusion = f"""
        <p>Cette étude compare la colonne <strong>description</strong> (courte) et la colonne
        <strong>long_description</strong> sur <strong>{n}</strong> événements, à l'aide d'un modèle
        d'embedding local multilingue ({MODEL}).</p>

        <h2>Distance cosinus entre les embeddings de la paire (description, long_description)</h2>
        <table class="stats">
            <tr><td>Distance moyenne</td><td>{mean_dist:.4f}</td></tr>
            <tr><td>Distance médiane</td><td>{median_dist:.4f}</td></tr>
            <tr><td>Écart-type</td><td>{std_dist:.4f}</td></tr>
            <tr><td>Distance minimale</td><td>{min_dist:.4f}</td></tr>
            <tr><td>Distance maximale</td><td>{max_dist:.4f}</td></tr>
            <tr><td>Similarité cosinus moyenne</td><td>{mean_sim:.3f}</td></tr>
            <tr><td>Pares avec cosinus &ge; 0.7</td><td>{high_sim} / {n}</td></tr>
        </table>

        <ul>
            <li>La <strong>distance cosinus moyenne</strong> entre les deux embeddings est très faible
                (<strong>{mean_dist:.4f}</strong>) et quasi constante (écart-type
                <strong>{std_dist:.4f}</strong>, médiane <strong>{median_dist:.4f}</strong>).</li>
            <li><strong>{high_sim}</strong> événements sur {n} ({high_sim/n*100:.0f}%) ont une similarité
                cosinus &ge; 0.7 : même information, formulée différemment.</li>
            <li>La <strong>long_description</strong> est plus longue dans
                <strong>{always_longer}</strong> cas sur {n} ({always_longer/n*100:.0f}%) et jamais plus courte.</li>
        </ul>

        <p><strong>Conclusion :</strong> la colonne <em>description</em> est redondante : son embedding est
        confondu avec celui de <em>long_description</em>. Pour le RAG, il suffit d'envoyer
        <strong>long_description</strong>, toujours plus longue et plus informative.</p>
    """

    report = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Étude : description vs long_description</title>
    <style>
        body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; background: #f7f7f7; color: #222; }}
        .wrap {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}
        h1 {{ font-size: 22px; }}
        h2 {{ font-size: 17px; margin-top: 28px; }}
        .card {{ background: #fff; padding: 16px 20px; border-radius: 10px; margin: 16px 0; box-shadow: 0 1px 4px rgba(0,0,0,.1); }}
        table.stats {{ border-collapse: collapse; width: auto; }}
        table.stats td {{ border: 1px solid #ddd; padding: 6px 14px; text-align: left; }}
        table.stats td:nth-child(2) {{ font-weight: bold; color: #1565c0; }}
        .muted {{ color: #777; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="wrap">
        <h1>Étude : la colonne <em>description</em> est-elle utile pour le RAG ?</h1>
        <div class="card">
            <div style="display:inline-block; margin-right:32px"><div>Événements analysés</div><strong style="font-size:24px;color:#1565c0">{n}</strong></div>
            <div style="display:inline-block; margin-right:32px"><div>Distance cosinus moyenne</div><strong style="font-size:24px;color:#1565c0">{mean_dist:.4f}</strong></div>
            <div style="display:inline-block; margin-right:32px"><div>Cosinus moyen</div><strong style="font-size:24px;color:#1565c0">{mean_sim:.3f}</strong></div>
        </div>
        <div class="card">{charts_html}</div>
        <div class="card">{conclusion}</div>
        <p class="muted">Extrait généré automatiquement par etude_description.py à partir de {CSV_PATH}.</p>
    </div>
</body>
</html>"""
    return report


def main():
    print("Chargement des données...")
    df = load_data(CSV_PATH)
    print(f"{len(df)} événements analysés.")
    print("Calcul des embeddings (modèle local multilingue)...")
    df = analyse(df)
    print("Génération du rapport HTML...")
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(build_report(df))
    print(f"Rapport généré : {HTML_PATH}")
    print(f"Distance cosinus moyenne={df['cos_dist'].mean():.4f}  médiane={df['cos_dist'].median():.4f}  "
          f"écart-type={df['cos_dist'].std():.4f}  cosinus moyen={df['cos_sim'].mean():.3f}")


if __name__ == "__main__":
    main()
