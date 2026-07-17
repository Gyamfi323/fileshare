# FileShare - GoFile.io Clone

A production-ready Django file-sharing platform. Upload files instantly, get shareable links, no login required.

## Features

✅ **Anonymous Uploads** - No registration needed  
✅ **Instant Share Links** - Get download link immediately  
✅ **No File Restrictions** - Upload ANY file type  
✅ **Download Tracking** - Count downloads per file  
✅ **HTTPS Ready** - Works with ngrok, Let's Encrypt, cPanel SSL  

---

## Quick Start (Local)

```bash
git clone https://github.com/Gyamfi323/fileshare.git
cd fileshare
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

Visit: http://localhost:8000/fileshare/upload/

---

## CPanel Deployment (5 Steps)

### Step 1: Upload to Server

```bash
ssh username@yourdomain.com
cd public_html
git clone https://github.com/Gyamfi323/fileshare.git
cd fileshare
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Configure Django

Edit `config/settings.py`:

```python
DEBUG = False
SECRET_KEY = 'your-new-secret-key'
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']
SECURE_SSL_REDIRECT = True
MEDIA_ROOT = '/home/username/public_html/fileshare/media'
STATIC_ROOT = '/home/username/public_html/fileshare/staticfiles'
```

### Step 4: Database & Files

```bash
python manage.py makemigrations fileshare
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
chmod 777 media/
chmod 666 db.sqlite3
```

### Step 5: Configure CPanel

1. Go to **cPanel > Setup Python App**
2. Click **Create Application**
3. Set:
   - **Python Version:** 3.9+
   - **Application root:** `/home/username/public_html/fileshare`
   - **Application URL:** `yourdomain.com`
   - **Application startup file:** `config/wsgi.py`
4. Click **Create**
5. Go to **SSL/TLS > AutoSSL** - Install Let's Encrypt

### Done! 

Visit: `https://yourdomain.com/fileshare/upload/`

---

## ngrok Setup (Test Anywhere)

```bash
brew install ngrok
ngrok config add-authtoken YOUR_TOKEN
ngrok http 8000
```

Use the generated URL: `https://abc123xyz.ngrok-free.dev/fileshare/upload/`

---

## Admin Panel

Local: http://localhost:8000/admin/  
CPanel: https://yourdomain.com/admin/

---

## API Endpoints

**Upload File:**
```bash
curl -X POST https://yourdomain.com/fileshare/api/upload/ \
  -F "file=@myfile.zip"
```

**Response:**
```json
{
  "link": "https://yourdomain.com/fileshare/download/TOKEN/",
  "filename": "myfile.zip",
  "size_mb": 2.5
}
```

**Download File:**
```bash
curl -O https://yourdomain.com/fileshare/download/TOKEN/
```

---

## Troubleshooting

### "Files not uploading on CPanel"
```bash
chmod 777 media/
chmod 666 db.sqlite3
```

### "Static files not loading"
```bash
python manage.py collectstatic --noinput --clear
touch tmp/restart.txt
```

### "Internal Server Error (500)"
```bash
tail -f error_log
cat logs/error_log
```

---

## Complete Deployment Guide

For detailed CPanel deployment steps, see: **[docs/CPANEL_DEPLOYMENT.md](docs/CPANEL_DEPLOYMENT.md)**

---

## License

MIT License - Free to use and deploy

**Built with Django • Django REST Framework • ❤️**

---

**Version:** 1.0.0  
**Author:** Francis Adu Gyamfi  
**GitHub:** https://github.com/Gyamfi323/fileshare
