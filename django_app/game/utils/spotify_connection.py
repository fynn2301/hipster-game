
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
        scope = "user-modify-playback-state user-read-playback-state streaming"
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
    
    def resume(self, device_id: str = None) -> None:
        """
        Resumes the playback on a specified device.
        """
        if not self.access_token:
            raise Exception("Access Token not set.")
        
        url = "https://api.spotify.com/v1/me/player/play"
        if device_id:
            url += f"?device_id={device_id}"

        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.put(url, headers=headers)
        if response.status_code == 204:
            print("Playback resumed.")
        else:
            print(f"Error resuming playback: {response.status_code} - {response.text}")


    def play_track(self, track_id: str, device_id: str = None) -> None:
        if not self.access_token:
            raise Exception("Access Token not set.")

        url = "https://api.spotify.com/v1/me/player/play"
        if device_id:
            url += f"?device_id={device_id}"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "uris": [f"spotify:track:{track_id}"]
        }
        response = requests.put(url, headers=headers, json=data)
        if response.status_code != 204:
            print(f"Error playing track: {response.status_code} - {response.text}")


    def stop(self, device_id: str = None) -> None:
        """
        Pauses the current playback on a specified device.
        """
        if not self.access_token:
            raise Exception("Access Token not set.")
        
        url = "https://api.spotify.com/v1/me/player/pause"
        if device_id:
            url += f"?device_id={device_id}"

        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.put(url, headers=headers)
        if response.status_code == 204:
            print("Playback paused.")
        else:
            print(f"Error pausing playback: {response.status_code} - {response.text}")



    def is_playing(self, device_id: str = None) -> bool:
        """
        Checks if a song is currently playing on a specific device.
        
        :param device_id: Optional Spotify device ID to check playback status.
        :return: True if a song is playing, False otherwise.
        """
        if not self.access_token:
            raise Exception("Access Token not set. Please retrieve the token using `get_spotify_token`.")
        
        url = "https://api.spotify.com/v1/me/player"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            is_playing = data.get("is_playing", False)

            if device_id:
                active_device = data.get("device", {}).get("id")
                if active_device == device_id:
                    return is_playing
                else:
                    print("The specified device is not currently active.")
                    return False
            
            # If no device_id is provided, return the overall playback state
            return is_playing
        elif response.status_code == 204:
            # 204 indicates no active device
            print("No active device found.")
            return False
        else:
            print(f"Error retrieving playback status: {response.status_code} - {response.text}")
            return False
