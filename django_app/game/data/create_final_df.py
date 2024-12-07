from chart_scraper import get_chart_data
from get_spotify_data import get_spotify_df
import pandas as pd
import ast
import time
genre_clusters = {
    "Pop": [
        'pop', 'dance', 'female vocalists', 'party', 'synthpop', 'electropop', 'dance-pop', 
        'happy', 'sad', 'love songs', 'romantic', 'best', 'eurodance',
        'love at first listen', 'happy hardcore'
    ],
    "Rock": [
        'rock', 'classic rock', 'soft rock', 'hard rock', 'glam rock', 'rock n roll', 'alternative rock',
        'indie', 'alternative', 'punk rock', 'punk', 'progressive rock', 'southern rock', 'Rock and Roll',
        'The Beatles', 'grunge'
    ],
    "Hip-Hop/Rap": [
        'hip hop', 'rap', 'trap', 'hip-hop', 'Deutschrap', 'german rap'
    ],
    "Electronic": [
        'electronic', 'techno', 'trance', 'electronica', 'house', 'disco', 'rave', 'Italo Disco'
    ],
    "Soul/Funk/R&B": [
        'soul', 'funk', 'motown', 'slow jams', 'new jack swing', 'r&b', 'rhythm and blues', 'rnb', 'synth pop', 'latin'
    ],
    "Country/Folk": [
        'country', 'classic country', 'folk', 'singer-songwriter', 'acoustic'
    ],
    "Schlager": [
        'Schlager', 'Deutsche Schlager', 'Deutsche Oldies', 'NDW', 'Neue Deutsche Welle', 
        'German Number 1', 'schlageroldies'
    ]
}

def ensure_unique(series, col_name):
    if series.apply(lambda x: isinstance(x, list)).all():  # Prüfen, ob alle Werte Listen sind
        unique_values = series.apply(tuple).unique()  # Listen in Tupel umwandeln für .unique()
    else:
        unique_values = series.unique()
    if len(unique_values) > 1:
        raise ValueError(f"Spalte '{col_name}' hat mehrere unterschiedliche Werte in einer Gruppe: {unique_values}")
    return unique_values[0]

def aggregate_same_id(df_songs):    
    # Aggregationslogik definieren
    aggregations_total = {
        "artists": lambda x: x.iloc[0],  # Take the first element of the group
        "artist_spotify": lambda x: ensure_unique(x, "artist_spotify"),
        "title": lambda x: x.iloc[0],   # Take the first element of the group
        "title_spotify": lambda x: ensure_unique(x, "title_spotify"),
        "match_score": lambda x: x.iloc[0],  # Take the first element of the group
        "year_released": lambda x: x.iloc[0],  # Take the first element of the group
        "year_charts": lambda x: x.iloc[0],  # Take the first element of the group
        "points": "sum",
        "pos": "min",
        "max_pos": "min",
        "weeks_top10": "sum",
        "image": lambda x: x.iloc[0],
        "country": lambda x: x.iloc[0],  # Take the first element of the group
        "tags": lambda x: x.iloc[0],  # Take the first element of the group
    }
    try:
        # `id_spotify` wird als Index verwendet und anschließend zurückgesetzt
        df_songs_sorted = df_songs.sort_values(by=["id_spotify", "year_released", "match_score"], ascending=[True, True, False])
        df_songs_filtered = df_songs_sorted.groupby("id_spotify").agg(aggregations_total).sort_values(["year_released", "points"], ascending=[False, False]).reset_index()
    except ValueError as e:
        print("Fehler bei der Gruppierung:", e)
    return df_songs_filtered

df_de = pd.read_csv("/Users/fynnersatz/Desktop/python/hitster/django/music_game/game/data/processed_data/chart_data_with_all_data_de.csv")
df_de["country"] = "de"
df_us = pd.read_csv("/Users/fynnersatz/Desktop/python/hitster/django/music_game/game/data/processed_data/chart_data_with_all_data_usa.csv")
df_us["country"] = "us"
df_songs = pd.concat([df_de, df_us], ignore_index=True)
df_songs = aggregate_same_id(df_songs)

df_songs['tags'] = df_songs['tags'].fillna('[]')
df_songs['tags'] = df_songs['tags'].apply(ast.literal_eval)

df_songs["genre"] = df_songs["tags"].apply(lambda x: [genre for genre, tags in genre_clusters.items() if any(tag in tags for tag in x)])

df_songs.to_csv(f"song_data.csv", index=False)