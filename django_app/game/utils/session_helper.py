
from game.config.config import Connection
from game.utils.spotify_connection import SpotifyConnection

def initialize_session() -> SpotifyConnection:
    config = Connection()
    return SpotifyConnection(
            config.CLIENT_ID, config.CLIENT_SECRET, config.REDIRECT_URI
        )
    