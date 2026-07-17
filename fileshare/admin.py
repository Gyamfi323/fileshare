"""
FileShare Django Admin Configuration
Manage files, downloads, and quotas from admin panel
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import FileUpload, DownloadLog, StorageQuota


@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    """Admin interface for uploaded files"""
    
    list_display = (
        'filename_link', 'owner', 'size_display', 
        'download_count', 'visibility', 'expires_display', 'scan_status'
    )
    list_filter = ('visibility', 'scan_status', 'created_at', 'expires_at')
    search_fields = ('original_filename', 'owner__username', 'file_hash')
    readonly_fields = (
        'id', 'file_hash', 'access_token', 'created_at', 
        'updated_at', 'scanned_at', 'file_size'
    )
    
    fieldsets = (
        ('File Info', {
            'fields': ('id', 'original_filename', 'file', 'file_size', 'mime_type', 'file_hash')
        }),
        ('Ownership & Access', {
            'fields': ('owner', 'visibility', 'password_hash', 'access_token')
        }),
        ('Sharing & Expiry', {
            'fields': ('expires_at', 'auto_delete', 'download_count', 'last_accessed')
        }),
        ('Malware Scanning', {
            'fields': ('scan_status', 'scan_result', 'scanned_at')
        }),
        ('Storage', {
            'fields': ('storage_backend', 's3_key')
        }),
        ('Metadata', {
            'fields': ('description', 'tags')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def filename_link(self, obj):
        """Display filename with download link"""
        return format_html(
            '<a href="{}">{}</a>',
            f'/fileshare/download/{obj.access_token}/',
            obj.original_filename
        )
    filename_link.short_description = 'Filename'
    
    def size_display(self, obj):
        """Display file size in MB"""
        mb = obj.file_size / 1024 / 1024
        return f"{mb:.2f} MB"
    size_display.short_description = 'Size'
    
    def expires_display(self, obj):
        """Display expiry status"""
        if obj.expires_at is None:
            return format_html('<span style="color: green;">Never</span>')
        if obj.is_expired():
            return format_html('<span style="color: red;">Expired</span>')
        return obj.expires_at.strftime('%Y-%m-%d %H:%M')
    expires_display.short_description = 'Expires'


@admin.register(DownloadLog)
class DownloadLogAdmin(admin.ModelAdmin):
    """Admin interface for download logs"""
    
    list_display = ('file_display', 'downloader_ip', 'downloaded_by', 'downloaded_at')
    list_filter = ('downloaded_at', 'downloader_ip')
    search_fields = ('file__original_filename', 'downloader_ip', 'downloaded_by__username')
    readonly_fields = ('id', 'file', 'downloader_ip', 'user_agent', 'downloaded_at', 'downloaded_by')
    
    def file_display(self, obj):
        """Link to the file"""
        return format_html(
            '<a href="/admin/fileshare/fileupload/{}/change/">{}</a>',
            obj.file.id,
            obj.file.original_filename
        )
    file_display.short_description = 'File'
    
    def has_add_permission(self, request):
        """Download logs are auto-created, don't allow manual adding"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only admins can delete logs"""
        return request.user.is_staff


@admin.register(StorageQuota)
class StorageQuotaAdmin(admin.ModelAdmin):
    """Admin interface for user storage quotas"""
    
    list_display = ('user', 'plan', 'usage_display', 'features_display')
    list_filter = ('plan',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('user', 'current_usage', 'created_at', 'updated_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user', 'plan')
        }),
        ('Storage Limits', {
            'fields': ('max_storage', 'current_usage', 'max_file_size', 'max_retention_days')
        }),
        ('Features', {
            'fields': (
                'allow_password_protection', 'allow_expiry', 
                'allow_download_tracking', 'concurrent_uploads'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def usage_display(self, obj):
        """Display storage usage as percentage"""
        if obj.max_storage == 0:
            return "N/A"
        percent = (obj.current_usage / obj.max_storage) * 100
        used_gb = obj.current_usage / 1024 / 1024 / 1024
        max_gb = obj.max_storage / 1024 / 1024 / 1024
        
        if percent > 90:
            color = 'red'
        elif percent > 70:
            color = 'orange'
        else:
            color = 'green'
        
        return format_html(
            '<span style="color: {};">{:.2f} GB / {:.2f} GB ({:.1f}%)</span>',
            color, used_gb, max_gb, percent
        )
    usage_display.short_description = 'Usage'
    
    def features_display(self, obj):
        """Display enabled features"""
        features = []
        if obj.allow_password_protection:
            features.append('🔐 Password')
        if obj.allow_expiry:
            features.append('⏰ Expiry')
        if obj.allow_download_tracking:
            features.append('📊 Tracking')
        return ' '.join(features) if features else 'Basic'
    features_display.short_description = 'Features'


# Customize admin site
admin.site.site_header = "FileShare Administration"
admin.site.site_title = "FileShare Admin"
admin.site.index_title = "Welcome to FileShare Admin"
