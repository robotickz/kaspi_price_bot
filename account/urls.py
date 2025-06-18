from django.urls import path

from . import views


app_name = 'account'
urlpatterns = [
    path("register/", views.register_view, name="register-view"),
    path("login/", views.login_view, name="login-view"),
    path("logout/", views.logout_view, name="logout-view"),
    path("profile/", views.profile_view, name="profile-view"),
]
