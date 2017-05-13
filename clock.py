from datetime import timedelta

import django
from apscheduler.schedulers.blocking import BlockingScheduler
from django.utils.timezone import now

from common.vk_client import VkMessenger

django.setup()

from django.conf import settings
from common.models import VkUser, TVSeries, TVSeriesVariants


print('RUN CLOCK FILE')
scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)


@scheduler.scheduled_job('cron', day_of_week='mon', hour=12)
def update_tv_shows_info_job():
    print('RUN UPDATE_TV_SHOWS_INFO_JOB')
    for tv in TVSeries.objects.all():
        tv.update_last_available_episode_date()


@scheduler.scheduled_job('cron', day_of_week='mon', hour=12, minute=10)
def remove_old_series_variants():
    TVSeriesVariants.objects.filter(created__lt=now() - timedelta(1)).delete()


@scheduler.scheduled_job('cron', hour=19, minute=30)
def notify_users_if_new_episode_available():
    print('RUN NOTIFY USERS')
    vk_client = VkMessenger()
    yesterday_date = now().date() - timedelta(days=1)
    for user in VkUser.objects.all():
        print('USER', user)
        new_tv_seres_names = user.tv_series.filter(
                last_available_episode_date=yesterday_date).values_list('name', flat=True)
        if new_tv_seres_names:
            print('SEND_MESSAGE', vk_client.send_message(
                    user_id=user.vk_id,
                    message='Released a new episode of "{}"'.format('\n'.join(new_tv_seres_names))))


scheduler.start()
