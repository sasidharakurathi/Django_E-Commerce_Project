# 🚀 Deployment Guide

This guide covers deploying the Django E-Commerce Platform to various hosting platforms.

## 📋 Pre-Deployment Checklist

### Security Configuration
- [ ] Set `DEBUG = False` in production
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Use strong `SECRET_KEY` (different from development)
- [ ] Set up HTTPS/SSL certificates
- [ ] Configure secure headers

### Database
- [ ] Use production database (PostgreSQL/MySQL)
- [ ] Set up database backups
- [ ] Configure connection pooling
- [ ] Run migrations on production database

### Static Files
- [ ] Configure static file serving
- [ ] Set up CDN for static files (optional)
- [ ] Optimize images and assets

### Environment Variables
- [ ] Set all production environment variables
- [ ] Configure email settings
- [ ] Set up payment gateway credentials

## 🌐 Heroku Deployment

### Prerequisites
- Heroku account
- Heroku CLI installed
- Git repository

### Step 1: Prepare for Heroku

1. **Create Procfile**
   ```
   web: gunicorn ecommerce.wsgi:application
   ```

2. **Update requirements.txt**
   ```bash
   pip freeze > requirements.txt
   ```

3. **Add Heroku-specific packages**
   ```
   gunicorn==20.1.0
   psycopg2-binary==2.9.3
   whitenoise==6.2.0
   ```

### Step 2: Configure Settings

1. **Create production settings**
   ```python
   # settings.py
   import os
   import dj_database_url
   
   # Production settings
   if 'DATABASE_URL' in os.environ:
       DATABASES['default'] = dj_database_url.parse(os.environ['DATABASE_URL'])
   
   # Static files
   STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
   STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
   
   # Middleware
   MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
   ```

### Step 3: Deploy to Heroku

1. **Login to Heroku**
   ```bash
   heroku login
   ```

2. **Create Heroku app**
   ```bash
   heroku create your-app-name
   ```

3. **Set environment variables**
   ```bash
   heroku config:set SECRET_KEY="your-secret-key"
   heroku config:set DEBUG=False
   heroku config:set EMAIL_HOST_USER="your-email@gmail.com"
   heroku config:set EMAIL_HOST_PASSWORD="your-app-password"
   ```

4. **Add buildpacks**
   ```bash
   heroku buildpacks:add --index 1 heroku/python
   heroku buildpacks:add --index 2 https://github.com/heroku/heroku-buildpack-apt
   ```

5. **Create Aptfile** (for OpenCV dependencies)
   ```
   libsm6
   libxext6
   libxrender-dev
   libglib2.0-0
   libgtk-3-0
   ```

6. **Deploy**
   ```bash
   git add .
   git commit -m "Prepare for Heroku deployment"
   git push heroku main
   ```

7. **Run migrations**
   ```bash
   heroku run python manage.py migrate
   heroku run python manage.py createsuperuser
   ```

## 🐳 Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.9

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        libpq-dev \
        gcc \
        cmake \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libglib2.0-0 \
        libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirement.txt /app/
RUN pip install --no-cache-dir -r requirement.txt

# Copy project
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "ecommerce.wsgi:application"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - SECRET_KEY=your-secret-key
      - DATABASE_URL=postgresql://user:password@db:5432/ecommerce
    depends_on:
      - db
    volumes:
      - ./media:/app/media

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=ecommerce
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## ☁️ AWS Deployment

### Using AWS Elastic Beanstalk

1. **Install EB CLI**
   ```bash
   pip install awsebcli
   ```

2. **Initialize EB application**
   ```bash
   eb init
   ```

3. **Create environment**
   ```bash
   eb create production
   ```

4. **Configure environment variables**
   ```bash
   eb setenv SECRET_KEY="your-secret-key"
   eb setenv DEBUG=False
   ```

5. **Deploy**
   ```bash
   eb deploy
   ```

### Using EC2 with Nginx

1. **Launch EC2 instance**
2. **Install dependencies**
   ```bash
   sudo apt update
   sudo apt install python3-pip nginx postgresql
   ```

3. **Clone repository**
   ```bash
   git clone your-repository-url
   cd your-project
   ```

4. **Set up virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

5. **Configure Nginx**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location /static/ {
           alias /path/to/your/project/staticfiles/;
       }
       
       location /media/ {
           alias /path/to/your/project/media/;
       }
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## 🔧 Production Optimizations

### Database Optimization
```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_db_name',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'your_db_host',
        'PORT': '5432',
        'OPTIONS': {
            'MAX_CONNS': 20,
            'CONN_MAX_AGE': 600,
        }
    }
}
```

### Caching Configuration
```python
# Redis caching
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### Security Headers
```python
# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

## 📊 Monitoring and Logging

### Logging Configuration
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### Health Check Endpoint
```python
# views.py
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({'status': 'healthy'})
```

## 🔄 CI/CD Pipeline

### GitHub Actions Example
```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python manage.py test
    
    - name: Deploy to Heroku
      uses: akhileshns/heroku-deploy@v3.12.12
      with:
        heroku_api_key: ${{secrets.HEROKU_API_KEY}}
        heroku_app_name: "your-app-name"
        heroku_email: "your-email@example.com"
```

## 🆘 Troubleshooting

### Common Issues

1. **Static files not loading**
   - Check `STATIC_ROOT` and `STATIC_URL` settings
   - Run `python manage.py collectstatic`
   - Configure web server to serve static files

2. **Database connection errors**
   - Verify database credentials
   - Check network connectivity
   - Ensure database server is running

3. **Face recognition issues**
   - Install OpenCV dependencies on server
   - Check file permissions for dataset directory
   - Verify camera access (if using live recognition)

### Performance Issues

1. **Slow page loads**
   - Enable database query optimization
   - Implement caching
   - Optimize images and static files

2. **High memory usage**
   - Monitor face recognition processes
   - Implement pagination for large datasets
   - Use database connection pooling

---

For more detailed deployment instructions, refer to the specific platform documentation.
