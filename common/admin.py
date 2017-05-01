from django.contrib import admin

from common.models import TVSeries


@admin.register(TVSeries)
class TVSeriesAdmin(admin.ModelAdmin):
    list_display = ('themoviedb_id', 'name', 'original_name', 'first_air_date')
