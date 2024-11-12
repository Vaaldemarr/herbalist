"""
URL configuration for myproject project.

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
from django.urls import path, include
from herbalist import views
# from herbalist.views import SignUpView, UserUpdateView
# from django.contrib.auth.urls
from herbalist.users import SignUpView, UserUpdateView, CustomLogoutView, CustomLoginView, CustomPasswordChangeView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/profile/edit_profile/', UserUpdateView.as_view(), name='edit_profile'),
    path('signup/', SignUpView.as_view(), name='signup'),
    # path('accounts/logout/', auth_views.LogoutView.as_view(template_name='registration/logged_out1.html'), name='logout'),
    path('accounts/logout/', CustomLogoutView.as_view(), name='logout'),

    # path(
    #     "accounts/password_change/", auth_views.PasswordChangeView.as_view(template_name='registration/password_change_form1.html'), name="password_change"
    # ),
    path("accounts/password_change/", CustomPasswordChangeView.as_view(), name="password_change"),
    path(
        "accounts/password_change/done/",
        auth_views.PasswordChangeDoneView.as_view(template_name='registration/password_change_done1.html'),
        name="password_change_done",
    ),
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    # path('accounts/logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/profile/', views.profile_view, name='profile'),

    path('', views.start_page, name='home'),  # Переадресация с главной страницы

    path('plants/', views.plants, name='plants'),
    path('plants/<int:id>/', views.plant_detail, name='plant_detail'),
    path('compounds/', views.compounds, name='compounds'),
    path('compounds/<int:id>/', views.compounds_detail, name='compounds_detail'),
    path('compounds-groups/', views.compounds_groups, name='compounds-groups'),
    path('compounds-groups/<int:id>/', views.compounds_group_detail, name='compounds_group_detail'),
    path('activities/', views.activities, name='activities'),
    path('activities/<int:id>/', views.activity_detail, name='activity_detail'),
    path('families/', views.families, name='families'),
    path('families/<int:id>/', views.family_detail, name='family_detail'),

    path('mixtures/', views.mixtures_list, name='mixtures_list'),
    path('mixtures/<int:id>/', views.mixture_detail, name='mixture_detail'),

    # path('language_redirect/<str:url>/<str:params>', views.language_redirect, name='language_redirect'),
    path('language_redirect/<int:id>/<str:url>/<str:params>', views.language_redirect, name='language_redirect'),

]
