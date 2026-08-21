from django.urls import path

from .views import (
    ChangePasswordView,
    CurrentOwnerView,
    LogoutView,
    OwnerLoginView,
    OwnerTokenRefreshView,
)


app_name = "accounts"


urlpatterns = [
    path(
        "login/",
        OwnerLoginView.as_view(),
        name="login",
    ),
    path(
        "refresh/",
        OwnerTokenRefreshView.as_view(),
        name="refresh",
    ),
    path(
        "logout/",
        LogoutView.as_view(),
        name="logout",
    ),
    path(
        "me/",
        CurrentOwnerView.as_view(),
        name="me",
    ),
    path(
        "change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),
]