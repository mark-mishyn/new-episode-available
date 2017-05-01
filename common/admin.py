from django.contrib import admin

from common.models import TVSeries, VkUser, TVSeriesVariants


@admin.register(TVSeries)
class TVSeriesAdmin(admin.ModelAdmin):
    list_display = ('themoviedb_id', 'name', 'original_name', 'first_air_date', 'created')


@admin.register(VkUser)
class VkUserAdmin(admin.ModelAdmin):
    list_display = ('vk_id', 'created')


@admin.register(TVSeriesVariants)
class TVSeriesVariantsAdmin(admin.ModelAdmin):
    list_display = ('vk_user', 'variants', 'created')
