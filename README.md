# FileShare - GoFile.io Clone

A production-ready Django file-sharing platform. Upload files instantly, get shareable links, no login required.

## Features

✅ **Anonymous Uploads** - No registration needed  
✅ **Instant Share Links** - Get download link immediately  
✅ **No File Restrictions** - Upload ANY file type  
✅ **Download Tracking** - Count downloads per file  
✅ **HTTPS Ready** - Works with ngrok, Let's Encrypt, cPanel SSL  

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/fileshare.git
cd fileshare
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

Visit: http://localhost:8000/fileshare/upload/

## Deployment

- **Local:** Follow Quick Start above
- **ngrok:** `ngrok http 8000`
- **cPanel:** See `docs/CPANEL_DEPLOYMENT.md`
- **GitHub:** See `docs/GITHUB_SETUP.md`

## Admin Panel

http://localhost:8000/admin/

## API

POST `/fileshare/api/upload/` - Upload file  
GET `/fileshare/download/[TOKEN]/` - Download file

## License

MIT License

---

For complete documentation, see docs/ folder.
