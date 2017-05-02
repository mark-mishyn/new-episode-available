import django
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import timedelta

from django.utils.timezone import now

from common.themoviedb_client import MovieDbClient
from common.vk_client import VkMessenger

django.setup()

from django.conf import settings
from common.models import VkUser, TVSeries


# TODO add removing of old TVSeriesVariants


scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)


def update_tv_shows_info():
    movie_client = MovieDbClient()
    for tv in TVSeries.objects.all():
        if tv.vk_users.exists():
            tv_details = movie_client.get_details(tv.themoviedb_id)

            if tv_details.get('number_of_seasons'):
                tv.number_of_seasons = tv_details['number_of_seasons']

            last_air_date = tv_details.get('last_air_date')
            if last_air_date and tv.last_air_date != last_air_date:
                tv.last_air_date = last_air_date

            tv.save()


@scheduler.scheduled_job('cron', day_of_week='mon', hour=12)
def update_tv_shows_info_job():
    update_tv_shows_info()


@scheduler.scheduled_job('cron', hour=19)
def notify_users_if_new_episode_available():
    vk_client = VkMessenger()

    yesterday_date = now().date() - timedelta(days=1)
    for user in VkUser.objects.all():
        new_tv_seres_names = user.tv_series.filter(
                last_air_date=yesterday_date).values_list('name', flat=True)
        if new_tv_seres_names:
            vk_client.send_message(
                    user_id=user.vk_id,
                    message='New episodes available! \n{}'.format('\n'.join(new_tv_seres_names)))


if __name__ == '__main__':
    scheduler.start()
