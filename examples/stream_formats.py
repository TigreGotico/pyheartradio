"""Stream formats — inspecting all available formats for a station.

iHeartRadio stations broadcast in multiple formats simultaneously
(shoutcast, MP3, AAC, HLS). pyheartradio selects the preferred format
via _STREAM_FORMAT_PREFERENCE and stores it in station.stream.
station.streams holds the full dict so you can pick a specific format.

Run:
    python examples/stream_formats.py
    python examples/stream_formats.py "NPR"
"""
import sys
from pyheartradio import IHeartRadio

client = IHeartRadio()
query = sys.argv[1] if len(sys.argv) > 1 else "jazz"

print(f'Searching for stations: "{query}"\n')

for station in client.search_stations(query, max_results=3):
    print(f"  {station.title}")
    print(f"  Preferred stream : {station.stream}")
    if len(station.streams) > 1:
        print(f"  All formats ({len(station.streams)}):")
        for fmt, url in station.streams.items():
            marker = " ← selected" if url == station.stream else ""
            print(f"    {fmt:<28}  {url}{marker}")
    print()

# --- Picking a specific format ---
print("Picking a specific format:")
print()

FORMAT_PREFERENCE = {
    "hls": ["hls_stream"],
    "mp3": ["shoutcast_stream", "secure_shoutcast_stream", "mp3"],
    "aac": ["aac_stream", "stw_stream"],
}

station = next(client.search_stations(query, max_results=1), None)
if station:
    for label, keys in FORMAT_PREFERENCE.items():
        url = next((station.streams[k] for k in keys if k in station.streams), None)
        status = url if url else "(not available)"
        print(f"  {label.upper():<6} → {status}")

print()
print("Tip: pass any stream URL directly to mpv, ffmpeg, or VLC:")
if station:
    print(f'  mpv "{station.stream}"')
