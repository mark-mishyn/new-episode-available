from django.contrib.auth.models import AbstractUser
from django.db import models
from model_utils.models import TimeStampedModel


class TVSeries(TimeStampedModel):
    themoviedb_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255)
    first_air_date = models.DateField()

    def __str__(self):
        return '{}, {} ({})'.format(self.name, self.first_air_date.year, self.original_name)


class User(AbstractUser):
    tv_series = models.ManyToManyField(TVSeries, related_name='tv_series')

    class Meta(AbstractUser.Meta):
        swappable = 'AUTH_USER_MODEL'
