from flask import Flask, render_template, request, redirect, url_for
import re
import logging
import json
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from youtubesearchpython import SearchVideos
import yt_dlp as ydlp

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

SPOTIPY_CLIENT_ID = 'f1e38febf2a44e8b8aad24194ff20df4'
SPOTIPY_CLIENT_SECRET = '14bcca4dde9341708c2d0d7783cf8c3f'
client_credentials_manager = SpotifyClientCredentials(
    client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def validate_url(sp_url):
    if re.search(r"^(https?://)?open\.spotify\.com/(playlist|track)/.+$", sp_url):
        return sp_url
    raise ValueError("Invalid Spotify URL")

def get_track_info(track):
    return {
        "artist_name": track["artists"][0]["name"],
        "track_title": track["name"]
    }

def get_playlist_info(sp_playlist):
    playlist = sp.playlist_tracks(sp_playlist)
    tracks = [item["track"] for item in playlist["items"]]
    return [get_track_info(track) for track in tracks]

def search_youtube(song_name):
    try:
        search = SearchVideos(song_name, offset=1, mode="json", max_results=1)
        results = search.result()

        results_dict = json.loads(results)
        video_info = results_dict['search_result'][0] if 'search_result' in results_dict else None

        if video_info:
            return {
                "link": video_info['link'],
                "poster": video_info['thumbnails'][0]
            }
        return None

    except Exception as e:
        logging.error(f"Error searching for {song_name} on YouTube. Reason: {e}")
        return None

def download_song_with_yt_dlp(link, download_path):
    ydl_opts = {
        'outtmpl': f'{download_path}/%(title)s.%(ext)s'
    }
    
    with ydlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search_songs():
    url = request.form.get('spotify_url')
    try:
        url = validate_url(url)
    except ValueError:
        return "Invalid Spotify URL", 400

    if "track" in url:
        track = sp.track(url)
        songs_info = [get_track_info(track)]
    elif "playlist" in url:
        songs_info = get_playlist_info(url)
    else:
        return "Invalid Spotify URL type. Supported types are track and playlist.", 400

    track_infos = [] 
    for track_info in songs_info:
        youtube_data = search_youtube(f"{track_info['artist_name']} - {track_info['track_title']}")
        if youtube_data:
            track_info['link'] = youtube_data['link']
            track_info['poster'] = youtube_data['poster']
            track_infos.append(track_info)

    return render_template('results.html', track_infos=track_infos)

@app.route('/download', methods=['POST'])
def download_song():
    links = request.form.getlist('youtube_links')  
    download_path = "./downloads"  
    for link in links:
        download_song_with_yt_dlp(link, download_path)
    return "Downloaded successfully! ", 200

if __name__ == '__main__':
    app.run(debug=True)
