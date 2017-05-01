from django.conf.urls import url
from django.contrib import admin

from common.views import HandleVkRequestView

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^bot/$', HandleVkRequestView.as_view()),
]
