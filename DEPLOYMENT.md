# Deployment Guide for WeSolar

This guide covers how to deploy the WeSolar project to a Linux server (Ubuntu/Debian) that **already hosts other websites**.

> [!IMPORTANT]
> **Safety First**: Since other sites are running, we will:
> 1. Use a **unique port** (e.g., 8001) for this application.
> 2. Use `nginx -s reload` instead of restart to avoid downtime for other sites.

## 1. Prerequisites

Ensure these are installed on the server:
- Python 3.10+
- Supervisor (optional but recommended for managing Gunicorn)
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
   Add:
   ```ini
   DJANGO_DEBUG=False
   DJANGO_SECRET_KEY=your-secure-secret-key-here
   ```

4. **Database & Static Files**:
   ```bash
   python manage.py migrate
   python manage.py collectstatic
   ```

## 3. Gunicorn Setup

Test it first to make sure it runs (we use port **8005** to be safe):
```bash
gunicorn --bind 0.0.0.0:8005 wesolar_web.wsgi
```
*Press Ctrl+C to stop.*

### Create a Systemd Service (Recommended)
Create a service file so the app stays running: `sudo nano /etc/systemd/system/wesolar.service`

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
*Note: The socket file `wesolar.sock` handles the connection, so the port is only needed if you run Gunicorn manually without a socket. If using the service above, we use a socket file which avoids port conflicts entirely!* 

Start it:
```bash
sudo systemctl start wesolar
sudo systemctl enable wesolar
```

## 4. Nginx Configuration (Safe Deployment)

We will add a **new** server block instead of modifying the default one.

1. **Create Config**: `sudo nano /etc/nginx/sites-available/wesolar`

   ```nginx
   server {
       listen 80;
       server_name wesolar.fastcopies.in;

       location = /favicon.ico { access_log off; log_not_found off; }
       
       location /static/ {
           alias /var/www/wesolar/staticfiles/;
       }

       location /media/ {
           root /var/www/wesolar;
       }

       location / {
           include proxy_params;
           proxy_pass http://unix:/var/www/wesolar/wesolar.sock;
       }
   }
   ```

2. **Enable Site**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/wesolar /etc/nginx/sites-enabled/
   ```

3. **Test Configuration** (Crucial step!):
   ```bash
   sudo nginx -t
   ```
   *Only proceed if this says "syntax is ok" and "test is successful".*

4. **Reload Nginx** (Safe):
   ```bash
   sudo nginx -s reload
   ```
   *This will load the new config without dropping connections for other sites.*

## 5. HTTPS Setup (Let's Encrypt)

Secure your site with a free SSL certificate.

1.  **Install Certbot**:
    ```bash
    sudo apt install certbot python3-certbot-nginx
    ```

2.  **Obtain Certificate**:
    ```bash
    sudo certbot --nginx -d wesolar.fastcopies.in
    ```
    - Enter your email when asked.
    - Agree to terms (type 'Y').
    - Choose to **redirect HTTP to HTTPS** (usually option 2) if asked.

3.  **Verify**:
    Visit https://wesolar.fastcopies.in

## 6. Updating Code Later

When you need to update the version:

1. `cd /var/www/wesolar`
2. `git pull`
3. `source venv/bin/activate && pip install -r requirements.txt` (only if requirements changed)
4. `python manage.py migrate` (only if DB models changed)
5. `python manage.py collectstatic --noinput`
6. `sudo systemctl restart wesolar` (Restart the Python app only, Nginx stays up)
