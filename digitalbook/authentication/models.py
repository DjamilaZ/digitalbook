from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    """Modèle utilisateur personnalisé pour stocker les données de l'API externe"""
    
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=255, unique=True, blank=True, null=True)
    
    # Profile de l'API externe
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Rôle (pas de table séparée, seulement un champ avec choices)
    ROLE_CHOICES = [
        ('employe', 'Employé'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
    ]
    role_name = models.CharField(max_length=255, choices=ROLE_CHOICES, default='employe', blank=True, null=True)
    
    # Timestamps
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
    
    def get_role_display(self):
        """Retourne le label lisible du rôle"""
        try:
            return dict(self.ROLE_CHOICES).get(self.role_name, 'User')
        except Exception:
            return self.role_name or 'User'


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
