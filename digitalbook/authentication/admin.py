from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser, UserSession


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'id', 'email', 'username', 'first_name', 'last_name',
        'role_name', 'is_active', 'is_staff', 'is_superuser'
    )
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'role_name')
    ordering = ('-id',)

    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Roles'), {'fields': ('role_name',)}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'role_name', 'password1', 'password2', 'is_staff', 'is_superuser', 'is_active')
        }),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_token', 'is_active', 'ip_address', 'created_at', 'last_activity')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user__email', 'user__username', 'session_token', 'ip_address')
    ordering = ('-created_at',)
