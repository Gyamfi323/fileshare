# CPanel Deployment Guide

## Phase 1: Upload to Server

```bash
ssh username@yourdomain.com
cd public_html
git clone https://github.com/Gyamfi323/fileshare.git
cd fileshare
```

## Phase 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Phase 3: Configure Django

Edit `config/settings.py`:
- Set `DEBUG = False`
- Set `ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']`
- Generate new `SECRET_KEY`

## Phase 4: Database Setup

```bash
python manage.py makemigrations fileshare
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

## Phase 5: Set Permissions

```bash
chmod 755 media/
chmod 755 staticfiles/
chmod 666 db.sqlite3
```

## Phase 6: Configure CPanel

1. Go to **cPanel > Setup Python App**
2. Create Application:
   - Python Version: 3.9+
   - Application root: `/home/username/public_html/fileshare`
   - Application URL: `yourdomain.com`
   - Application startup file: `config/wsgi.py`

## Phase 7: Enable SSL/HTTPS

1. Go to **cPanel > SSL/TLS**
2. Install AutoSSL (Let's Encrypt)

## Phase 8: Test

Visit: `https://yourdomain.com/fileshare/upload/`

## Troubleshooting

**Files not uploading:**
```bash
chmod 777 media/
chmod 666 db.sqlite3
```

**Static files not loading:**
```bash
python manage.py collectstatic --noinput --clear
touch tmp/restart.txt
```

**Internal Server Error:**
```bash
tail -f error_log
cat logs/error_log
```

For complete guide, see main repository README.
