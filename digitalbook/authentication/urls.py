from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'auth'

router = DefaultRouter()
router.register(r'users', views.AdminUserViewSet, basename='admin-user')

urlpatterns = [
    # CSRF
    path('csrf/', views.get_csrf_token, name='get_csrf_token'),
    # Inscription locale
    path('register/', views.RegisterView.as_view(), name='register'),
    # Endpoints d'authentification
    path('login/', views.LoginView.as_view(), name='login'),
    path('refresh/', views.RefreshTokenView.as_view(), name='refresh_token'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # Endpoints utilisateur
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('sessions/', views.UserSessionsView.as_view(), name='user_sessions'),
    path('validate-token/', views.validate_token, name='validate_token'),
    path('revoke-session/<str:session_token>/', views.revoke_session, name='revoke_session'),
    # Admin user management routes
    path('', include(router.urls)),
]
