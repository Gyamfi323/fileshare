"""
FileShare Django App - Utility Functions
File validation, hashing, token generation, malware scanning, storage backends
"""

import hashlib
import secrets
import mimetypes
import logging
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.files.storage import default_storage
from io import BytesIO
import os

logger = logging.getLogger(__name__)


# =============================================================================
# FILE HASHING & VALIDATION
# =============================================================================

def compute_file_hash(file_obj, algorithm='sha256', chunk_size=8192):
    """
    Compute hash of uploaded file for deduplication
    Supports: sha256, md5, sha512
    """
    hasher = hashlib.new(algorithm)
    file_obj.seek(0)
    
    while True:
        chunk = file_obj.read(chunk_size)
        if not chunk:
            break
        hasher.update(chunk)
    
    file_obj.seek(0)  # Reset file pointer
    return hasher.hexdigest()


def generate_access_token(length=32):
    """Generate cryptographically secure random access token"""
    return secrets.token_urlsafe(length)


# =============================================================================
# FILE VALIDATION
# =============================================================================

# Whitelist of allowed file extensions
ALLOWED_EXTENSIONS = {
    # Documents
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf',
    # Images
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'ico', 'bmp',
    # Archives
    'zip', '7z', 'rar', 'tar', 'gz', 'tar.gz', 'tar.bz2',
    # Media
    'mp3', 'mp4', 'wav', 'avi', 'mov', 'mkv', 'flv', 'webm',
    # Code
    'py', 'js', 'ts', 'java', 'cpp', 'c', 'cs', 'go', 'rb', 'php', 'json', 'xml', 'html', 'css',
    # Data
    'csv', 'json', 'sql', 'db', 'sqlite',
}

# Blacklist (even if extension is in whitelist)
# NOTE: 'exe' REMOVED to match GoFile - allows .exe uploads
# If you want security, use ClamAV scanning (scan_file_with_clamav.delay())
BLACKLISTED_EXTENSIONS = {
    'bat', 'cmd', 'com', 'scr', 'vbs',  # Script files
    # 'exe' INTENTIONALLY REMOVED - GoFile allows .exe files
    # Use ClamAV antivirus scanning instead for safety!
}

# MIME type validation
SAFE_MIME_TYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain',
    'text/csv',
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'audio/mpeg',
    'audio/wav',
    'video/mp4',
    'video/webm',
    'application/json',
    'application/xml',
    'text/html',
    'text/css',
}


def validate_file_extension(filename, user):
    """
    Validate file extension against whitelist/blacklist
    Raises ValidationError if file is not allowed
    """
    
    # Get extension
    _, ext = os.path.splitext(filename)
    ext = ext.lstrip('.').lower()
    
    # Check double extensions (e.g., .pdf.exe)
    parts = filename.lower().split('.')
    if len(parts) > 2:
        # Check if second-to-last is blacklisted
        if parts[-2] in BLACKLISTED_EXTENSIONS:
            raise ValidationError(f"Suspicious file extension: .{parts[-2]}")
    
    # Blacklist check
    if ext in BLACKLISTED_EXTENSIONS:
        raise ValidationError(f"File type .{ext} is not allowed")
    
    # Whitelist check for free tier
    if user.storage_quota.plan == 'free':
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError(
                f"File type .{ext} is not allowed for free tier. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
    
    return True


def validate_file_content(file_obj):
    """
    Validate file content for malware/suspicious content
    Returns (is_safe, reason)
    """
    file_obj.seek(0)
    header = file_obj.read(512)
    file_obj.seek(0)
    
    # Check for common executable signatures
    dangerous_signatures = {
        b'MZ': 'Windows executable',  # .exe, .dll, .sys
        b'PK\x03\x04': None,  # ZIP (benign, could be .docx, .xlsx, etc)
        b'\x7fELF': 'Linux executable',  # ELF
        b'\xFE\xED\xFA': 'Mach-O executable',  # macOS
        b'%PDF': None,  # PDF (benign)
    }
    
    for sig, name in dangerous_signatures.items():
        if header.startswith(sig):
            if name:
                return False, f"Detected {name} signature"
    
    return True, None


# =============================================================================
# MALWARE SCANNING (ClamAV Integration)
# =============================================================================

def scan_file_with_clamav(file_id):
    """
    Scan file with ClamAV antivirus
    To be run as Celery async task
    
    Usage in views:
        scan_file_with_clamav.delay(upload.id)
    
    Requires:
    1. ClamAV daemon running: sudo systemctl start clamav-daemon
    2. celery-beat for periodic scanning
    """
    from .models import FileUpload
    
    try:
        import pyclamd
        
        upload = FileUpload.objects.get(id=file_id)
        
        # Connect to ClamAV daemon
        clam = pyclamd.ClamD()
        
        if not clam.ping():
            logger.error("ClamAV daemon not responding")
            upload.scan_status = 'skipped'
            upload.scan_result = 'ClamAV unavailable'
            upload.save()
            return
        
        # Scan file
        file_path = upload.file.path
        result = clam.scan_file(file_path)
        
        if result is None:
            # No virus found
            upload.scan_status = 'clean'
            upload.scan_result = 'No threats detected'
        else:
            # Virus detected
            upload.scan_status = 'infected'
            virus_name = str(result).split(':')[1] if ':' in str(result) else 'Unknown'
            upload.scan_result = f"Virus detected: {virus_name}"
            logger.warning(f"INFECTED FILE: {upload.id} - {virus_name}")
        
        from django.utils import timezone
        upload.scanned_at = timezone.now()
        upload.save()
        
    except ImportError:
        logger.error("pyclamd not installed. Install with: pip install pyclamd")
        upload.scan_status = 'skipped'
        upload.scan_result = 'Scanner not installed'
        upload.save()
    except Exception as e:
        logger.error(f"Malware scan failed for {file_id}: {str(e)}")
        upload.scan_status = 'skipped'
        upload.scan_result = f"Scan error: {str(e)}"
        upload.save()


# =============================================================================
# STORAGE BACKENDS
# =============================================================================

class LocalStorageBackend:
    """Local filesystem storage"""
    
    @staticmethod
    def save(file_obj, path):
        """Save file locally"""
        return default_storage.save(path, file_obj)
    
    @staticmethod
    def get_file(path):
        """Retrieve file from local storage"""
        if not default_storage.exists(path):
            return None
        return default_storage.open(path, 'rb')
    
    @staticmethod
    def delete(path):
        """Delete file from local storage"""
        if default_storage.exists(path):
            default_storage.delete(path)
    
    @staticmethod
    def exists(path):
        """Check if file exists"""
        return default_storage.exists(path)


class S3StorageBackend:
    """AWS S3 storage backend"""
    
    def __init__(self):
        self.bucket = settings.AWS_STORAGE_BUCKET_NAME
        self.s3_client = self._get_client()
    
    def _get_client(self):
        """Get boto3 S3 client"""
        try:
            import boto3
            return boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )
        except ImportError:
            raise ImportError("boto3 not installed. Install with: pip install boto3")
    
    def save(self, file_obj, path):
        """Upload file to S3"""
        try:
            file_obj.seek(0)
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket,
                path,
                ExtraArgs={'ServerSideEncryption': 'AES256'}
            )
            return path
        except Exception as e:
            logger.error(f"S3 upload failed: {str(e)}")
            raise
    
    def get_file(self, path):
        """Download file from S3"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=path)
            return response['Body']
        except Exception as e:
            logger.error(f"S3 download failed: {str(e)}")
            return None
    
    def delete(self, path):
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=path)
        except Exception as e:
            logger.error(f"S3 delete failed: {str(e)}")
    
    def get_signed_url(self, path, expiry_seconds=3600):
        """Generate presigned URL for direct S3 access"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': path},
                ExpiresIn=expiry_seconds
            )
            return url
        except Exception as e:
            logger.error(f"Presigned URL generation failed: {str(e)}")
            return None


# =============================================================================
# NETWORK & CLIENT INFO
# =============================================================================

def get_client_ip(request):
    """
    Extract client IP from request
    Handles X-Forwarded-For, X-Real-IP, etc (proxy support)
    """
    # Check for forwarded IPs (behind proxy)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
        return ip
    
    # Check X-Real-IP (Nginx proxy)
    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    if x_real_ip:
        return x_real_ip
    
    # Fallback to direct connection
    return request.META.get('REMOTE_ADDR')


# =============================================================================
# CLEANUP & MAINTENANCE
# =============================================================================

def cleanup_expired_files():
    """
    Cleanup expired files
    Should be run via Celery beat: @periodic_task(run_every=crontab(minute=0))
    """
    from .models import FileUpload, StorageQuota
    from django.utils import timezone
    
    expired = FileUpload.objects.filter(
        expires_at__lt=timezone.now(),
        auto_delete=True
    )
    
    total_freed = 0
    
    for file_obj in expired:
        # Update quota
        quota = StorageQuota.objects.get(user=file_obj.owner)
        quota.current_usage -= file_obj.file_size
        quota.save()
        
        # Delete file
        if file_obj.file:
            file_obj.file.delete()
        
        total_freed += file_obj.file_size
        file_obj.delete()
    
    logger.info(f"Cleaned up {expired.count()} expired files, freed {total_freed} bytes")
    return expired.count()


def cleanup_old_download_logs(days=90):
    """Delete download logs older than N days"""
    from .models import DownloadLog
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = DownloadLog.objects.filter(downloaded_at__lt=cutoff).delete()
    
    logger.info(f"Cleaned up {deleted} old download logs")
    return deleted
