from django.urls import path
from .views import RequestPasswordResetView, ResetPasswordView, ChangePasswordView

app_name = 'users'

urlpatterns = [
    path('request-password-reset/', RequestPasswordResetView.as_view(), name='request_password_reset'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
]
