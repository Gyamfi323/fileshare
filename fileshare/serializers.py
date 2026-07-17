"""
FileShare Serializers
Convert Django models to JSON for API responses
"""

from rest_framework import serializers
from .models import FileUpload, DownloadLog, StorageQuota


class FileUploadSerializer(serializers.ModelSerializer):
    """Serialize FileUpload model"""
    
    file_url = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = FileUpload
        fields = [
            'id', 'original_filename', 'file_size', 'size_mb', 'mime_type',
            'visibility', 'access_token', 'file_url', 'download_count', 
            'created_at', 'expires_at', 'owner_username', 'description',
            'scan_status', 'last_accessed'
        ]
        read_only_fields = [
            'id', 'file_url', 'access_token', 'download_count', 
            'created_at', 'owner_username', 'size_mb'
        ]
    
    def get_file_url(self, obj):
        """Generate shareable URL"""
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/fileshare/download/{obj.access_token}/')
        return f'/fileshare/download/{obj.access_token}/'
    
    def get_size_mb(self, obj):
        """Convert bytes to MB"""
        return round(obj.file_size / 1024 / 1024, 2)


class DownloadLogSerializer(serializers.ModelSerializer):
    """Serialize DownloadLog model"""
    
    class Meta:
        model = DownloadLog
        fields = ['id', 'downloader_ip', 'downloaded_at', 'user_agent']
        read_only_fields = fields


class StorageQuotaSerializer(serializers.ModelSerializer):
    """Serialize StorageQuota model"""
    
    username = serializers.CharField(source='user.username', read_only=True)
    usage_percent = serializers.SerializerMethodField()
    available_gb = serializers.SerializerMethodField()
    used_gb = serializers.SerializerMethodField()
    max_gb = serializers.SerializerMethodField()
    
    class Meta:
        model = StorageQuota
        fields = [
            'username', 'plan', 'max_storage', 'current_usage',
            'max_file_size', 'max_retention_days', 'usage_percent',
            'used_gb', 'available_gb', 'max_gb', 'allow_password_protection',
            'allow_expiry', 'allow_download_tracking', 'concurrent_uploads'
        ]
        read_only_fields = fields
    
    def get_usage_percent(self, obj):
        """Calculate usage percentage"""
        if obj.max_storage == 0:
            return 0
        return round((obj.current_usage / obj.max_storage) * 100, 1)
    
    def get_used_gb(self, obj):
        """Convert current usage to GB"""
        return round(obj.current_usage / 1024 / 1024 / 1024, 2)
    
    def get_available_gb(self, obj):
        """Convert available space to GB"""
        available = obj.get_available_storage()
        return round(available / 1024 / 1024 / 1024, 2)
    
    def get_max_gb(self, obj):
        """Convert max storage to GB"""
        return round(obj.max_storage / 1024 / 1024 / 1024, 2)
