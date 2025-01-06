import pyaudio
import struct
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib as mpl
import time
from tkinter import TclError
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import syncedlyrics
import re
import matplotlib.patheffects as pe

clientID = '' #put your own clientID
clientSecret = '' #put your own clientSecret
redirectURI = 'https://localhost:8080/'
scope = "user-read-currently-playing"

spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=clientID, client_secret=clientSecret, redirect_uri=redirectURI, scope=scope))

oldTrack = None
prev_time_changesong = time.time()
parsed_lyrics = None
prev_lyrics = None

def parse_lyrics(lyrics_data):
    parsed_lyrics = []
    lines = lyrics_data.splitlines()
    for line in lines:
        match = re.match(r"\[(\d+):(\d+\.\d+)\] (.+)", line)
        if match:
            minutes = int(match.group(1))
            seconds = float(match.group(2))
            lyrics = match.group(3)
            timestamp_ms = minutes * 60000 + seconds * 1000
            parsed_lyrics.append((timestamp_ms, lyrics))
    return parsed_lyrics

def get_lyrics_at_time(parsed_lyrics, time):
    previous_lyrics = None
    for timestamp_ms, lyrics in parsed_lyrics:
        if time < timestamp_ms:
            return previous_lyrics
        previous_lyrics = lyrics
    
    return previous_lyrics 

#remove toolbar
mpl.rcParams['toolbar'] = 'None'

# matplotlib.use('TkAgg')
plt.style.use('dark_background')

# create matplotlib figure and axes
fig, ax = plt.subplots(1, figsize=(15, 7))
plt.axis('off')

def truncate_colormap(cmap, min_val=0.0, max_val=1.0, n=100):
    """
    Truncate the color map according to the min_val and max_val from the
    original color map.
    """
    new_cmap = colors.LinearSegmentedColormap.from_list(
        'trunc({n},{a:.2f},{b:.2f})'.format(n=cmap.name, a=min_val, b=max_val),
        cmap(np.linspace(min_val, max_val, n)))
    return new_cmap

def colormap():
    return colors.LinearSegmentedColormap.from_list("lime_to_red", ["lime", "red"])

# constants for the audio stream
CHUNK = 1024 * 2             # samples per frame
FORMAT = pyaudio.paInt16     # audio format (bytes per sample?)
CHANNELS = 1                 # single channel for microphone
RATE = 48000                 # samples per second

p = pyaudio.PyAudio()

# get list of availble inputs
info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')
for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            print ("input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))

# select input
audio_input = input("\n\nSelect input by Device id: ")

# stream object to get data from microphone
stream = p.open(
    input_device_index=int(audio_input),
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    output=True,
    frames_per_buffer=CHUNK
)

print('stream started')

# variable for plotting
x = np.arange(0, 2 * CHUNK, 128)
w = 100
max_y = 60
gradient_images = [] 
song_title = []
song_lyrics = []

# create a rectobject with random data
rects = ax.bar(x, [0 for i in range(CHUNK//64)], width=w, color='lime')

# basic formatting for the axes
ax.set_ylim(0, max_y)
ax.set_xlim(0, 2 * CHUNK)
plt.setp(ax, xticks=[0, CHUNK, 2 * CHUNK], yticks=[0,max_y])

# show the plot
plt.show(block=False)

grad = np.atleast_2d(np.linspace(0, 1, 20)).T

def update_text(list, string, string2=None, x=CHUNK, y=0, fontsize=20, color='white', zorder=0, ha='center', va='center', font = 'Arial', path_effects=None, wrap=True):
    while list:
        list.pop().remove()
    list.append(ax.text(x, y, string, fontsize=fontsize, color=color, zorder=zorder, ha=ha, va=va, font=font, path_effects=path_effects, wrap=wrap))
    if string2:
        list.append(ax.text(x, y-3, string2, fontsize=fontsize-10, color=color, zorder=zorder, ha=ha, va=va, font=font, path_effects=path_effects, wrap=wrap))

while True:
    time.sleep(0.01)
    current_time = time.time()
    if current_time - prev_time_changesong > 1:
        currentTrack = spotify.currently_playing()
        item = currentTrack['item'] if currentTrack else None
        if item:
            track = currentTrack['item']['name']
            artist = currentTrack['item']['artists'][0]['name']
            if parsed_lyrics:
                song_progress = currentTrack['progress_ms']
                lyrics = get_lyrics_at_time(parsed_lyrics, song_progress)
                if lyrics != prev_lyrics and lyrics:
                    update_text(song_lyrics, lyrics.upper(), x=CHUNK, y=max_y//2, fontsize=120, zorder=0, color=(0.4,0.4,0.4), font='Impact', path_effects=[pe.withStroke(linewidth=10, foreground="black")])
                    prev_lyrics = lyrics
            if track != oldTrack:
                if song_lyrics:
                    while song_lyrics:
                        song_lyrics.pop().remove()
                lyrics_and_time = syncedlyrics.search(f"{track} {artist}") 
                if lyrics_and_time:
                    parsed_lyrics = parse_lyrics(lyrics_and_time)
                else:
                    parsed_lyrics = None
                update_text(song_title, track.upper(), artist.upper(), x=CHUNK, y=1, fontsize=30, zorder=2, path_effects=[pe.withStroke(linewidth=20, foreground=(0,0,0,0.5))])
                oldTrack = track
                
        else:
            while song_title:
                song_title.pop().remove()
            while song_lyrics:
                song_lyrics.pop().remove()
        prev_time_changesong = current_time

    # binary data
    # binary data
    data = stream.read(CHUNK, exception_on_overflow=False)

    # convert data to integers, make np array
    data_int = struct.unpack(str(CHUNK) + 'h', data)
    data_np = np.array(data_int, dtype='int16')
    data_np = (data_np / 32768.0) * 128  # Normalize

    while gradient_images:
        img = gradient_images.pop()
        img.remove()

    # update plot
    for i, bar in enumerate(rects):
        height = data_np[i]
        bar.set_facecolor("none")
        c_map = truncate_colormap(colormap(), min_val=0,
                                    max_val=height/max_y)
        x, _ = bar.get_xy()  # get the corners
        img = ax.imshow(grad, extent=[x, x+w, height, 0], aspect="auto",
              cmap=c_map, zorder=1)
        gradient_images.append(img)
        bar.set_height(height)

    # update figure canvas
    fig.canvas.draw()
    fig.canvas.flush_events()
    
    
