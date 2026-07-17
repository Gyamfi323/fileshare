from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import FileUpload
import secrets

@csrf_exempt
def upload_file(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file'}, status=400)
    
    file_obj = request.FILES['file']
    token = secrets.token_urlsafe(32)
    
    upload = FileUpload.objects.create(
        original_filename=file_obj.name,
        file=file_obj,
        file_size=file_obj.size,
        file_hash=secrets.token_hex(16),
        mime_type='application/octet-stream',
        visibility='public',
        access_token=token,
    )
    
    # Build URL with HTTPS for ngrok
    base_url = request.build_absolute_uri('/').rstrip('/')
    
    # Force HTTPS if it's ngrok
    if 'ngrok' in base_url:
        base_url = base_url.replace('http://', 'https://')
    
    download_link = f"{base_url}/fileshare/download/{token}/"
    
    return JsonResponse({
        'link': download_link,
        'filename': file_obj.name,
        'size_mb': round(file_obj.size / 1024 / 1024, 2)
    }, status=201)

@csrf_exempt
def download_file(request, token):
    file_obj = get_object_or_404(FileUpload, access_token=token)
    file_obj.download_count += 1
    file_obj.save()
    return FileResponse(file_obj.file.open('rb'), as_attachment=True, filename=file_obj.original_filename)

def upload_page(request):
    from django.http import HttpResponse
    with open('static/upload/index.html', 'r') as f:
        return HttpResponse(f.read())
