from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import JSONField
from django.db import models
from model_utils.models import TimeStampedModel


class TVSeries(TimeStampedModel):
    themoviedb_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255)
    first_air_date = models.DateField()

    def __str__(self):
        return '{}, {} ({})'.format(self.name, self.first_air_date.year, self.original_name)


class VkUser(TimeStampedModel):
    vk_id = models.PositiveIntegerField(unique=True)
    tv_series = models.ManyToManyField(TVSeries, related_name='tv_series', blank=True)

    def __str__(self):
        return str(self.vk_id)


class TVSeriesVariants(TimeStampedModel):
    variants = JSONField()
    vk_user = models.ForeignKey(VkUser, related_name='variants')

    class Meta:
        unique_together = [('vk_user', 'variants'), ]

