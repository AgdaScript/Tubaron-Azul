from __future__ import annotations
import math
import random
from dataclasses import dataclass
from engine.mathx.vec2 import Vec2
from game.data.teams import TeamDef, FORMATION
from game.match import pitch
from game.match.entities import Player, Ball, PLAYER_RADIUS, BALL_RADIUS
from game.match import ai

"""The live football simulation.

Pure game logic — it never draws. Each frame it takes the human player's input
for the team's active man, runs the AI for everyone else, advances ball physics,
resolves collisions, and detects goals. The scene layer reads the resulting
state to render the pitch.
"""

BASE_SPEED = 244.0
SPRINT_SPEED = 322.0
KEEPER_SPEED = 250.0
STEER_ACCEL = 2100.0

CAPTURE_RADIUS = 27.0
KEEPER_REACH = 34.0
SUPER_KEEPER_REACH = 70.0
DRIBBLE_OFFSET = 23.0
OWNER_STICKINESS = 0.52
LUNGE_SPEED = 430.0

SHOOT_SPEED = 720.0
PASS_SPEED = 560.0
CLEAR_SPEED = 780.0
BALL_DRAG = 430.0
WALL_BOUNCE = 0.62
GRAVITY = 900.0

KICKOFF_DELAY = 1.1
GOAL_CELEBRATION = 3.0
KEEPER_DIVE_DURATION = 0.45
DEFAULT_DURATION = 150.0

STATE_KICKOFF = "kickoff"
STATE_PLAYING = "playing"
STATE_GOAL = "goal"
STATE_FULLTIME = "fulltime"


@dataclass
class MatchInput:
    move: Vec2
    sprint: bool
    shoot: bool
    pass_: bool
    switch: bool

    @staticmethod
    def Idle() -> "MatchInput":
        return MatchInput(Vec2(0.0, 0.0), False, False, False, False)


class Match:
    def __init__(self, home: TeamDef, away: TeamDef, duration: float = DEFAULT_DURATION) -> None:
        self.home = home
        self.away = away
        self.duration = duration
        self.score = [0, 0]
        self.elapsed = 0.0
        self.state = STATE_KICKOFF
        self.state_timer = KICKOFF_DELAY
        self.kickoff_team = 0
        self.players: list[Player] = []
        self.ball = Ball(pitch.CENTER)
        self.controlled: Player | None = None
        self.last_scorer = -1
        self.events: list[str] = []
        self._rng = random.Random(1234)
        self._BuildSquads()
        self._ResetPositions(0)

    # -- setup -----------------------------------------------------------

    def _BuildSquads(self) -> None:
        number = 1
        for slot_index, (role, nx, ny) in enumerate(FORMATION):
            home_pos = pitch.PlaceFromFormation(nx, ny, 0)
            keeper = Player(0, role, self.home.short, number, home_pos, role == "GK")
            if keeper.is_keeper:
                # Vozinha, o muro: the over-tuned keeper who teleports to every save.
                keeper.is_super = True
                keeper.name = "Vozinha"
            self.players.append(keeper)
            number += 1

        number = 1
        for slot_index, (role, nx, ny) in enumerate(FORMATION):
            away_pos = pitch.PlaceFromFormation(nx, ny, 1)
            self.players.append(Player(1, role, self.away.short, number, away_pos, role == "GK"))
            number += 1

    def _ResetPositions(self, kickoff_team: int) -> None:
        self.kickoff_team = kickoff_team

        for player in self.players:
            player.pos = player.home
            player.vel = Vec2(0.0, 0.0)
            player.ball_cooldown = 0.0
            player.kick_timer = 0.0
            player.lunge_timer = 0.0
            player.keeper_beaten_timer = 0.0
            if player.is_keeper:
                player.facing = self._KeeperFieldFacing(player.team_index)

        self.ball.pos = pitch.CENTER
        self.ball.vel = Vec2(0.0, 0.0)
        self.ball.owner = None
        self.ball.height = 0.0
        self.ball.height_vel = 0.0
        self.ball.shot_immunity = 0.0
        self.ball.pending_shot = False

    # -- queries used by the AI -----------------------------------------

    def TeamSkill(self, team_index: int) -> float:
        if team_index == 0:
            return self.home.ai_skill

        return self.away.ai_skill

    def Teammates(self, team_index: int) -> list[Player]:
        return [p for p in self.players if p.team_index == team_index]

    def Opponents(self, team_index: int) -> list[Player]:
        return [p for p in self.players if p.team_index != team_index]

    def PossessionTeam(self) -> int:
        if self.ball.owner is None:
            return -1

        return self.ball.owner.team_index

    def CanShootAtGoal(self, player: Player) -> bool:
        return pitch.CanShootAtGoal(player.team_index, player.pos)

    def ClosestTeammateToBall(self, team_index: int) -> Player | None:
        best = None
        best_dist = 1e9

        for player in self.players:
            if player.team_index != team_index or player.is_keeper:
                continue

            dist = player.DistanceToBall(self.ball)
            if dist < best_dist:
                best_dist = dist
                best = player

        return best

    def NearestOpponent(self, player: Player) -> Player | None:
        best = None
        best_dist = 1e9

        for other in self.players:
            if other.team_index == player.team_index:
                continue

            dist = player.pos.GetDistanceTo(other.pos)
            if dist < best_dist:
                best_dist = dist
                best = other

        return best

    # -- main update -----------------------------------------------------

    def Update(self, dt: float, human: MatchInput) -> None:
        if self.state == STATE_FULLTIME:
            return

        self._UpdateClock(dt)
        self._UpdateStateTimer(dt)

        if self.state == STATE_GOAL:
            return

        self._SelectControlled()
        self._DecideAndSteer(dt, human)
        self._IntegratePlayers(dt)
        self._ResolvePlayerCollisions()
        self._TeleportSuperKeeper()
        self.ball.shot_immunity = max(0.0, self.ball.shot_immunity - dt)
        self._ResolveKicks(human)
        self._UpdateBall(dt)
        self._UpdateOwnership()
        self._CheckGoal()

    def _UpdateClock(self, dt: float) -> None:
        if self.state != STATE_PLAYING:
            return

        self.elapsed += dt

        if self.elapsed >= self.duration:
            self.elapsed = self.duration
            self.state = STATE_FULLTIME

    def _UpdateStateTimer(self, dt: float) -> None:
        if self.state in (STATE_KICKOFF, STATE_GOAL):
            self.state_timer -= dt

            if self.state_timer <= 0.0:
                if self.state == STATE_GOAL:
                    self._ResetPositions(self.kickoff_team)

                self.state = STATE_PLAYING

    def DisplayMinute(self) -> int:
        return min(90, int(self.elapsed / self.duration * 90.0))

    def _SelectControlled(self) -> None:
        if self.ball.owner is not None and self.ball.owner.team_index == 0 and not self.ball.owner.is_keeper:
            chosen = self.ball.owner
        else:
            chosen = self.ClosestTeammateToBall(0)

        for player in self.players:
            player.controlled = False

        if chosen is not None:
            chosen.controlled = True
            self.controlled = chosen

    def _DecideAndSteer(self, dt: float, human: MatchInput) -> None:
        for player in self.players:
            player.kick_timer = max(0.0, player.kick_timer - dt)
            player.keeper_beaten_timer = max(0.0, player.keeper_beaten_timer - dt)
            player.ball_cooldown = max(0.0, player.ball_cooldown - dt)
            player.lunge_timer = max(0.0, player.lunge_timer - dt)
            player.teleport_flash = max(0.0, player.teleport_flash - dt)

            if player is self.controlled:
                desired = self._HumanDesired(player, human)
            else:
                desired = ai.DecideMovement(self, player)

            self._Steer(player, desired, dt)
            self._UpdateFacing(player)

    def _HumanDesired(self, player: Player, human: MatchInput) -> Vec2:
        if player.lunge_timer > 0.0:
            return self._LungeVelocity(player)

        if human.switch and self.ball.owner is not player:
            player.lunge_timer = 0.22
            player.ball_cooldown = 0.0
            return self._LungeVelocity(player)

        if human.move.GetLength() < 0.2:
            # No steering input: let the player's own AI keep him useful rather
            # than freezing the team's best-placed man at the ball.
            return ai.DecideMovement(self, player)

        speed = BASE_SPEED
        if human.sprint:
            speed = SPRINT_SPEED

        return human.move.GetNormalized() * speed

    def _LungeVelocity(self, player: Player) -> Vec2:
        toward = (self.ball.pos - player.pos).GetNormalized()
        return toward * LUNGE_SPEED

    def _Steer(self, player: Player, desired: Vec2, dt: float) -> None:
        diff = desired - player.vel
        max_dv = STEER_ACCEL * dt

        if diff.GetLength() > max_dv:
            diff = diff.GetNormalized() * max_dv

        player.vel = player.vel + diff

    def _KeeperFieldFacing(self, team_index: int) -> float:
        return 1.0 if team_index == 0 else -1.0

    def _UpdateKeeperFacing(self, player: Player) -> None:
        if not pitch.BallInKeeperHalf(player.team_index, self.ball.pos.x):
            return

        dx = self.ball.pos.x - player.pos.x
        if dx > 10.0:
            player.facing = 1.0
        elif dx < -10.0:
            player.facing = -1.0
        else:
            player.facing = self._KeeperFieldFacing(player.team_index)

    def _UpdateFacing(self, player: Player) -> None:
        if player.is_keeper:
            self._UpdateKeeperFacing(player)
        elif player.vel.x > 18.0:
            player.facing = 1.0
        elif player.vel.x < -18.0:
            player.facing = -1.0

        if player.IsMoving():
            player.run_phase += 0.18
        elif player.is_keeper and pitch.BallInKeeperHalf(player.team_index, self.ball.pos.x):
            player.run_phase += 0.14

    def _IntegratePlayers(self, dt: float) -> None:
        for player in self.players:
            player.pos = player.pos + player.vel * dt
            self._ClampToField(player)
            self._ClampAttackDepth(player)

    def _ClampAttackDepth(self, player: Player) -> None:
        if self.ball.owner is not player or player.is_keeper:
            return

        small_left, _, small_right, _ = pitch.AttackingSmallBox(player.team_index)
        margin = PLAYER_RADIUS + 6.0

        if player.team_index == 0:
            max_x = small_left - margin
            if player.pos.x > max_x:
                player.pos = Vec2(max_x, player.pos.y)
                if player.vel.x > 0.0:
                    player.vel = Vec2(0.0, player.vel.y)
        else:
            min_x = small_right + margin
            if player.pos.x < min_x:
                player.pos = Vec2(min_x, player.pos.y)
                if player.vel.x < 0.0:
                    player.vel = Vec2(0.0, player.vel.y)

    def _ClampToField(self, player: Player) -> None:
        x = min(max(player.pos.x, PLAYER_RADIUS), pitch.WIDTH - PLAYER_RADIUS)
        y = min(max(player.pos.y, PLAYER_RADIUS), pitch.HEIGHT - PLAYER_RADIUS)
        player.pos = Vec2(x, y)

    def _ResolvePlayerCollisions(self) -> None:
        count = len(self.players)
        min_dist = PLAYER_RADIUS * 2.0

        for i in range(count):
            for j in range(i + 1, count):
                a = self.players[i]
                b = self.players[j]
                delta = b.pos - a.pos
                dist = delta.GetLength()

                if dist <= 0.0 or dist >= min_dist:
                    continue

                push = (min_dist - dist) / 2.0
                direction = delta.GetNormalized()
                a.pos = a.pos - direction * push
                b.pos = b.pos + direction * push

    def _TeleportSuperKeeper(self) -> None:
        """Vozinha is unbeatable: he blinks straight to wherever the save is.

        Any ball that threatens Cape Verde's goal — a shot on its way in, or the
        ball loose / dribbled inside his box — pulls him instantly onto it, so the
        islands simply do not concede from open play.
        """
        for keeper in self.players:
            if not keeper.is_super:
                continue

            own_goal = pitch.OwnGoalCenter(keeper.team_index)
            line_x = own_goal.x + 46.0
            box = pitch.PenaltyBox(keeper.team_index)
            ball = self.ball
            in_box = box[0] <= ball.pos.x <= box[2] and box[1] <= ball.pos.y <= box[3]
            incoming = ball.owner is None and ball.vel.x < -40.0 and ball.pos.x < 760.0

            # He sweeps up anything in his box — even a team-mate's loose dribble,
            # which is what stops own goals — and reads any incoming shot.
            target = None
            if in_box and ball.owner is not keeper:
                target = ball.pos
            elif incoming and abs(ball.vel.x) > 1.0:
                travel = (line_x - ball.pos.x) / ball.vel.x
                if travel > 0.0:
                    cross_y = ball.pos.y + ball.vel.y * travel
                    cross_y = min(max(cross_y, pitch.GoalMouthTop() - 30), pitch.GoalMouthBottom() + 30)
                    target = Vec2(line_x, cross_y)

            if target is None:
                continue

            keeper.pos = target
            keeper.vel = Vec2(0.0, 0.0)
            keeper.kick_timer = max(keeper.kick_timer, 0.25)
            keeper.teleport_flash = 0.3
            keeper.facing = self._KeeperFieldFacing(keeper.team_index)

    def _UpdateOwnership(self) -> None:
        if self.ball.shot_immunity > 0.0:
            return

        if self.ball.height > 48.0:
            return

        best = None
        best_eff = 1e9

        for player in self.players:
            if player.ball_cooldown > 0.0:
                continue

            dist = player.DistanceToBall(self.ball)
            reach = CAPTURE_RADIUS
            if player.is_super:
                reach = SUPER_KEEPER_REACH
            elif player.is_keeper:
                reach = KEEPER_REACH

            if dist > reach:
                continue

            eff = dist

            if player is self.ball.owner:
                eff = dist * OWNER_STICKINESS

            if eff < best_eff:
                best_eff = eff
                best = player

        if best is not None:
            if best is not self.ball.owner and self.ball.owner is not None:
                self.ball.owner.ball_cooldown = 0.18

            self.ball.owner = best
            self.ball.last_touch_team = best.team_index
            self.ball.pending_shot = False

    def _ResolveKicks(self, human: MatchInput) -> None:
        owner = self.ball.owner

        if owner is None:
            return

        if owner is self.controlled:
            if human.shoot:
                self._Shoot(owner, human)
                return
            if human.pass_:
                self._Pass(owner)
                return

        if owner is not self.controlled:
            action = ai.DecideBallAction(self, owner)

            if action == "shoot":
                self._Shoot(owner, None)
            elif action == "pass":
                self._Pass(owner)
            elif action == "clear":
                self._Clear(owner)

    def _Shoot(self, player: Player, human: MatchInput | None) -> None:
        goal_line_x = pitch.AttackingGoalLineX(player.team_index)
        aim_y = self._rng.uniform(pitch.GoalMouthTop() + 24, pitch.GoalMouthBottom() - 24)
        target = Vec2(goal_line_x, aim_y)
        direction = (target - self.ball.pos).GetNormalized()

        if human is not None and human.move.GetLength() > 0.3:
            direction = (direction * 0.45 + human.move.GetNormalized() * 0.55).GetNormalized()

        spread = (1.0 - self.TeamSkill(player.team_index)) * 0.34
        if human is not None:
            spread = 0.05

        direction = self._ApplySpread(direction, spread)
        self._ReleaseBall(player, direction, SHOOT_SPEED, loft=150.0, shot=True)

    def _Pass(self, player: Player) -> None:
        mate = self._BestPassTarget(player)

        if mate is None:
            self._Clear(player)
            return

        lead = mate.pos + mate.vel * 0.25
        direction = (lead - player.pos).GetNormalized()
        distance = player.pos.GetDistanceTo(mate.pos)
        speed = min(PASS_SPEED, 260.0 + distance * 1.3)
        self._ReleaseBall(player, direction, speed, loft=0.0)

    def _Clear(self, player: Player) -> None:
        goal = pitch.AttackingGoalCenter(player.team_index)
        direction = (Vec2(goal.x, pitch.HEIGHT / 2.0) - player.pos).GetNormalized()
        direction = self._ApplySpread(direction, 0.25)
        self._ReleaseBall(player, direction, CLEAR_SPEED, loft=220.0)

    def _BestPassTarget(self, player: Player) -> Player | None:
        goal = pitch.AttackingGoalCenter(player.team_index)
        best = None
        best_score = -1e9

        for mate in self.players:
            if mate is player or mate.team_index != player.team_index or mate.is_keeper:
                continue

            to_goal = goal.x - mate.pos.x
            progress = -abs(to_goal)
            if player.team_index == 0:
                progress = mate.pos.x
            else:
                progress = pitch.WIDTH - mate.pos.x

            distance = player.pos.GetDistanceTo(mate.pos)
            if distance < 70.0 or distance > 620.0:
                continue

            score = progress - distance * 0.5
            if score > best_score:
                best_score = score
                best = mate

        return best

    def _ApplySpread(self, direction: Vec2, spread: float) -> Vec2:
        if spread <= 0.0:
            return direction

        angle = self._rng.uniform(-spread, spread)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        x = direction.x * cos_a - direction.y * sin_a
        y = direction.x * sin_a + direction.y * cos_a
        return Vec2(x, y)

    def _ReleaseBall(self, player: Player, direction: Vec2, speed: float, loft: float = 0.0, shot: bool = False) -> None:
        self.ball.owner = None
        if shot:
            self.ball.pos = self.ball.pos + direction * 48.0
            self.ball.shot_immunity = 0.32
            self.ball.pending_shot = True
            for keeper in self.players:
                if keeper.is_keeper and keeper.team_index != player.team_index:
                    keeper.kick_timer = KEEPER_DIVE_DURATION
                    if player.pos.x > keeper.pos.x + 8.0:
                        keeper.facing = 1.0
                    elif player.pos.x < keeper.pos.x - 8.0:
                        keeper.facing = -1.0
        else:
            self.ball.pending_shot = False
        self.ball.vel = direction * speed
        self.ball.last_touch_team = player.team_index
        self.ball.height_vel = loft
        player.ball_cooldown = 0.4
        player.kick_timer = 0.32

    def _UpdateBall(self, dt: float) -> None:
        if self.ball.owner is not None:
            self._DribbleBall(dt)
            return

        self._IntegrateBall(dt)

    def _DribbleBall(self, dt: float) -> None:
        owner = self.ball.owner
        direction = owner.vel.GetNormalized()

        if direction.GetLength() < 0.1:
            direction = Vec2(owner.facing, 0.0)

        target = owner.pos + direction * DRIBBLE_OFFSET
        self.ball.pos = self.ball.pos + (target - self.ball.pos) * min(1.0, 18.0 * dt)
        self.ball.vel = owner.vel
        self.ball.height = 0.0
        self.ball.height_vel = 0.0

    def _IntegrateBall(self, dt: float) -> None:
        self.ball.pos = self.ball.pos + self.ball.vel * dt
        speed = self.ball.vel.GetLength()
        drag = BALL_DRAG * dt

        if speed <= drag:
            self.ball.vel = Vec2(0.0, 0.0)
        else:
            self.ball.vel = self.ball.vel.GetNormalized() * (speed - drag)

        self.ball.height_vel -= GRAVITY * dt
        self.ball.height += self.ball.height_vel * dt

        if self.ball.height <= 0.0:
            self.ball.height = 0.0
            if self.ball.height_vel < -40.0:
                self.ball.height_vel = -self.ball.height_vel * 0.45
            else:
                self.ball.height_vel = 0.0

        self._BounceWalls()

    def _BounceWalls(self) -> None:
        pos = self.ball.pos
        vel = self.ball.vel
        x, y = pos.x, pos.y
        vx, vy = vel.x, vel.y

        if y < BALL_RADIUS:
            y = BALL_RADIUS
            vy = -vy * WALL_BOUNCE
        elif y > pitch.HEIGHT - BALL_RADIUS:
            y = pitch.HEIGHT - BALL_RADIUS
            vy = -vy * WALL_BOUNCE

        if x < BALL_RADIUS and not pitch.IsWithinMouth(y):
            x = BALL_RADIUS
            vx = -vx * WALL_BOUNCE
        elif x > pitch.WIDTH - BALL_RADIUS and not pitch.IsWithinMouth(y):
            x = pitch.WIDTH - BALL_RADIUS
            vx = -vx * WALL_BOUNCE

        self.ball.pos = Vec2(x, y)
        self.ball.vel = Vec2(vx, vy)

    def _CheckGoal(self) -> None:
        if self.state != STATE_PLAYING:
            return

        x = self.ball.pos.x

        if x <= 2.0 and pitch.IsWithinMouth(self.ball.pos.y):
            self._RegisterGoal(1)
        elif x >= pitch.WIDTH - 2.0 and pitch.IsWithinMouth(self.ball.pos.y):
            self._RegisterGoal(0)

    def _RegisterGoal(self, team_index: int) -> None:
        conceding = 1 - team_index

        if self.ball.pending_shot:
            for player in self.players:
                if player.is_keeper and player.team_index == conceding:
                    player.keeper_beaten_timer = GOAL_CELEBRATION
                    player.kick_timer = 0.0

        self.ball.pending_shot = False
        self.score[team_index] += 1
        self.last_scorer = team_index
        self.state = STATE_GOAL
        self.state_timer = GOAL_CELEBRATION
        self.kickoff_team = conceding

        if team_index == 0:
            self.events.append(f"GOLO! {self.home.name} {self.score[0]}-{self.score[1]}")
        else:
            self.events.append(f"Golo de {self.away.name} ({self.score[0]}-{self.score[1]})")

    def IsOver(self) -> bool:
        return self.state == STATE_FULLTIME

    def HomeWon(self) -> bool:
        return self.score[0] > self.score[1]

    def IsDraw(self) -> bool:
        return self.score[0] == self.score[1]
