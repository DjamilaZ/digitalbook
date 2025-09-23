from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import json


class CustomUser(AbstractUser):
    """Modèle utilisateur personnalisé pour stocker les données de l'API externe"""
    
    # Champs de l'API externe
    external_user_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=255, unique=True, blank=True, null=True)
    
    # Profile de l'API externe
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Rôle de l'API externe
    role_id = models.IntegerField(blank=True, null=True)
    role_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Tokens d'authentification de l'API externe
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    token_expires_at = models.DateTimeField(blank=True, null=True)
    
    # Métadonnées
    is_external_user = models.BooleanField(default=True)
    external_api_url = models.URLField(default='https://total-cms.worldws.pro//api')
    
    # Timestamps
    last_login_api = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'auth_custom_user'
        verbose_name = 'Custom User'
        verbose_name_plural = 'Custom Users'
    
    def __str__(self):
        return f"{self.email} ({self.username or 'No username'})"
    
    def get_full_name(self):
        """Retourne le nom complet de l'utilisateur"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username or self.email
    
    def is_token_valid(self):
        """Vérifie si le token d'accès est encore valide"""
        if not self.token_expires_at:
            return False
        return timezone.now() < self.token_expires_at
    
    def get_role_display(self):
        """Retourne le nom du rôle pour l'affichage"""
        return self.role_name or 'User'
    
    def update_from_external_data(self, user_data):
        """Met à jour les données utilisateur à partir de l'API externe"""
        self.external_user_id = user_data.get('id')
        self.username = user_data.get('username')
        self.email = user_data.get('email')
        self.role_id = user_data.get('roleId')
        
        # Mettre à jour le profil si disponible
        profile = user_data.get('profile', {})
        self.first_name = profile.get('firstName')
        self.last_name = profile.get('lastName')
        
        # Mettre à jour le rôle si disponible
        role = user_data.get('role', {})
        self.role_name = role.get('name')
        
        self.last_login_api = timezone.now()
        self.save()
    
    def update_tokens(self, access_token, refresh_token=None, expires_in=None):
        """Met à jour les tokens d'authentification"""
        self.access_token = access_token
        if refresh_token:
            self.refresh_token = refresh_token
        
        if expires_in:
            self.token_expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)
        
        self.save()


class UserSession(models.Model):
    """Modèle pour suivre les sessions utilisateur"""
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sessions')
    session_token = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'auth_user_session'
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
    
    def __str__(self):
        return f"{self.user.email} - {self.session_token[:10]}..."
