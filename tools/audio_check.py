
from __future__ import annotations
import os
import sys
import time
import threading

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACK = os.path.join(PROJECT_ROOT, "assets", "audio", "match.ogg")


def _burn_cpu(stop: threading.Event) -> None:
    x = 0.0
    while not stop.is_set():
        for i in range(200000):
            x += i * 0.5
        x = 0.0


def Main() -> None:
    import pygame

    # Same mixer setup the game uses.
    pygame.mixer.pre_init(frequency=48000, size=-16, channels=2, buffer=16384)
    pygame.init()
    print("mixer:", pygame.mixer.get_init())

    sound = pygame.mixer.Sound(TRACK)
    channel = pygame.mixer.Channel(0)
    channel.play(sound, loops=-1)
    channel.set_volume(0.5)

    stop = threading.Event()
    if "load" in sys.argv:
        print("CPU load: ON (simulating a busy game)")
        threading.Thread(target=_burn_cpu, args=(stop,), daemon=True).start()
    else:
        print("CPU load: off (pure playback)")

    print("Playing for 3 minutes. Listen for when it starts bugging, and note the time.\n")
    start = time.time()
    while time.time() - start < 180:
        elapsed = int(time.time() - start)
        print(f"  t = {elapsed:3d}s   channel playing: {channel.get_busy()}")
        time.sleep(5)

    stop.set()
    print("\nDone.")


if __name__ == "__main__":
    Main()
