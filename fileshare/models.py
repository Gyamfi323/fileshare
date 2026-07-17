"""
FileShare Django App - Models
Production-ready file upload/download system similar to GoFile
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.urls import reverse
import uuid
import os
from datetime import timedelta


class FileUpload(models.Model):
    """Core file upload model with metadata, ownership, and expiry"""
    
    STORAGE_CHOICES = [
        ('local', 'Local Storage'),
        ('s3', 'AWS S3'),
    ]
    
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
        ('password', 'Password Protected'),
    ]
    
    # Primary identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploads', null=True, blank=True)
    
    # File info
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    file_size = models.BigIntegerField()  # bytes
    file_hash = models.CharField(max_length=64, unique=True)  # SHA256 for dedup
    mime_type = models.CharField(max_length=100)
    
    # Access control
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='private')
    password_hash = models.CharField(max_length=255, blank=True, null=True)
    access_token = models.CharField(max_length=64, unique=True, db_index=True)  # shareable link token
    
    # Expiry & cleanup
    expires_at = models.DateTimeField(null=True, blank=True)  # NULL = never expires
    auto_delete = models.BooleanField(default=False)  # auto-delete after expiry
    
    # Storage
    storage_backend = models.CharField(max_length=20, choices=STORAGE_CHOICES, default='local')
    s3_key = models.CharField(max_length=500, blank=True)  # S3 object key if stored there
    
    # Metadata
    description = models.TextField(blank=True)
    tags = models.CharField(max_length=500, blank=True)  # comma-separated
    
    # Statistics
    download_count = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Malware scanning
    scan_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('clean', 'Clean'), ('infected', 'Infected'), ('skipped', 'Skipped')],
        default='pending'
    )
    scan_result = models.TextField(blank=True)
    scanned_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'created_at']),
            models.Index(fields=['access_token']),
            models.Index(fields=['file_hash']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.original_filename} ({self.id})"
    
    def is_expired(self):
        """Check if file has expired"""
        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at
    
    def is_accessible(self, viewer=None, password=None):
        """Check if file is accessible to viewer"""
        # Check expiry
        if self.is_expired():
            if self.auto_delete:
                self.delete()
            return False
        
        # Public access
        if self.visibility == 'public':
            return True
        
        # Owner access
        if viewer and viewer == self.owner:
            return True
        
        # Password protected
        if self.visibility == 'password':
            if password is None:
                return False
            from django.contrib.auth.hashers import check_password
            return check_password(password, self.password_hash)
        
        # Private - owner only
        return False
    
    def get_share_url(self):
        """Generate shareable URL"""
        return reverse('fileshare:download', kwargs={'token': self.access_token})
    
    def mark_accessed(self):
        """Update access timestamp and increment counter"""
        self.download_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['download_count', 'last_accessed'])


class DownloadLog(models.Model):
    """Track download activity for analytics"""
    
    id = models.BigAutoField(primary_key=True)
    file = models.ForeignKey(FileUpload, on_delete=models.CASCADE, related_name='download_logs')
    downloader_ip = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    downloaded_at = models.DateTimeField(auto_now_add=True)
    downloaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['file', 'downloaded_at']),
            models.Index(fields=['downloader_ip']),
        ]
    
    def __str__(self):
        return f"{self.file.original_filename} - {self.downloader_ip} - {self.downloaded_at}"


class StorageQuota(models.Model):
    """User storage quotas (FREE_TIER, PRO, ENTERPRISE)"""
    
    PLAN_CHOICES = [
        ('free', 'Free Tier'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='storage_quota')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    
    # Limits in bytes
    max_storage = models.BigIntegerField()  # Total allowed storage
    max_file_size = models.BigIntegerField()  # Per-file limit
    max_retention_days = models.IntegerField()  # How long files persist (NULL = unlimited)
    concurrent_uploads = models.IntegerField(default=5)  # Parallel upload limit
    
    # Current usage
    current_usage = models.BigIntegerField(default=0)
    
    # Features
    allow_password_protection = models.BooleanField(default=False)
    allow_expiry = models.BooleanField(default=False)
    allow_download_tracking = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Storage Quotas'
    
    def __str__(self):
        return f"{self.user.username} - {self.plan}"
    
    def get_available_storage(self):
        """Get remaining storage in bytes"""
        return max(0, self.max_storage - self.current_usage)
    
    def has_capacity_for(self, file_size):
        """Check if user can upload a file of given size"""
        return (
            file_size <= self.max_file_size and
            file_size <= self.get_available_storage()
        )
    
    @staticmethod
    def get_or_create_for_user(user):
        """Create default quota for new users"""
        quota, created = StorageQuota.objects.get_or_create(
            user=user,
            defaults={
                'plan': 'free',
                'max_storage': 5 * 1024 * 1024 * 1024,  # 5GB free
                'max_file_size': 500 * 1024 * 1024,  # 500MB per file
                'max_retention_days': 30,
            }
        )
        return quota


class RateLimitExceeded(models.Model):
    """Track rate limit violations for security"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    endpoint = models.CharField(max_length=200)
    attempts = models.IntegerField(default=1)
    first_attempt = models.DateTimeField(auto_now_add=True)
    last_attempt = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'ip_address', 'endpoint')
        indexes = [
            models.Index(fields=['ip_address', 'endpoint']),
        ]
    
    def __str__(self):
        return f"{self.ip_address} - {self.endpoint} ({self.attempts} attempts)"
