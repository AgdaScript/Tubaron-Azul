from __future__ import annotations
from engine.mathx.vec2 import Vec2
from game.match import pitch

"""Decision logic for every player the human is not controlling.

Both the away nation and the player's own off-the-ball teammates run through
here. Each call returns a desired velocity; ball actions (shoot / pass / clear)
are decided separately for whoever owns the ball. A team's ai_skill scales speed
and shooting range, so the World Cup road gets genuinely harder.
"""

BASE = 244.0


def _Speed(match, player) -> float:
    skill = match.TeamSkill(player.team_index)
    return BASE * (0.82 + 0.20 * skill)


def DecideMovement(match, player) -> Vec2:
    if player.is_keeper:
        return _KeeperMovement(match, player)

    ball = match.ball
    possession = match.PossessionTeam()

    if ball.owner is player:
        return _CarrierMovement(match, player)

    if possession == player.team_index:
        return _SupportMovement(match, player)

    if possession == -1:
        return _LooseMovement(match, player)

    return _DefendMovement(match, player)


def _SteerTo(player, target: Vec2, speed: float) -> Vec2:
    direction = (target - player.pos).GetNormalized()
    return direction * speed


def _KeeperMovement(match, player) -> Vec2:
    box = pitch.PenaltyBox(player.team_index)
    goal = pitch.OwnGoalCenter(player.team_index)
    ball = match.ball

    if player.team_index == 0:
        line_x = goal.x + 46.0
        incoming = ball.vel.x < -60.0
    else:
        line_x = goal.x - 46.0
        incoming = ball.vel.x > 60.0

    target_y = _Clamp(ball.pos.y, pitch.GoalMouthTop() + 10, pitch.GoalMouthBottom() - 10)

    # Read an incoming loose shot and slide to where it will cross the line.
    # A keener (higher skill) keeper trusts the read; a weaker one lags toward
    # the ball's current line, so sharp shots beat him.
    if ball.owner is None and incoming and abs(ball.vel.x) > 1.0:
        travel = (line_x - ball.pos.x) / ball.vel.x
        if travel > 0.0:
            cross_y = ball.pos.y + ball.vel.y * travel
            read = 0.45 + 0.5 * match.TeamSkill(player.team_index)
            cross_y = cross_y * read + ball.pos.y * (1.0 - read)
            target_y = _Clamp(cross_y, pitch.GoalMouthTop() - 6, pitch.GoalMouthBottom() + 6)

    ball_in_box = box[0] <= ball.pos.x <= box[2] and box[1] <= ball.pos.y <= box[3]
    if ball_in_box and ball.owner is None and match.PossessionTeam() != player.team_index:
        return _SteerTo(player, ball.pos, _Speed(match, player) * 1.18)

    if ball_in_box and ball.owner is not None and ball.owner.team_index != player.team_index:
        shade_y = _Clamp(ball.pos.y, pitch.GoalMouthTop() + 10, pitch.GoalMouthBottom() - 10)
        return _SteerTo(player, Vec2(line_x, shade_y), _Speed(match, player) * 1.02)

    return _SteerTo(player, Vec2(line_x, target_y), _Speed(match, player) * 1.1)


def _CarrierMovement(match, player) -> Vec2:
    shoot_x = pitch.AttackingShootLineX(player.team_index)
    target = Vec2(shoot_x, _Clamp(player.pos.y, pitch.GoalMouthTop(), pitch.GoalMouthBottom()))
    direction = (target - player.pos).GetNormalized()

    opponent = match.NearestOpponent(player)
    if opponent is not None and player.pos.GetDistanceTo(opponent.pos) < 90.0:
        away = (player.pos - opponent.pos).GetNormalized()
        direction = (direction * 0.6 + away * 0.6).GetNormalized()

    return direction * (_Speed(match, player) * 1.06)


def _SupportMovement(match, player) -> Vec2:
    ball = match.ball
    goal = pitch.AttackingGoalCenter(player.team_index)
    push = 0.34

    target_x = player.home.x + (goal.x - player.home.x) * push
    target_x = target_x * 0.7 + ball.pos.x * 0.3
    target_y = player.home.y * 0.6 + ball.pos.y * 0.4
    return _SteerTo(player, Vec2(target_x, target_y), _Speed(match, player) * 0.9)


def _LooseMovement(match, player) -> Vec2:
    chaser = match.ClosestTeammateToBall(player.team_index)
    ball = match.ball

    if player is chaser:
        intercept = ball.pos + ball.vel * 0.18
        return _SteerTo(player, intercept, _Speed(match, player) * 1.05)

    target_y = player.home.y * 0.7 + ball.pos.y * 0.3
    return _SteerTo(player, Vec2(player.home.x, target_y), _Speed(match, player) * 0.8)


def _DefendMovement(match, player) -> Vec2:
    ball = match.ball
    chaser = match.ClosestTeammateToBall(player.team_index)
    own_goal = pitch.OwnGoalCenter(player.team_index)

    if player is chaser:
        intercept = ball.pos + ball.vel * 0.12
        return _SteerTo(player, intercept, _Speed(match, player) * 1.08)

    # Drop goal-side of the ball and shade toward it.
    target_x = player.home.x * 0.55 + ((ball.pos.x + own_goal.x) / 2.0) * 0.45
    target_y = player.home.y * 0.5 + ball.pos.y * 0.5
    return _SteerTo(player, Vec2(target_x, target_y), _Speed(match, player) * 0.92)


def DecideBallAction(match, player) -> str | None:
    if player.is_keeper:
        return "clear"

    if pitch.CanShootAtGoal(player.team_index, player.pos):
        return "shoot"

    opponent = match.NearestOpponent(player)
    pressured = opponent is not None and player.pos.GetDistanceTo(opponent.pos) < 64.0

    if pressured:
        return "pass"

    own_goal = pitch.OwnGoalCenter(player.team_index)
    if player.pos.GetDistanceTo(own_goal) < 320.0 and pressured:
        return "clear"

    return None


def _Clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)
