from __future__ import annotations
import os
import threading
from engine.app import Application, AppConfig
from game.scenes.services import GameContext
from game.scenes.cinematic_scene import CinematicScene
from game.persistence.save_manager import SaveManager
from game.persistence.records import RecordBook
from game.data import theme

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ASSET_ROOT = os.path.join(PROJECT_ROOT, "assets")
SAVE_PATH = os.path.join(PROJECT_ROOT, "saves", "save.json")
RECORDS_PATH = os.path.join(PROJECT_ROOT, "saves", "records.json")


def _EnsureAssets() -> None:
    pitch_sentinel = os.path.join(ASSET_ROOT, "pitch", "floor.png")
    if not os.path.exists(pitch_sentinel):
        from tools.generate_assets import GenerateAll
        GenerateAll()

    player_sentinel = os.path.join(ASSET_ROOT, "players", "outfield_idle.png")
    if not os.path.exists(player_sentinel):
        from tools.process_players import ProcessAll
        ProcessAll()


def _WarmMusic(app: Application) -> None:
    if not app.GetAudio().IsEnabled():
        return

    for track in (theme.MUSIC_OPENING, theme.MUSIC_ANTHEM, theme.MUSIC_MATCH):
        app.GetAssets().LoadSound(track)


def Main() -> None:
    _EnsureAssets()
    config = AppConfig("Cabo Verde — Mundial 2026", theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT, ASSET_ROOT, 60)
    app = Application(config)
    threading.Thread(target=_WarmMusic, args=(app,), daemon=True).start()
    save_manager = SaveManager(SAVE_PATH)
    records = RecordBook(RECORDS_PATH)
    context = GameContext(app, save_manager, records)
    app.StartWith(CinematicScene(context))
    app.Run()


if __name__ == "__main__":
    Main()
