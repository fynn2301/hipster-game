from django.shortcuts import render, redirect
from django.shortcuts import render
from game.utils.session_helper import initialize_session
from game.utils.spotify_connection import SpotifyConnection
from django.http import HttpResponse
from game.utils.mapping import Mappings
from game.utils.helpers import set_new_current_song, get_start_songs, fetch_song_years, get_playlist
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import cache_page
import pandas as pd
import ast

def connect_to_spotify(request):
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "connect":
            # SpotifyConnection initialisieren
            spotify_connection = initialize_session()
            request.session['spotify_connection'] = spotify_connection.to_dict()

            # Authentifizierungs-URL abrufen
            auth_url = spotify_connection.get_spotify_auth_url()

            # Weiterleitung zur Spotify-Auth-Seite
            return redirect(auth_url)

    return render(request, 'connect.html')

def spotify_callback(request):
    auth_code = request.GET.get("code")  # Der von Spotify zurückgegebene Auth-Code
    serialized_connection = request.session.get('spotify_connection')
    if not serialized_connection:
        return None
    spotify_connection = SpotifyConnection.from_dict(serialized_connection)

    # Access Token abrufen
    try:
        access_token = spotify_connection.get_spotify_token(auth_code)
        spotify_connection.access_token = access_token
        request.session['spotify_connection'] = spotify_connection.to_dict()
    except Exception as e:
        return HttpResponse(f"Fehler beim Abrufen des Tokens: {str(e)}", status=500)

    # Weiterleitung zu einer anderen Seite (z. B. Auswahlseite)
    return redirect('select_settings')

def select_settings(request):
    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'show_start_cards':
            start_year = int(request.POST.get('start_decade', 1900))
            end_year = int(request.POST.get('end_decade', 2020))
            difficulty = float(request.POST.get('difficulty', 5))
            genres = request.POST.getlist('genres', ['Pop', 'Rock', 'Soul/Funk/R&B', 'Hip-Hop/Rap', 'Electronic', 'Schlager', 'Country/Folk'])
            df_songs_de_filters = get_playlist(start_year, end_year, genres, difficulty)
            request.session['all_songs'] = df_songs_de_filters.to_dict('records')
            request.session['played_songs'] = []
            return redirect('start_cards')
    
    return render(request, 'select_settings.html')
def start_cards(request):
    serialized_connection = request.session.get('spotify_connection')
    if not serialized_connection:
        return None
    spotify_connection = SpotifyConnection.from_dict(serialized_connection)
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == 'play_first_song':
            set_new_current_song(request)
            return redirect('music_player')
    # You can pass context if needed; here it's an empty dictionary
    song0, song1 = get_start_songs(request)
    return render(request, 'start_cards.html', {"song0": song0, "song1": song1})

playing = None
def music_player(request):
    global playing
    # connection
    serialized_connection = request.session.get('spotify_connection')
    if not serialized_connection:
        return JsonResponse({"error": "No Spotify connection found."}, status=400)
    spotify_connection = SpotifyConnection.from_dict(serialized_connection)
    # get song
    current_song = request.session.get('current_song')
    if not current_song:
        return JsonResponse({"error": "No song is currently loaded."}, status=400)

    play_pause_label = "Play"
    

    if request.method == "POST":
        action = request.POST.get('action', None)
        if not action:
            return JsonResponse({"error": "No action provided."}, status=400)

        # Handle actions
        play_pause_label = "Pause"  # Default label
        device_id = request.session.get('spotify_device_id')  # May be None if not set yet
        if action == "play_pause":
            if playing is True:
                spotify_connection.stop(device_id=device_id)
                play_pause_label = "Play"
                playing = False
            elif playing is False:
                spotify_connection.resume(device_id=device_id)
                play_pause_label = "Pause"
                playing = True
            else:
                spotify_connection.play_track(current_song["id_spotify"], device_id=device_id)
                play_pause_label = "Pause"
                playing = True


        elif action == "repeat":
            playing = True
            spotify_connection.play_track(current_song["id_spotify"], device_id=device_id)
            play_pause_label = "Pause"

        elif action == "next_song":
            playing = True
            set_new_current_song(request)
            current_song = request.session.get('current_song')
            device_id = request.session.get('spotify_device_id')  # May be None if not set yet
            spotify_connection.play_track(current_song["id_spotify"], device_id=device_id)
            play_pause_label = "Pause"
        return JsonResponse({
            "current_song": {
                "title": current_song["title"],
                "artists": current_song["artists"],
                "year": current_song["year_released"],
                "image": current_song["image"],
            },
            "spotify_access_token": spotify_connection.access_token,
        })

    return render(request, 'music_player.html', {
        "current_song": {
            "title": current_song["title"],
            "artists": current_song["artists"],
            "year": current_song["year_released"],
            "image": current_song["image"],
        },
        "play_pause_label": play_pause_label,
        "spotify_access_token": spotify_connection.access_token,
    })


import logging

logger = logging.getLogger(__name__)

def store_device_id(request):
    if request.method == 'POST':
        logger.info("Received POST request")
        device_id = request.POST.get('device_id')
        logger.info(f"Device ID: {device_id}")
        request.session['spotify_device_id'] = device_id
        current_song = request.session.get('current_song')
        serialized_connection = request.session.get('spotify_connection')
        if not serialized_connection:
            logger.error("No Spotify connection found.")
            return JsonResponse({"error": "No Spotify connection found."}, status=400)
        spotify_connection = SpotifyConnection.from_dict(serialized_connection)
        spotify_connection.play_track(current_song["id_spotify"], device_id=device_id)
        return JsonResponse({"status": "okay"})
    return JsonResponse({"error": "Invalid request method"}, status=405)
