import random
import requests
import time
from typing import Any
import pandas as pd
import os
def fetch_song_years(songs, fetch_full_response=False):
    base_url = "https://musicbrainz.org/ws/2/recording"
    headers = {"User-Agent": "YourAppName/1.0 (your-email@example.com)"}
    results = []

    for song in songs:
        # Construct the query
        title = song['title']
        artist = " AND ".join(f'artist:"{a}"' for a in song['artists'])
        query = f'recording:"{title}" AND {artist}'
        params = {'query': query, 'fmt': 'json'}

        try:
            # Make the API request
            response = requests.get(base_url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                # Extract the first matching recording's release year
                if data['recordings']:
                    first_recording = data['recordings'][0]
                    if fetch_full_response:
                        results.append(first_recording)
                    else:
                        # Get the release year from the first release in the list
                        if 'release-list' in first_recording and first_recording['release-list']:
                            release_date = first_recording['release-list'][0].get('date')
                            results.append(release_date.split('-')[0] if release_date else None)
                        else:
                            results.append(None)
                else:
                    results.append(None)
            else:
                results.append(None)
        except Exception as e:
            print(f"Error fetching data for '{title}' by {song['artists']}: {e}")
            results.append(None)

        # Rate-limiting: MusicBrainz allows 1 request per second for unauthenticated users
        time.sleep(1)

    return results


def set_new_current_song(request):
    all_songs: list[dict[str, Any]] = request.session.get('all_songs')
    played_songs: list[dict[str, Any]] = request.session.get('played_songs')

    possible_songs = [song for song in all_songs if song not in played_songs]
    new_song = random.choice(possible_songs)
    played_songs.append(new_song)
    request.session['played_songs'] = played_songs
    request.session['current_song'] = new_song

def get_start_songs(request):
    all_songs: list[dict[str, Any]] = request.session.get('all_songs')
    played_songs: list[dict[str, Any]] = request.session.get('played_songs')

    possible_songs = [song for song in all_songs if song not in played_songs]
    start_song0 = random.choice(possible_songs)
    played_songs.append(start_song0)

    possible_songs = [song for song in all_songs if song not in played_songs]
    start_song1 = random.choice(possible_songs)
    played_songs.append(start_song1)

    request.session['played_songs'] = played_songs

    return start_song0, start_song1

def get_playlist(start_year: int, end_year: int, genres: list[str], difficulty: float) -> pd.DataFrame:
    """
    Filter songs based on the selected settings
    df looks like this:
    id_spotify,artists,artist_spotify,title,title_spotify,match_score,year_released,year_charts,points,pos,max_pos,weeks_top10,image,country,tags,genre
    6tNQ70jh4OwmPGpYy6R2o9,Benson Boone,Benson Boone,Beautiful Things,Beautiful Things,1.000000047683716,2024,2024,343,* 3 *,1,33,https://i.scdn.co/image/ab67616d0000b273bef221ea02a821e7feeda9cf,de,"['pop', 'pop rock', 'black metal', 'emo', 'american']",['Pop']
    ...
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(BASE_DIR, "data", "song_data.csv")

    all_songs = pd.read_csv(file_path, index_col=None)
    # match score needs to be over 0.95
    all_songs = all_songs[all_songs['match_score'] > 0.95]
    # Filter by year range
    filtered_songs = all_songs[(all_songs['year_released'] >= start_year) & (all_songs['year_released'] <= end_year)]
    
    # Filter by genres
    if genres:
        filtered_songs = filtered_songs[filtered_songs['genre'].apply(lambda x: any(genre in x for genre in genres))]
    
    # filters for the points of the songs. difficulty=10 means we take the all songs, if difficulty=1 we take the 10% of the songs with the highest points of each year
    if difficulty < 10:
        filtered_songs = filtered_songs.groupby('year_released').apply(
            lambda x: x.nlargest(int(len(x) * difficulty / 10), 'points')
        ).reset_index(drop=True)

    
    return filtered_songs
