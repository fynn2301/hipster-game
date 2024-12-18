from decouple import config
class Connection:
    REDIRECT_URI = f"https://{config('ALLOWED_HOSTS', default='fallback-key')}/spotify_callback"
    CLIENT_ID = config('CLIENT_ID', default='fallback-key')
    CLIENT_SECRET = config('CLIENT_SECRET', default='fallback-key')