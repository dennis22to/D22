from django.contrib.staticfiles.templatetags.staticfiles import static

from games.models import TeamOutcome, GameOutcome
from teams.models import Team


def dec(value, arg):
    return value - arg


def team_logo_url(team: Team):
    if team.logo:
        return team.logo.url
    else:
        return static('base/images/favicons/favicon.png')


def team_outcome_badge(outcome: TeamOutcome):
    if outcome is None:
        return "-"

    mapping = {
        TeamOutcome.WIN: ('success', 'Sieg'),
        TeamOutcome.TIE: ('warning', 'Unentschieden'),
        TeamOutcome.LOSS: ('danger', 'Niederlage')
    }
    return '<span class="badge badge-{}">{}</span>'.format(*mapping[outcome])


def game_outcome_badge(outcome: GameOutcome):
    if outcome is None:
        return "-"

    mapping = {
        GameOutcome.HOME_WIN: 'Heimsieg',
        GameOutcome.AWAY_WIN: 'Auswärtssieg',
        GameOutcome.TIE: 'Unentschieden',
    }
    return '<span class="badge badge-light">{}</span>'.format(mapping[outcome])
