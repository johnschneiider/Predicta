# 📊 Informe del Estado del Proyecto Predicta

**Fecha de revisión:** $(date)  
**Ubicación del servidor:** `/var/www/predicta.com.co/`  
**Ubicación local:** `E:\Predicta\`

---

## 🔍 Resumen Ejecutivo

El proyecto **Predicta** es un sistema Django de predicción de fútbol con IA que está desplegado en producción pero presenta varios problemas de configuración que requieren atención inmediata.

---

## ⚠️ PROBLEMAS CRÍTICOS IDENTIFICADOS

### 1. **Entorno Virtual Incorrecto** 🔴
**Problema:** Intentaste activar el entorno virtual desde una ruta que no existe:
```bash
source /var/www/predicta.com.co/app/.venv/bin/activate
# Error: No such file or directory
```

**Solución:**
- El entorno virtual está en: `/var/www/predicta.com.co/venv/` (no en `app/.venv/`)
- Para activarlo en Linux, usa:
```bash
cd /var/www/predicta.com.co
source venv/bin/activate
```

### 2. **Configuración de Producción Insegura** 🔴
**Problema:** El archivo `settings.py` tiene configuración de desarrollo activa:

```python
DEBUG = True  # ⚠️ PELIGROSO en producción
ALLOWED_HOSTS = ['localhost', '127.0.0.1']  # ⚠️ No incluye el dominio real
SECRET_KEY = 'django-insecure-...'  # ⚠️ Clave expuesta en el código
```

**Riesgos:**
- Exposición de información sensible en errores
- Vulnerabilidades de seguridad
- El sitio no funcionará con el dominio real `predicta.com.co`

### 3. **Archivo de Variables de Entorno Faltante** 🟡
**Problema:** No existe un archivo `.env` con las variables de entorno necesarias.

**Solución:** Crear un archivo `.env` basado en `env_example.txt` con valores reales.

### 4. **Configuración de Gunicorn No Encontrada** 🟡
**Problema:** Se menciona `gunicorn_config.py` en el directorio pero no existe en el repositorio.

**Estado:** El servicio Gunicorn está configurado como servicio systemd (según los scripts), pero falta el archivo de configuración.

---

## ✅ ASPECTOS POSITIVOS

1. **Estructura del Proyecto:** Bien organizada con múltiples apps Django
2. **Backups de Base de Datos:** Múltiples backups encontrados (buena práctica)
3. **Scripts de Diagnóstico:** Scripts útiles para diagnóstico y reinicio del servicio
4. **Logging:** Sistema de logging configurado correctamente
5. **Dependencias:** `requirements.txt` completo y actualizado

---

## 📁 ESTRUCTURA DEL PROYECTO

### Aplicaciones Django Instaladas:
- ✅ `cuentas` - Sistema de usuarios
- ✅ `odds` - Gestión de cuotas
- ✅ `betfair` - Integración con Betfair API
- ✅ `betting` - Sistema de apuestas
- ✅ `football_data` - Datos de fútbol
- ✅ `ai_predictions` - Predicciones con IA
- ✅ `basketball_data` - Datos de baloncesto (presente pero no en INSTALLED_APPS)

### Archivos Importantes:
- ✅ `manage.py` - Configurado correctamente
- ✅ `requirements.txt` - Dependencias definidas
- ✅ `gunicorn` - Incluido en requirements (v21.2.0)
- ✅ Scripts de diagnóstico y reinicio
- ✅ Múltiples backups de `db.sqlite3`

---

## 🔧 CONFIGURACIÓN ACTUAL

### Base de Datos:
- **Tipo:** SQLite (`db.sqlite3`)
- **Backups encontrados:**
  - `db.sqlite3.backup_20251009_015209`
  - `db.sqlite3.backup_20251011_130739`
  - `db.sqlite3.backup_20251011_144544`
  - `db.sqlite3.local_backup`

### Servidor:
- **WSGI:** Configurado en `betting_bot/wsgi.py`
- **Gunicorn:** Servicio systemd configurado
- **Static Files:** Configurado en `staticfiles/`
- **Media Files:** Configurado en `media/`

### Logs:
- **Ubicación:** `logs/betting_bot.log`
- **Estado:** Activo, con registros recientes (última actividad: 2025-09-14)

---

## 🚨 ACCIONES RECOMENDADAS (PRIORIDAD)

### 🔴 URGENTE - Seguridad

1. **Crear archivo `.env` para producción:**
```bash
cd /var/www/predicta.com.co
cp env_example.txt .env
nano .env  # Editar con valores reales
```

2. **Actualizar `settings.py` para producción:**
   - Cambiar `DEBUG = False`
   - Agregar dominio real a `ALLOWED_HOSTS`
   - Usar `python-decouple` para leer variables de entorno
   - Mover `SECRET_KEY` a `.env`

3. **Configurar ALLOWED_HOSTS:**
```python
ALLOWED_HOSTS = ['predicta.com.co', 'www.predicta.com.co', 'localhost', '127.0.0.1']
```

### 🟡 IMPORTANTE - Funcionalidad

4. **Verificar y corregir ruta del entorno virtual:**
```bash
# En el servidor Linux:
cd /var/www/predicta.com.co
ls -la venv/  # Verificar que existe
source venv/bin/activate  # Activar correctamente
```

5. **Crear archivo de configuración de Gunicorn:**
   - Crear `gunicorn_config.py` con configuración adecuada
   - O verificar configuración en el servicio systemd

6. **Verificar migraciones:**
```bash
source venv/bin/activate
python manage.py migrate --check
python manage.py showmigrations
```

### 🟢 MEJORAS - Optimización

7. **Considerar migrar a PostgreSQL** (para producción)
8. **Configurar SSL/HTTPS** (si no está configurado)
9. **Revisar y optimizar configuración de Nginx**
10. **Implementar sistema de monitoreo** (según roadmap)

---

## 📋 CHECKLIST DE VERIFICACIÓN

### Configuración del Entorno
- [ ] Entorno virtual existe y está activado correctamente
- [ ] Todas las dependencias instaladas (`pip install -r requirements.txt`)
- [ ] Archivo `.env` creado y configurado
- [ ] Variables de entorno cargadas correctamente

### Configuración de Django
- [ ] `DEBUG = False` en producción
- [ ] `ALLOWED_HOSTS` incluye el dominio real
- [ ] `SECRET_KEY` en archivo `.env` (no en código)
- [ ] Base de datos configurada y migraciones aplicadas
- [ ] Archivos estáticos recopilados (`python manage.py collectstatic`)

### Servidor
- [ ] Gunicorn configurado y funcionando
- [ ] Servicio systemd activo y habilitado
- [ ] Nginx configurado como proxy reverso
- [ ] Logs funcionando correctamente
- [ ] Puertos correctamente configurados

### Seguridad
- [ ] SSL/HTTPS configurado
- [ ] Variables sensibles en `.env` (no en código)
- [ ] Permisos de archivos correctos
- [ ] Firewall configurado

---

## 🛠️ COMANDOS ÚTILES PARA EL SERVIDOR

### Activar entorno virtual:
```bash
cd /var/www/predicta.com.co
source venv/bin/activate
```

### Verificar estado del servicio:
```bash
systemctl status gunicorn
./diagnostico_vps.sh
```

### Reiniciar servicio:
```bash
./reiniciar_servicio.sh
# o manualmente:
sudo systemctl restart gunicorn
```

### Ver logs:
```bash
journalctl -u gunicorn -f
tail -f logs/betting_bot.log
```

### Aplicar migraciones:
```bash
source venv/bin/activate
python manage.py migrate
```

### Recopilar archivos estáticos:
```bash
source venv/bin/activate
python manage.py collectstatic --noinput
```

---

## 📊 ESTADO DE LAS APLICACIONES

| Aplicación | Estado | Notas |
|------------|--------|-------|
| `cuentas` | ✅ Instalada | Sistema de usuarios personalizado |
| `odds` | ✅ Instalada | Gestión de cuotas |
| `betfair` | ✅ Instalada | Integración API |
| `betting` | ✅ Instalada | Sistema de apuestas |
| `football_data` | ✅ Instalada | Datos de fútbol |
| `ai_predictions` | ✅ Instalada | Predicciones IA |
| `basketball_data` | ⚠️ Presente pero no instalada | No en INSTALLED_APPS |

---

## 🔗 REFERENCIAS

- **README.md** - Documentación principal
- **ROADMAP_IA_PREDICTIVA.md** - Roadmap del proyecto
- **env_example.txt** - Ejemplo de variables de entorno
- **requirements.txt** - Dependencias del proyecto

---

## 📝 NOTAS ADICIONALES

1. El proyecto tiene un roadmap ambicioso para implementar un sistema de IA jerárquico de 3 capas
2. Actualmente usa modelos estadísticos básicos (Poisson, Average, etc.)
3. La base de datos SQLite es adecuada para desarrollo pero se recomienda PostgreSQL para producción
4. Los logs muestran actividad reciente, lo que indica que el sistema está siendo usado

---

**Próximos pasos sugeridos:**
1. Corregir la configuración de seguridad (DEBUG, ALLOWED_HOSTS, SECRET_KEY)
2. Crear y configurar el archivo `.env`
3. Verificar que el entorno virtual se active correctamente
4. Probar el servicio en producción después de los cambios

---

*Informe generado automáticamente - Revisar y actualizar según sea necesario*

