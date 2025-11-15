# 🔧 Correcciones Urgentes para Predicta

## Problema 1: Entorno Virtual - RUTA INCORRECTA

### Error encontrado:
```bash
source /var/www/predicta.com.co/app/.venv/bin/activate
# Error: No such file or directory
```

### Solución:
El entorno virtual está en la raíz del proyecto, no en `app/.venv/`:

```bash
# En el servidor Linux:
cd /var/www/predicta.com.co
source venv/bin/activate
```

### Verificación:
```bash
which python  # Debe mostrar: /var/www/predicta.com.co/venv/bin/python
python --version
pip list  # Verificar que Django y otras dependencias estén instaladas
```

---

## Problema 2: Configuración de Producción Insegura

### Cambios necesarios en `betting_bot/settings.py`:

#### 1. Agregar soporte para variables de entorno al inicio del archivo:

```python
from pathlib import Path
import os
from decouple import config, Csv  # Ya está en requirements.txt

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
```

#### 2. Reemplazar configuración insegura:

**ANTES (INSEGURO):**
```python
SECRET_KEY = 'django-insecure-05hl%jnp2o6j)8)zo=u8eu9_zkk7yd8h7&w^x6xix%@y*owsu+'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
```

**DESPUÉS (SEGURO):**
```python
SECRET_KEY = config('SECRET_KEY', default='django-insecure-05hl%jnp2o6j)8)zo=u8eu9_zkk7yd8h7&w^x6xix%@y*owsu+')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
```

#### 3. Crear archivo `.env` en el servidor:

```bash
cd /var/www/predicta.com.co
cp env_example.txt .env
nano .env
```

**Contenido del `.env` (editar con valores reales):**
```env
# Django Configuration
SECRET_KEY=tu-clave-secreta-generada-aqui-muy-larga-y-aleatoria
DEBUG=False
ALLOWED_HOSTS=predicta.com.co,www.predicta.com.co,localhost,127.0.0.1

# The Odds API Configuration
ODDS_API_KEY=9c2c101074ae4a4c3ec9b01a4d38cb6a

# Betfair API Configuration
BETFAIR_APP_KEY=your_betfair_app_key_here
BETFAIR_USERNAME=your_betfair_username_here
BETFAIR_PASSWORD=your_betfair_password_here
BETFAIR_SANDBOX=True

# Bot Configuration
SPORT_KEY=soccer_epl
REGIONS=uk,us,eu
MARKETS=h2h
ODDS_FORMAT=decimal

# Betting Configuration
MIN_STAKE=1.0
MAX_STAKE=10.0
MIN_EDGE=0.05

# Execution Configuration
EXECUTION_INTERVAL=10
```

**⚠️ IMPORTANTE:** 
- Generar una nueva `SECRET_KEY` segura (puedes usar: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- Cambiar `DEBUG=False` para producción
- Agregar el dominio real a `ALLOWED_HOSTS`
- Proteger el archivo `.env`: `chmod 600 .env`

---

## Problema 3: Archivo de Configuración de Gunicorn

### Crear `gunicorn_config.py` en la raíz del proyecto:

```python
# gunicorn_config.py
import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = os.path.join(os.path.dirname(__file__), "logs", "gunicorn_access.log")
errorlog = os.path.join(os.path.dirname(__file__), "logs", "gunicorn_error.log")
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "predicta_gunicorn"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn_predicta.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (si está configurado)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
```

### Verificar servicio systemd:

El servicio systemd probablemente esté en `/etc/systemd/system/gunicorn.service`. Verificar que apunte a la configuración correcta:

```bash
sudo cat /etc/systemd/system/gunicorn.service
```

Debería contener algo como:
```ini
[Unit]
Description=gunicorn daemon for Predicta
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/predicta.com.co
ExecStart=/var/www/predicta.com.co/venv/bin/gunicorn \
    --config /var/www/predicta.com.co/gunicorn_config.py \
    betting_bot.wsgi:application

Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Pasos de Implementación (Ejecutar en orden)

### 1. Activar entorno virtual correctamente:
```bash
cd /var/www/predicta.com.co
source venv/bin/activate
```

### 2. Verificar que python-decouple esté instalado:
```bash
pip install python-decouple
# o
pip install -r requirements.txt
```

### 3. Crear archivo `.env`:
```bash
cp env_example.txt .env
chmod 600 .env
nano .env  # Editar con valores reales
```

### 4. Generar nueva SECRET_KEY:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# Copiar el resultado al archivo .env
```

### 5. Actualizar `settings.py`:
- Agregar `from decouple import config, Csv`
- Reemplazar `SECRET_KEY`, `DEBUG`, y `ALLOWED_HOSTS` como se muestra arriba

### 6. Crear `gunicorn_config.py`:
- Crear el archivo con el contenido proporcionado arriba

### 7. Verificar configuración:
```bash
python manage.py check --deploy
```

### 8. Aplicar migraciones (si es necesario):
```bash
python manage.py migrate
```

### 9. Recopilar archivos estáticos:
```bash
python manage.py collectstatic --noinput
```

### 10. Reiniciar servicio:
```bash
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
```

### 11. Verificar logs:
```bash
journalctl -u gunicorn -f
tail -f logs/betting_bot.log
```

---

## Verificación Final

### Checklist de seguridad:
- [ ] `DEBUG = False` en producción
- [ ] `SECRET_KEY` en `.env` (no en código)
- [ ] `ALLOWED_HOSTS` incluye el dominio real
- [ ] Archivo `.env` tiene permisos 600
- [ ] Servicio Gunicorn funcionando
- [ ] No hay errores en los logs
- [ ] El sitio responde correctamente

### Comandos de prueba:
```bash
# Verificar que el entorno virtual funciona
source venv/bin/activate
python manage.py check

# Verificar que el servicio está activo
systemctl is-active gunicorn

# Verificar que el sitio responde
curl http://localhost:8000
# o desde el navegador: http://predicta.com.co
```

---

## Notas Importantes

1. **Backup antes de cambios:** Siempre hacer backup de `settings.py` y la base de datos antes de modificar
2. **Probar en desarrollo primero:** Si es posible, probar los cambios en un entorno de desarrollo antes de producción
3. **Monitorear logs:** Después de los cambios, monitorear los logs durante las primeras horas
4. **Permisos:** Asegurarse de que los archivos tengan los permisos correctos (`.env` debe ser 600)

---

*Documento de correcciones urgentes - Revisar y aplicar según el entorno específico*

