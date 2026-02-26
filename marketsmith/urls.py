"""
URL configuration for marketsmith project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from core import views
from core.auth_views import register_view


urlpatterns = [
    path('admin/', admin.site.urls),
    path("cron/ping/", views.cron_ping),
    # Screen 1: Login
    path(
        'accounts/login/',
        auth_views.LoginView.as_view(template_name='accounts/login.html'),
        name='login'
    ),

    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Screen 2: Home / Main Lobby
    path('', views.home, name='home'),

    path('matchmaking/', views.matchmaking, name='matchmaking'),

    path('waiting/<int:game_id>/', views.waiting_room, name='waiting_room'),

    path('game/<int:game_id>/', views.game_interface, name='game_interface'),

    path('api/order/', views.api_place_order, name='api_order'),

    path('accounts/register/', register_view, name='register'),

    path('cleanup/<int:game_id>/', views.cleanup_game, name='cleanup_game'),

    path('view_players/', views.view_player_info, name='players')

]