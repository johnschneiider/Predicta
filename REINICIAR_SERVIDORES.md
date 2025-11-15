# 🔄 Guía para Reiniciar los Servidores

## 🖥️ SERVIDOR LOCAL (Windows - Desarrollo)

### Reiniciar servidor Django de desarrollo

Si el servidor está corriendo, presiona:
```
CTRL + C
```

Luego inicia de nuevo:
```powershell
# Activar entorno virtual
venv\Scripts\Activate.ps1

# Iniciar servidor
python manage.py runserver
```

O en una sola línea:
```powershell
venv\Scripts\Activate.ps1; python manage.py runserver
```

### Verificar si el servidor está corriendo

```powershell
# Ver procesos de Python en el puerto 8000
netstat -ano | findstr :8000
```

### Detener servidor forzadamente (si no responde)

```powershell
# Encontrar el proceso
netstat -ano | findstr :8000
# Nota el PID (última columna)

# Matar el proceso (reemplaza PID con el número)
taskkill /PID <PID> /F
```

---

## 🚀 SERVIDOR DE PRODUCCIÓN (VPS - Debian/Linux)

### Método 1: Usar el script de reinicio (Recomendado)

```bash
cd /var/www/predicta.com.co
./reiniciar_servicio.sh
```

### Método 2: Reiniciar manualmente con systemctl

```bash
# Reiniciar Gunicorn
sudo systemctl restart gunicorn

# Verificar estado
sudo systemctl status gunicorn

# Ver logs recientes
sudo journalctl -u gunicorn --no-pager -n 50
```

### Método 3: Reiniciar Gunicorn y Nginx

```bash
# Reiniciar ambos servicios
sudo systemctl restart gunicorn && sudo systemctl restart nginx

# Verificar ambos
sudo systemctl status gunicorn
sudo systemctl status nginx
```

### Comandos útiles para el servidor de producción

#### Ver estado del servicio:
```bash
sudo systemctl status gunicorn
```

#### Verificar si está activo:
```bash
sudo systemctl is-active gunicorn
```

#### Ver logs en tiempo real:
```bash
sudo journalctl -u gunicorn -f
```

#### Ver solo errores:
```bash
sudo journalctl -u gunicorn --no-pager -n 200 | grep -i "error\|failed\|exception"
```

#### Ver procesos de Gunicorn:
```bash
pgrep -f gunicorn
```

#### Ver puertos en uso:
```bash
sudo netstat -tlnp | grep gunicorn
# o
sudo ss -tlnp | grep gunicorn
```

#### Iniciar servicio (si está detenido):
```bash
sudo systemctl start gunicorn
```

#### Detener servicio:
```bash
sudo systemctl stop gunicorn
```

#### Habilitar inicio automático:
```bash
sudo systemctl enable gunicorn
```

#### Deshabilitar inicio automático:
```bash
sudo systemctl disable gunicorn
```

---

## 📋 Proceso Completo de Actualización en VPS

Cuando haces cambios y quieres actualizar el servidor:

```bash
# 1. Ir al directorio del proyecto
cd /var/www/predicta.com.co

# 2. Activar entorno virtual
source venv/bin/activate

# 3. Hacer pull de los cambios
git pull origin main

# 4. Instalar nuevas dependencias (si hay)
pip install -r requirements.txt

# 5. Aplicar migraciones (si hay)
python manage.py migrate

# 6. Recopilar archivos estáticos
python manage.py collectstatic --noinput

# 7. Reiniciar servicio
sudo systemctl restart gunicorn

# 8. Verificar que todo esté bien
sudo systemctl status gunicorn
```

O usar el script completo (si existe):
```bash
cd /var/www/predicta.com.co
source venv/bin/activate
git pull origin main
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
```

---

## 🔍 Diagnóstico de Problemas

### El servidor no inicia

1. **Ver logs de errores:**
```bash
sudo journalctl -u gunicorn --no-pager -n 100
```

2. **Verificar configuración:**
```bash
cd /var/www/predicta.com.co
source venv/bin/activate
python manage.py check
```

3. **Verificar que el puerto no esté en uso:**
```bash
sudo netstat -tlnp | grep :8000
```

### El servidor se cae frecuentemente

1. **Ver logs para encontrar el error:**
```bash
sudo journalctl -u gunicorn -f
```

2. **Verificar recursos del sistema:**
```bash
# Memoria
free -h

# CPU
top

# Espacio en disco
df -h
```

3. **Revisar configuración de Gunicorn:**
```bash
# Ver archivo de servicio
sudo cat /etc/systemd/system/gunicorn.service
```

---

## ⚡ Comandos Rápidos de Referencia

### Local (Windows):
```powershell
# Iniciar
venv\Scripts\Activate.ps1; python manage.py runserver

# Detener
CTRL + C
```

### Producción (VPS):
```bash
# Reiniciar
sudo systemctl restart gunicorn

# Estado
sudo systemctl status gunicorn

# Logs
sudo journalctl -u gunicorn -f
```

---

## 📝 Notas Importantes

1. **En producción**, siempre usa `systemctl` para gestionar Gunicorn, no lo ejecutes manualmente
2. **Después de cambios en código**, recuerda hacer `collectstatic` si hay cambios en archivos estáticos
3. **Después de migraciones**, reinicia el servicio para aplicar los cambios
4. **Los logs** son tu mejor amigo para diagnosticar problemas
5. **Nunca detengas** el servidor de producción sin tener un plan de respaldo

---

*Guía de reinicio de servidores - Actualizar según configuración específica*

