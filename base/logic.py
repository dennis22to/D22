import collections
from typing import Callable, Dict, List

import requests
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth
from lxml import html

from games.models import Game, TeamOutcome
from players.models import Player, Score
from teams.models import Team


def get_html(url):
    # time.sleep(1)
    response = requests.get(url)
    response.encoding = 'utf-8'
    return html.fromstring(response.text)


def add_ranking_place(items: list, field: str):
    """
    Adds 'place' to all items according to their order.
    If the value of the specified field on any given item matches the value on the field of the previous item,
    then the item gets the same place as its predecessor.

    :param items: an already sorted list of items, ordered by `field`
    :param field: the field of the items to compare
    """
    for index, item in enumerate(items):
        item.place = index + 1
        if index > 0:
            previous = items[index - 1]
            if getattr(previous, field) == getattr(item, field):
                item.place = previous.place


def add_score(score: Score, log_fun: Callable = print):
    log_fun('CREATING Score: {} {}'.format(score.game, score.player.name))

    if duplicate_player_scores_exist(score):
        split_by_number(score.player.name, score.player.team)
        score.player.name = '{} ({})'.format(score.player.name, score.player_number)

    player, created = Player.objects.get_or_create(name=score.player.name, team=score.player.team)
    if created:
        log_fun('CREATED Player: {}'.format(player))
    else:
        log_fun('EXISTING Player: {}'.format(player))

    score.player = player
    score.save()


def duplicate_player_scores_exist(score: Score):
    divided_players = score.player.team.player_set.filter(name__regex="^{} \(\d+\)$".format(score.player.name))
    duplicate_scores = Score.objects.filter(player__name=score.player.name, player__team=score.player.team,
                                            game=score.game)
    return divided_players.exists() or duplicate_scores.exists()


@transaction.atomic
def split_by_number(original_name: str, team: Team, log_fun: Callable = print):
    log_fun("DIVIDING Player: {} ({})".format(original_name, team))

    matches = Player.objects.filter(name=original_name, team=team)
    if not matches.exists():
        log_fun("SKIPPING Player (not found): {} ({})".format(original_name, team))
        return

    original_player = matches[0]
    for score in original_player.score_set.all():
        new_name = "{} ({})".format(original_player.name, score.player_number)
        new_player, created = Player.objects.get_or_create(name=new_name, team=original_player.team)
        if created:
            log_fun("CREATED Player: {}".format(new_player))
        score.player = new_player
        score.save()

    if not original_player.score_set.all().exists():
        log_fun("DELETING Player (no dangling scores): {}".format(original_player))
        original_player.delete()


def league_games(league):
    games = league.game_set \
        .annotate(month=TruncMonth('opening_whistle')) \
        .order_by('opening_whistle')
    games_by_month = collections.defaultdict(list)
    for game in games:
        games_by_month[game.month].append(game)
    return games_by_month


def team_points(team):
    points = 0
    for game in Game.objects.filter(Q(home_team=team) | Q(guest_team=team)):
        outcome = game.outcome_for(team)
        if outcome == TeamOutcome.WIN:
            points += 2
        elif outcome == TeamOutcome.TIE:
            points += 1
    return points


def top_league_teams(league):
    teams = league.team_set.all()
    for team in teams:
        team.points = team_points(team)
    add_ranking_place(teams, 'points')
    teams_by_rank = collections.defaultdict(list)
    for team in teams:
        if team.place <= 5:
            teams_by_rank[team.place].append(team)
    for team_group in teams_by_rank.values():
        team_group.sort(key=lambda p: p.name)
    return teams_by_rank


def league_teams_by_rank(league, top: int = 0) -> Dict[int, List[Team]]:
    teams = league.team_set.all()
    for team in teams:
        team.points = team_points(team)
    add_ranking_place(teams, 'points')
    teams_by_rank: Dict[int, List[Team]] = collections.defaultdict(list)
    for team in teams:
        if top == 0 or team.place <= top:
            teams_by_rank[team.place].append(team)
    for team_group in teams_by_rank.values():
        team_group.sort(key=lambda p: p.name)
    return teams_by_rank


def league_scorers(league):
    scorers = Player.objects \
        .filter(team__league=league) \
        .annotate(games=Count('score')) \
        .filter(games__gt=0) \
        .annotate(total_goals=Coalesce(Sum('score__goals'), 0)) \
        .filter(total_goals__gt=0) \
        .annotate(total_penalty_goals=Sum('score__penalty_goals')) \
        .annotate(total_field_goals=F('total_goals') - F('total_penalty_goals')) \
        .order_by('-total_goals')
    add_ranking_place(scorers, 'total_goals')
    return scorers


def top_league_scorers(league):
    players = Player.objects \
        .filter(team__league=league) \
        .annotate(games=Count('score')) \
        .filter(games__gt=0) \
        .annotate(total_goals=Coalesce(Sum('score__goals'), 0)) \
        .order_by('-total_goals')
    add_ranking_place(players, 'total_goals')
    scorers_by_rank = collections.defaultdict(list)
    for player in players:
        if player.place <= 5:
            scorers_by_rank[player.place].append(player)
    for scorers_group in scorers_by_rank.values():
        scorers_group.sort(key=lambda p: p.name)
    return scorers_by_rank


def league_offenders(league):
    offenders = Player.objects \
        .filter(team__league=league) \
        .annotate(games=Count('score')) \
        .annotate(warnings=Count('score__warning_time')) \
        .annotate(suspensions=Count('score__first_suspension_time') +
                  Count('score__second_suspension_time') +
                  Count('score__third_suspension_time')) \
        .annotate(disqualifications=Count('score__disqualification_time')) \
        .annotate(offender_points=F('warnings') + 2 * F('suspensions') + 3 * F('disqualifications')) \
        .filter(offender_points__gt=0) \
        .order_by('-offender_points')
    add_ranking_place(offenders, 'offender_points')
    offenders_by_rank = collections.defaultdict(list)
    for offender in offenders:
        if offender.place <= 5:
            offenders_by_rank[offender.place].append(offender)
    for scorers_group in offenders_by_rank.values():
        scorers_group.sort(key=lambda p: p.name)
    return offenders_by_rank


def top_league_offenders(league):
    offenders = Player.objects \
        .filter(team__league=league) \
        .annotate(games=Count('score')) \
        .annotate(warnings=Count('score__warning_time')) \
        .annotate(suspensions=Count('score__first_suspension_time') +
                  Count('score__second_suspension_time') +
                  Count('score__third_suspension_time')) \
        .annotate(disqualifications=Count('score__disqualification_time')) \
        .annotate(offender_points=F('warnings') + 2 * F('suspensions') + 3 * F('disqualifications')) \
        .filter(offender_points__gt=0) \
        .order_by('-offender_points')
    add_ranking_place(offenders, 'offender_points')
    offenders_by_place = collections.defaultdict(list)
    for offender in offenders:
        if offender.place <= 5:
            offenders_by_place[offender.place].append(offender)
    for scorers_group in offenders_by_place.values():
        scorers_group.sort(key=lambda p: p.name)
    return offenders_by_place
