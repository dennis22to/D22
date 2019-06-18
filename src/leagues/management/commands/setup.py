import logging
from datetime import date, datetime, timedelta

from django.conf import settings
from django.core.management import BaseCommand
from django.db import transaction

from associations.models import Association
from base import logic, parsing
from base.middleware import env
from base.models import Value
from districts.models import District
from leagues.models import League, Season
from teams.models import Team

logger = logging.getLogger('hbscorez')


class Command(BaseCommand):
    options: dict = {}
    processed_districts: set = set()

    def add_arguments(self, parser):
        parser.add_argument('--youth', action='store_true', help="Include youth teams in setup.")
        parser.add_argument(
            '--associations', '-a', nargs='+', type=int, metavar='orgGrpID', help="IDs of Associations to be setup.")
        parser.add_argument(
            '--districts', '-d', nargs='+', type=int, metavar='orgID', help="IDs of Districts to be setup.")
        parser.add_argument(
            '--seasons', '-s', nargs='+', type=int, metavar='start_year', help="Start Years of Seasons to be setup.")
        parser.add_argument(
            '--leagues', '-l', nargs='+', type=int, metavar='score', help="IDs of Leagues to be setup.")

    def handle(self, *args, **options):
        self.options = options
        self.processed_districts = set()
        env.UPDATING.set_value(Value.TRUE)
        self.create_associations()
        env.UPDATING.set_value(Value.FALSE)

    def create_associations(self):
        url = settings.ROOT_SOURCE_URL
        dom = logic.get_html(url)
        links = dom.xpath('//div[@id="main-content"]/div/ul/li/a')
        for link in links:
            self.create_association(link)

    def create_association(self, association_link):
        name = association_link.text_content()
        try:
            abbreviation = Association.get_association_abbreviation(name)
        except KeyError:
            logger.warn("No abbreviation for association '{}'".format(name))
            return

        bhv_id = parsing.parse_association_bhv_id(association_link)

        if self.options['associations'] and bhv_id not in self.options['associations']:
            logger.debug('SKIPPING Association (options): {} {}'.format(bhv_id, name))
            return

        association, created = Association.objects.get_or_create(name=name, abbreviation=abbreviation, bhv_id=bhv_id)
        if created:
            logger.info('CREATED Association: {}'.format(association))
        else:
            logger.info('EXISTING Association: {}'.format(association))

        url = association.source_url()
        dom = logic.get_html(url)
        items = dom.xpath('//select[@name="orgID"]/option[position()>1]')
        for item in items:
            self.create_district(item, association)

    def create_district(self, district_item, association):
        name = district_item.text
        bhv_id = int(district_item.get('value'))

        if self.options['districts'] and bhv_id not in self.options['districts']:
            logger.debug('SKIPPING District (options): {} {}'.format(bhv_id, name))
            return

        district, created = District.objects.get_or_create(name=name, bhv_id=bhv_id)
        district.associations.add(association)
        if bhv_id in self.processed_districts:
            logger.debug('SKIPPING District: {} {} (already processed)'.format(bhv_id, name))
            return

        if created:
            logger.info('CREATED District: {}'.format(district))
        else:
            logger.info('EXISTING District: {}'.format(district))
        self.processed_districts.add(bhv_id)

        for start_year in range(2004, datetime.now().year + 1):
            self.create_season(district, start_year)

    def create_season(self, district, start_year):
        if self.options['seasons'] and start_year not in self.options['seasons']:
            logger.debug('SKIPPING District Season (options): {} {}'.format(district, start_year))
            return

        season, season_created = Season.objects.get_or_create(start_year=start_year)
        if season_created:
            logger.info('CREATED Season: {}'.format(season))
        else:
            logger.info('EXISTING Season: {}'.format(season))

        for start_date in [date(start_year, 10, 1) + timedelta(days=10*n) for n in range(4)]:
            logger.debug('trying District Season: {} {} {}'.format(district, season, start_date))
            url = District.build_source_url(district.bhv_id, start_date)
            dom = logic.get_html(url)
            league_links = dom.xpath('//div[@id="results"]/div/table[2]/tr/td[1]/a')
            if league_links:
                break
        else:
            logger.warn('District Season without Leagues: {} {}'.format(district, season))
            return

        for league_link in league_links:
            self.create_league(league_link, district, season)

    @transaction.atomic
    def create_league(self, league_link, district, season):
        abbreviation = league_link.text
        bhv_id = parsing.parse_league_bhv_id(league_link)

        if self.options['leagues'] and bhv_id not in self.options['leagues']:
            logger.debug('SKIPPING League (options): {} {}'.format(bhv_id, abbreviation))
            return

        if abbreviation[:1] in ['m', 'w', 'g', 'u'] and not self.options['youth']:
            logger.debug('SKIPPING League (youth league): {} {}'.format(bhv_id, abbreviation))
            return

        url = League.build_source_url(bhv_id)
        dom = logic.get_html(url)

        name = parsing.parse_league_name(dom)

        if League.is_youth_league(name) and not self.options['youth']:
            logger.debug('SKIPPING League (youth league): {} {}'.format(bhv_id, name))
            return

        team_links = dom.xpath('//table[@class="scoretable"]/tr[position() > 1]/td[3]/a') or \
            dom.xpath('//table[@class="scoretable"]/tr[position() > 1]/td[2]/a')
        if not team_links:
            logger.debug('SKIPPING League: {} {} (no team table)'.format(bhv_id, name))
            return

        game_rows = parsing.parse_game_rows(dom)
        if not game_rows:
            logger.debug('SKIPPING League (no games): {} {}'.format(bhv_id, name))
            return
        if len(game_rows) < len(team_links) * (len(team_links) - 1):
            logger.debug('SKIPPING League (few games): {} {}'.format(bhv_id, abbreviation))
            return

        if "Platzierungsrunde" in name:
            logger.debug('SKIPPING League (Platzierungsrunde): {} {}'.format(bhv_id, name))
            return

        if "Meister" in name:
            logger.debug('SKIPPING League (Meisterschaft): {} {}'.format(bhv_id, name))
            return

        if bhv_id == 7424:
            name = "Männer Kreisliga C Staffel 3"

        if bhv_id == 5380:
            name = "Männer Kreisliga 2-1"

        if bhv_id == 5381:
            name = "Männer Kreisliga 2-2"

        league, league_created = League.objects.get_or_create(
            name=name, abbreviation=abbreviation, district=district, season=season, bhv_id=bhv_id)
        if league_created:
            logger.info('CREATED League: {}'.format(league))
        else:
            logger.info('EXISTING League: {}'.format(league))

        for team_link in team_links:
            self.create_team(team_link, league)

    def create_team(self, link, league):
        bhv_id = parsing.parse_team_bhv_id(link)
        name = link.text

        url = Team.build_source_url(league.bhv_id, bhv_id)
        dom = logic.get_html(url)
        game_rows = parsing.parse_game_rows(dom)
        short_team_names = [c.text for game_row in game_rows for c in game_row.xpath('td')[4:7:2]]
        short_team_name = max(set(short_team_names), key=short_team_names.count)

        team, created = Team.objects.get_or_create(
            name=name, short_name=short_team_name, league=league, bhv_id=bhv_id)
        if created:
            logger.info('CREATED Team: {}'.format(team))
        else:
            logger.info('EXISTING Team: {}'.format(team))