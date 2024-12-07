import os
import time
import re
from decouple import config
import pandas as pd
import unicodedata
import random
import logging
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, field
from tqdm import tqdm
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.exceptions import SpotifyException

from sentence_transformers import SentenceTransformer, util
from unidecode import unidecode

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the BERT model
model = SentenceTransformer('all-MiniLM-L6-v2')  # You can choose a more powerful model if needed

# Constants
SIMILARITY_THRESHOLD = 0.95
MAX_WORKERS = 5  # Adjust based on your system's capabilities

# Data class for songs
@dataclass
class Song:
    title_spotify: Optional[str] = None
    artist_spotify: List[str] = field(default_factory=list)
    id_spotify: Optional[str] = None
    match_score: float = 0.0
    image: Optional[str] = None

# Text normalization and cleaning
STANDARDIZATIONS = {
    "p!nk": "pink",
    "feat.": "&",
    "featuring": "&",
    "*nsync": "nsync",
    "senorita": "señorita",  # Reverse for common cases
    "d-12": "d12",
    # Add more standardizations as needed
}

CONNECTORS = [
    r'\bfeat\b', r'\bfeaturing\b', r'\bft\b', r'&', r'\band\b',
    r'\bwith\b', r'\bvs\b', r'\bversus\b', r'\bplus\b', r',', r'\bx\b', r'\+'
]

# Cache for embeddings
@lru_cache(maxsize=10000)
def bert_encode_cached(text: str):
    return model.encode(text, convert_to_tensor=True)

def normalize_text(text: str) -> str:
    """
    Normalize input text by removing accents, special characters, and standardizing variations.
    """
    text = text.lower()
    text = unidecode(text)
    for key, value in STANDARDIZATIONS.items():
        text = text.replace(key, value)
    text = re.sub(r'\([^)]*\)', '', text)  # Remove parenthetical information
    text = re.sub(r"[^\w\s]", "", text)    # Remove special characters
    text = re.sub(r"\s+", " ", text)       # Replace multiple spaces with a single space
    return text.strip()

def clean_spotify_title(title: str) -> Tuple[str, List[str]]:
    """
    Clean the Spotify track title and extract any featured artists.
    """
    match = re.search(r"\((?:feat\.|featuring)\s([^)]*)\)", title, re.IGNORECASE)
    if match:
        artists_raw = match.group(1)
        artists = re.split(r",|\band\b|&", artists_raw)
        artists = [artist.strip() for artist in artists]
        cleaned_title = re.sub(r"\((?:feat\.|featuring)\s[^)]*\)", "", title, flags=re.IGNORECASE).strip()
    else:
        cleaned_title = title.strip()
        artists = []
    return cleaned_title, artists

def clean_query_artists(query_artists: str) -> str:
    """
    Clean the artist string from the query.
    """
    pattern = re.compile('|'.join(CONNECTORS), re.IGNORECASE)
    cleaned_query = pattern.sub('', query_artists)
    cleaned_query = re.sub(' +', ' ', cleaned_query).strip()
    return cleaned_query

def calculate_similarity_bert(
    query_title: str,
    query_artists: str,
    spotify_title: str,
    spotify_artists: List[str]
) -> float:
    """
    Calculate similarity between query and Spotify data using BERT embeddings.
    """
    # Normalize and encode texts
    query_title_norm = normalize_text(query_title)
    query_artists_norm = normalize_text(query_artists)
    spotify_title_norm = normalize_text(spotify_title)
    spotify_artists_norm = normalize_text(' '.join(spotify_artists))

    # Encode using cached function
    query_embedding_title = bert_encode_cached(query_title_norm)
    spotify_embedding_title = bert_encode_cached(spotify_title_norm)

    query_embedding_artists = bert_encode_cached(query_artists_norm)
    spotify_embedding_artists = bert_encode_cached(spotify_artists_norm)

    # Calculate cosine similarities
    similarity_title = util.cos_sim(query_embedding_title, spotify_embedding_title).item()
    similarity_artists = util.cos_sim(query_embedding_artists, spotify_embedding_artists).item()

    # Weighted similarity
    weighted_similarity = 0.7 * similarity_title + 0.3 * similarity_artists
    return weighted_similarity

def get_result_track(
    results: Dict[str, Any],
    query_artists: str,
    query_title: str
) -> Song:
    """
    Process Spotify API search results to find the best matching track.
    """
    best_song = Song()
    best_score = 0.0
    if results['tracks']['items']:
        for track in results['tracks']['items']:
            spotify_artists = [artist["name"] for artist in track['artists']]
            spotify_title = track['name']
            score = calculate_similarity_bert(query_title, query_artists, spotify_title, spotify_artists)
            if score > best_score:
                best_score = score
                best_song = Song(
                    title_spotify=spotify_title,
                    artist_spotify=spotify_artists,
                    id_spotify=track['id'],
                    match_score=score,
                    image=track["album"]["images"][0]["url"] if track["album"]["images"] else None
                )
                if best_score >= SIMILARITY_THRESHOLD:
                    break  # High-confidence match found
    return best_song

def get_spotify_client() -> spotipy.Spotify:
    """
    Initialize Spotify client with credentials from environment variables.
    """
    client_credentials_manager = SpotifyClientCredentials(
        client_id = config('CLIENT_ID', default='fallback-key'),
        client_secret = config('CLIENT_SECRET', default='fallback-key')
    )
    return spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def search_track(
    sp: spotipy.Spotify,
    artist_charts: str,
    title_charts: str,
    query_year: Optional[int] = None,
    retries: int = 5,
    delay: int = 2
) -> Song:
    """
    Search for a specific track on Spotify, with retry logic for rate-limiting.
    """
    best_song = Song()
    best_score = 0.0
    query_artist_clean = clean_query_artists(artist_charts)
    queries = [
        f"{title_charts} {artist_charts}",
        f"track:{title_charts} artist:{artist_charts}",
        f"{artist_charts} {title_charts}",
        f"{title_charts} {query_year}" if query_year else f"{title_charts}",
    ]
    for query in queries:
        for attempt in range(retries):
            try:
                results = sp.search(q=query, type='track', limit=10)
                song = get_result_track(results, query_artist_clean, title_charts)
                if song.match_score > best_score:
                    best_score = song.match_score
                    best_song = song
                    if best_score >= SIMILARITY_THRESHOLD:
                        return best_song  # High-confidence match found
                break
            except SpotifyException as e:
                logger.error(f"Spotify API error: {e}")
                sleep_time = delay * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(sleep_time)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                break  # Exit retry loop on unexpected errors
    return best_song

def process_track(row: pd.Series) -> pd.Series:
    sp = get_spotify_client()
    song = search_track(
        sp,
        row['artists'],
        row['title'],
        row.get("year_released", None)
    )
    # Convert Song object to Series
    song_data = {
        'title_spotify': song.title_spotify,
        'artist_spotify': ', '.join(song.artist_spotify) if song.artist_spotify else None,
        'id_spotify': song.id_spotify,
        'match_score': song.match_score,
        'image': song.image
    }
    return pd.Series(song_data)

def get_spotify_df(df: pd.DataFrame) -> pd.DataFrame:
    # Apply process_track to each row and concatenate results
    tqdm.pandas(desc="Processing Tracks")
    spotify_data = df.progress_apply(process_track, axis=1)
    # Append new columns to the original DataFrame
    df = pd.concat([df.reset_index(drop=True), spotify_data.reset_index(drop=True)], axis=1)
    return df

# Example usage
if __name__ == "__main__":
    # Load your DataFrame
    chart_usa_df = pd.read_csv("/Users/fynnersatz/Desktop/python/hitster/django/music_game/game/data/raw_usa/chart_data_usa.csv")

    # Process the DataFrame and append Spotify data
    chart_usa_df = get_spotify_df(chart_usa_df[2282:])

    # Save to CSV or further processing
    chart_usa_df.to_csv("chart_data_with_spotify_usa2.csv", index=False)

