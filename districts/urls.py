from django.conf.urls import url, include

from . import views

urlpatterns = [
    url(r'^$', views.district, name='index'),
    url(r'^(?P<league_abbr>[^/]+)/', include('leagues.urls', namespace='league')),
]