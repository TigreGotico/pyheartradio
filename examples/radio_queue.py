"""Build a play queue from station search results.

Shows how to collect multiple stations, deduplicate by stream URL,
and print a ready-to-use mpv command for each one.

Run:
    python examples/radio_queue.py
    python examples/radio_queue.py | grep mpv | bash   # actually play them
"""
from pyheartradio import IHeartRadio
from pyheartradio.models import Station

client = IHeartRadio()

QUERIES = ["jazz", "blues", "ambient"]


def build_queue(queries: list) -> list[Station]:
    seen_streams: set = set()
    queue: list[Station] = []
    for q in queries:
        for station in client.search_stations(q):
            if station.stream not in seen_streams:
                seen_streams.add(station.stream)
                queue.append(station)
    return queue


queue = build_queue(QUERIES)

print(f"Play queue ({len(queue)} stations)\n")
print(f"  {'#':<3}  {'Title':<35}  Stream URL")
print(f"  {'-'*3}  {'-'*35}  {'-'*40}")
for i, station in enumerate(queue, 1):
    short = station.stream[:55] + "…" if len(station.stream) > 55 else station.stream
    print(f"  {i:<3}  {station.title:<35}  {short}")

print()
print("mpv commands:")
for station in queue:
    print(f'  mpv --title="{station.title}" "{station.stream}"')
