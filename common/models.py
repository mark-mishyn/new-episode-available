from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import JSONField
from django.db import models
from model_utils.models import TimeStampedModel


class TVSeries(TimeStampedModel):
    themoviedb_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255)
    first_air_date = models.DateField(blank=True, null=True)
    last_air_date = models.DateField(blank=True, null=True)
    number_of_seasons = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        res = self.name
        if self.first_air_date:
            res += ', {}'.format(self.first_air_date.year)
        if self.original_name != self.name:
            res += ' ({})'.format(self.original_name)
        if self.last_air_date or self.number_of_seasons:
            res += '\n'
            if self.number_of_seasons:
                res += ' seasons: {};'.format(self.number_of_seasons)
            if self.last_air_date:
                res += ' last episode date: {};'.format(self.last_air_date)
        return res


class VkUser(TimeStampedModel):
    vk_id = models.PositiveIntegerField(unique=True)
    tv_series = models.ManyToManyField(TVSeries, related_name='vk_users', blank=True)

    def __str__(self):
        return str(self.vk_id)


class TVSeriesVariants(TimeStampedModel):
    variants = JSONField()
    vk_user = models.ForeignKey(VkUser, related_name='variants')

