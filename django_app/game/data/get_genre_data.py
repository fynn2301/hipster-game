import pylast
import pandas as pd
from tqdm import tqdm
from decouple import config
# Last.fm API credentials
API_KEY = config('API_KEY', default='fallback-key')
API_SECRET = config('API_SECRET', default='fallback-key')

# Initialize Last.fm network
lastfm_network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET)

# Function to get track tags from Last.fm
def get_lastfm_tags(artist_name, song_title):
    try:
        track = lastfm_network.get_track(artist_name, song_title)
        tags = track.get_top_tags(limit=5)
        tag_names = [tag.item.get_name() for tag in tags]
        return tag_names
    except Exception as e:
        print(f"Error fetching Last.fm tags for '{song_title}' by '{artist_name}': {e}")
        return None
    
def process_track(row: pd.Series) -> pd.Series:
    tag_names = get_lastfm_tags(
        row['artists'],
        row['title']
    )
    # append the tags to the row and return it
    song_data = {
        "tags": tag_names
    }
    return pd.Series(song_data)


def get_lastfm_data(df: pd.DataFrame) -> pd.DataFrame:
    # Apply process_track to each row and concatenate results
    tqdm.pandas(desc="Processing Tracks")
    spotify_data = df.progress_apply(process_track, axis=1)
    # Append new columns to the original DataFrame
    df = pd.concat([df.reset_index(drop=True), spotify_data.reset_index(drop=True)], axis=1)
    return df

if __name__ == "__main__":
    chart_de_df = pd.read_csv("/Users/fynnersatz/Desktop/python/hitster/chart_data_with_spotify_usa.csv")

    chart_de_with_genre_df = get_lastfm_data(chart_de_df)

    chart_de_with_genre_df.to_csv("chart_usa_with_genre.csv", index=False)