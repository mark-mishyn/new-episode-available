from datetime import timedelta
from django.contrib.auth.models import AbstractUser
from django.contrib.humanize.templatetags.humanize import naturalday
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.dateparse import parse_date
from django.utils.timezone import now
from model_utils.models import TimeStampedModel

from common.themoviedb_client import MovieDbClient


class TVSeries(TimeStampedModel):
    themoviedb_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255)
    first_air_date = models.DateField(blank=True, null=True)
    last_available_episode_date = models.DateField(blank=True, null=True)
    number_of_seasons = models.PositiveIntegerField(blank=True, null=True)
    seasons = JSONField(blank=True, null=True)

    def __str__(self):
        res = self.name
        if self.first_air_date:
            res += ', {}'.format(self.first_air_date.year)
        if self.original_name != self.name:
            res += ' ({})'.format(self.original_name)
        if self.last_available_episode_date or self.number_of_seasons:
            if self.last_available_episode_date:
                res += '\n last episode date: {}'.format(
                        naturalday(self.last_available_episode_date))

            if self.seasons:
                res += '\n seasons:'
                for s in self.seasons:
                    res += '\n - {}: {}'.format(
                            s['season_number'],
                            naturalday(parse_date(s['air_date'])) if s.get('air_date') else '?')

        return res

    def update_last_available_episode_date(self):
        movie_client = MovieDbClient()
        today_date = now().date()

        if self.vk_users.exists():
            tv_details = movie_client.get_details(self.themoviedb_id)

            if tv_details.get('number_of_seasons'):
                self.number_of_seasons = tv_details['number_of_seasons']

            if tv_details.get('seasons'):
                self.seasons = tv_details['seasons']

                for season in tv_details['seasons']:
                    if season.get('air_date'):
                        season_date = parse_date(season['air_date'])
                        if season_date < today_date:
                            for week_num in range(season['episode_count']):
                                episode_date = season_date + timedelta(weeks=week_num)
                                if episode_date <= today_date:
                                    self.last_available_episode_date = episode_date

            self.save()


class VkUser(TimeStampedModel):
    vk_id = models.PositiveIntegerField(unique=True)
    tv_series = models.ManyToManyField(TVSeries, related_name='vk_users', blank=True)

    def __str__(self):
        return str(self.vk_id)


class TVSeriesVariants(TimeStampedModel):
    variants = JSONField()
    vk_user = models.ForeignKey(VkUser, related_name='variants')

