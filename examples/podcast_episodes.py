"""Search for a podcast then list all available episodes with stream URLs.

Run:
    python examples/podcast_episodes.py
    python examples/podcast_episodes.py "Serial"
"""
import sys
from pyheartradio import IHeartRadio

client = IHeartRadio()
query = sys.argv[1] if len(sys.argv) > 1 else "Radiolab"

print(f'Searching for podcast: "{query}"\n')

podcast = next(client.search_podcast(query), None)
if podcast is None:
    print("No results.")
    raise SystemExit(1)

print(f"  Title      : {podcast.title}")
print(f"  ID         : {podcast.id}")
print(f"  Description: {podcast.description[:120]}…")
print()

print(f"Episodes (podcast_id={podcast.id}):")
print()

for i, ep in enumerate(client.get_podcast_episodes(podcast.id), 1):
    mins, secs = divmod(ep.duration or 0, 60)
    hrs, mins = divmod(mins, 60)
    duration_str = f"{hrs}h {mins:02d}m" if hrs else f"{mins}m {secs:02d}s"
    print(f"  {i:>3}.  {ep.title}")
    print(f"        Duration : {duration_str}  (id={ep.id})")
    print(f"        Stream   : {ep.stream}")
    print()
    if i >= 5:
        print("  … (use get_podcast_episodes to iterate all)")
        break
