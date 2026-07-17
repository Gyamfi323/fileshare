"""
FileShare App Configuration
"""

from django.apps import AppConfig


class FileshareConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fileshare'
    verbose_name = 'FileShare - File Upload Manager'
