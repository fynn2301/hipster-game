
import requests
import time
class SpotifyConnection:

    # Used before connection
    def __init__(self,client_id, client_secret, redirect_uri, access_token=None) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = access_token

    def to_dict(self):
        """Serialize the connection to a dictionary."""
        return {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'access_token': self.access_token
        }

    @classmethod
    def from_dict(cls, data):
        """Reconstruct the connection from a dictionary."""
        return cls(
            client_id=data.get('client_id'),
            client_secret=data.get('client_secret'),
            redirect_uri=data.get('redirect_uri'),
            access_token=data.get('access_token')
        )
    
    def get_spotify_auth_url(self) -> str:
        scope = "user-read-playback-state user-modify-playback-state streaming"
        return (
            f"https://accounts.spotify.com/authorize"
            f"?client_id={self.client_id}"
            f"&response_type=code"
            f"&redirect_uri={self.redirect_uri}"
            f"&scope={scope}"
        )

    # Access Token abrufen
    def get_spotify_token(self, auth_code: str) -> str:
        token_url = "https://accounts.spotify.com/api/token"
        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data["access_token"]
            return token_data["access_token"]
        else:
            response.raise_for_status()
        
    def get_songs_info_from_playlists(self, playlists_ids: dict[str, str]) -> list[dict]:
        """
        Retrieves song information (ID, title, artists, year) from the given playlists.

        :param playlists_ids: A list of playlist IDs
        :return: A list of dictionaries with song information
        """
        if not self.access_token:
            raise Exception("Access Token is not set. Please retrieve the token using `get_spotify_token`.")

        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        songs = []

        for play_list, playlist_id in playlists_ids.items():
            url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
            
            while url:
                print(url)
                response = requests.get(url, headers=headers)

                # Handle rate limiting or other errors
                if response.status_code == 429:  # Rate limited
                    retry_after = int(response.headers.get("Retry-After", 1))  # Default to 1 second
                    print(f"Rate limited. Retrying after {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue  # Retry the same request

                if response.status_code != 200:
                    raise Exception(f"Failed to fetch data: {response.status_code} - {response.text}")

                data = response.json()

                # Extract song details
                for item in data.get("items", []):
                    track = item.get("track")
                    if track:
                        song = {
                            "id": track["id"],
                            "title": track["name"],
                            "artists": [artist["name"] for artist in track["artists"]],
                            "year": track["album"]["release_date"][:4] if track["album"]["release_date"] else "Unknown",
                            "image": track["album"]["images"][0]["url"],
                            "playlist": play_list,
                        }
                        songs.append(song)

                # Get the next page URL (if available)
                url = data.get("next")

        return songs
    
    def resume(self) -> None:
        """
        Resumes the playback.
        """
        if not self.access_token:
            raise Exception("Access Token ist nicht gesetzt. Bitte Token mit `get_spotify_token` abrufen.")
        
        url = "https://api.spotify.com/v1/me/player/play"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.put(url, headers=headers)
        if response.status_code == 204:
            print("Wiedergabe wurde fortgesetzt.")
        else:
            print(f"Fehler beim Fortsetzen der Wiedergabe: {response.status_code} - {response.text}")

    def play_track(self, track_id: str) -> None:
            """
            Spielt einen Song im aktiven Spotify-Player ab.

            :param track_id: Die ID des Songs, der abgespielt werden soll.
            """
            if not self.access_token:
                raise Exception("Access Token ist nicht gesetzt. Bitte Token mit `get_spotify_token` abrufen.")
            
            url = "https://api.spotify.com/v1/me/player/play"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            data = {
                "uris": [f"spotify:track:{track_id}"]
            }

            response = requests.put(url, headers=headers, json=data)
            if response.status_code == 204:
                print(f"Track {track_id} wird abgespielt.")
            else:
                print(f"Fehler beim Abspielen des Tracks: {response.status_code} - {response.text}")

    def stop(self) -> None:
        """
        Pauses the current playback.
        """
        if not self.access_token:
            raise Exception("Access Token ist nicht gesetzt. Bitte Token mit `get_spotify_token` abrufen.")
        
        url = "https://api.spotify.com/v1/me/player/pause"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.put(url, headers=headers)
        if response.status_code == 204:
            print("Wiedergabe wurde gestoppt.")
        else:
            print(f"Wiedergabe wurde gestoppt: {response.status_code} - {response.text}")

    def play_from_start(self, track_id: str) -> None:
        """
        Plays the track from the beginning.
        """
        if not self.access_token:
            raise Exception("Access Token ist nicht gesetzt. Bitte Token mit `get_spotify_token` abrufen.")
        
        url = "https://api.spotify.com/v1/me/player/play"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "uris": [f"spotify:track:{track_id}"],
            "position_ms": 0  # Starts the track from the beginning
        }

        response = requests.put(url, headers=headers, json=data)
        if response.status_code == 204:
            print(f"Track {track_id} wird von Anfang an abgespielt.")
        else:
            print(f"Fehler beim Abspielen des Tracks: {response.status_code} - {response.text}")

    def is_playing(self) -> bool:
        """
        Checks if a song is currently playing.

        :return: True if a song is playing, False if paused.
        """
        if not self.access_token:
            raise Exception("Access Token ist nicht gesetzt. Bitte Token mit `get_spotify_token` abrufen.")
        
        url = "https://api.spotify.com/v1/me/player"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("is_playing", False)  # Returns False if "is_playing" is missing
        elif response.status_code == 204:
            # 204 indicates no active device
            print("Es ist kein aktives Gerät verbunden.")
            return False
        else:
            print(f"Fehler beim Abrufen des Player-Status: {response.status_code} - {response.text}")
            return False
