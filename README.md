## Flaskaraoke

This is a very basic script and Flask-based web app that automates the process of...

- Downloading a music video from YouTube,
- Extracting the audio
- Removing vocals from the audio
- Reintegrating the non-vocal audio back into the video file
- Creating an ASS subtitle file and trying to sync the video with the lyrics
 
If using the Flask web-app, you can also play the video with the option of re-introducing the original lyrics, either at reduced or full volume. There's also a UI to adjust the lyric sync if the system has failed to determine it automatically.

## Requirements

Needs FFMPEG for video and audio conversion.
Uses Spleeter for audio stripping - the files for 2-stem audio extraction are required
Uses PyTube for YouTube downloading
Uses Flask for the web service

## Running

On Windows, ensure all Python pre-requisites are installed.
Download FFMPEG and copy both FFMPEG.exe and FFPROBE.exe to the application folder.
Use the *spleeter* tool once from the app folder to download the required files - use the Quick Start example from https://github.com/deezer/spleeter
Edit the *run.bat* file to point to your Python installation
Double-click *run.bat*, and visit http://localhost:5000 in your web-browser


