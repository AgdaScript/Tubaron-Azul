from __future__ import annotations
import pygame
from engine.resources.asset_manager import AssetManager

MUSIC_CHANNEL = 0


class AudioManager:

    def __init__(self, assets: AssetManager) -> None:
        self._assets = assets
        self._enabled = pygame.mixer.get_init() is not None
        self._track: str | None = None
        self._volume = 0.5
        self._channel: pygame.mixer.Channel | None = None

        if self._enabled:
            pygame.mixer.set_reserved(MUSIC_CHANNEL + 1)
            self._channel = pygame.mixer.Channel(MUSIC_CHANNEL)

    def IsEnabled(self) -> bool:
        return self._enabled

    def PlaySound(self, relative: str, volume: float = 1.0) -> None:
        if not self._enabled:
            return

        sound = self._assets.LoadSound(relative)

        if sound is None:
            return

        sound.set_volume(volume)
        sound.play()

    def PlayMusic(self, relative: str, volume: float = 0.5, loop: bool = True) -> None:
        if not self._enabled or self._channel is None:
            return

        if relative == self._track and self._channel.get_busy():
            self._channel.set_volume(volume)
            self._volume = volume
            return

        sound = self._assets.LoadSound(relative)

        if sound is None:
            return

        self._track = relative
        self._volume = volume
        loops = -1 if loop else 0
        self._channel.play(sound, loops=loops)
        self._channel.set_volume(volume)

    def StopMusic(self) -> None:
        if not self._enabled or self._channel is None:
            return

        self._channel.stop()
        self._track = None
