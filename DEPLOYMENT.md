# Deployment Guide for WeSolar

This guide covers how to deploy the WeSolar project to a Linux server (Ubuntu/Debian).

## 1. Prerequisites

Ensure these are installed on the server:
- Python 3.10+
- Gunicorn
- Nginx

## 2. Project Setup on Server

1. **Clone/Copy Project**:
   ```bash
   cd /var/www/
   git clone https://github.com/phanindrauddagiri05-ops/wesolar.git wesolar
   cd wesolar
   ```

2. **Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Environment Variables**:
   Create a `.env` file in the project root:
   ```bash
   nano .env
   ```
   Add the following (Replace with your actual values):
   ```ini
   DJANGO_DEBUG=False
   DJANGO_SECRET_KEY=your-secure-secret-key-here
   DJANGO_ALLOWED_HOSTS=wesolar.fastcopies.in,localhost,127.0.0.1
   DJANGO_CSRF_TRUSTED_ORIGINS=https://wesolar.fastcopies.in
   ```

4. **Database & Static Files**:
   ```bash
   python manage.py migrate
   python manage.py collectstatic
   ```

## 3. Gunicorn Setup

Test it first:
```bash
gunicorn --bind 0.0.0.0:8005 wesolar_web.wsgi
```
*Press Ctrl+C to stop.*

### Create a Systemd Service
`sudo nano /etc/systemd/system/wesolar.service`

```ini
[Unit]
Description=WeSolar Gunicorn Daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/wesolar
ExecStart=/var/www/wesolar/venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/var/www/wesolar/wesolar.sock \
          wesolar_web.wsgi:application

[Install]
WantedBy=multi-user.target
```

Start it:
```bash
sudo systemctl start wesolar
sudo systemctl enable wesolar
```

## 4. Nginx Configuration

`sudo nano /etc/nginx/sites-available/wesolar`

```nginx
server {
    listen 80;
    server_name wesolar.fastcopies.in;

    location = /favicon.ico { access_log off; log_not_found off; }

    # Static files are handled by WhiteNoise, but Nginx can serve media
    location /media/ {
        root /var/www/wesolar;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/wesolar/wesolar.sock;
    }
}
```

Enable Site:
```bash
sudo ln -s /etc/nginx/sites-available/wesolar /etc/nginx/sites-enabled/
sudo nginx -t
sudo nginx -s reload
```

## 5. HTTPS Setup (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d wesolar.fastcopies.in
```

## 6. Updating Code Later
1. `cd /var/www/wesolar`
2. `git pull`
3. `source venv/bin/activate && pip install -r requirements.txt`
4. `python manage.py migrate`
5. `python manage.py collectstatic --noinput`
6. `sudo systemctl restart wesolar`

