from django.urls import path

from . import views

app_name = 'realtime_chat'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('groups/create/', views.create_group, name='create_group'),
    path('groups/<slug:slug>/join/', views.join_group, name='join_group'),
    path('groups/<slug:slug>/leave/', views.leave_group, name='leave_group'),
    path('history/private/<str:username>/', views.private_history, name='private_history'),
    path('history/group/<slug:slug>/', views.group_history, name='group_history'),
]
