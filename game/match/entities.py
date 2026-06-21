from __future__ import annotations
from engine.mathx.vec2 import Vec2

"""Runtime objects on the pitch: the players and the ball.

These are deliberately plain mutable holders. All behaviour — movement, AI,
ball physics, scoring — lives in the Match simulation, so these classes only
carry state.
"""

PLAYER_RADIUS = 17.0
BALL_RADIUS = 9.0


class Player:
    def __init__(self, team_index: int, role: str, short: str, number: int,
                 home: Vec2, is_keeper: bool) -> None:
        self.team_index = team_index
        self.role = role
        self.short = short
        self.number = number
        self.home = home
        self.is_keeper = is_keeper
        self.is_super = False
        self.name = ""
        self.pos = home
        self.vel = Vec2(0.0, 0.0)
        self.facing = 1.0
        self.controlled = False
        self.kick_timer = 0.0
        self.ball_cooldown = 0.0
        self.lunge_timer = 0.0
        self.run_phase = 0.0
        self.teleport_flash = 0.0

    def IsMoving(self) -> bool:
        return self.vel.GetLength() > 16.0

    def DistanceToBall(self, ball: "Ball") -> float:
        return self.pos.GetDistanceTo(ball.pos)


class Ball:
    def __init__(self, pos: Vec2) -> None:
        self.pos = pos
        self.vel = Vec2(0.0, 0.0)
        self.owner: Player | None = None
        self.last_touch_team = -1
        self.height = 0.0
        self.height_vel = 0.0
        self.shot_immunity = 0.0

    def IsLoose(self) -> bool:
        return self.owner is None
