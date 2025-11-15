#!/bin/bash

# Script de diagnóstico y solución para problemas de puerto en VPS
# Uso: ./diagnostico_vps.sh

echo "=========================================="
echo "Diagnóstico de Gunicorn en VPS"
echo "=========================================="
echo ""

# 1. Verificar estado del servicio
echo "1. Estado del servicio Gunicorn:"
echo "-----------------------------------"
systemctl status gunicorn --no-pager -l
echo ""

# 2. Verificar si el servicio está activo
echo "2. ¿Está activo el servicio?"
echo "-----------------------------------"
if systemctl is-active --quiet gunicorn; then
    echo "✓ Servicio GUNICORN está ACTIVO"
else
    echo "✗ Servicio GUNICORN está INACTIVO"
    echo ""
    echo "Intentando iniciar el servicio..."
    sudo systemctl start gunicorn
    sleep 2
    if systemctl is-active --quiet gunicorn; then
        echo "✓ Servicio iniciado correctamente"
    else
        echo "✗ Error al iniciar el servicio"
    fi
fi
echo ""

# 3. Verificar qué puertos están escuchando
echo "3. Puertos en uso por Gunicorn:"
echo "-----------------------------------"
GUNICORN_PIDS=$(pgrep -f gunicorn)
if [ -z "$GUNICORN_PIDS" ]; then
    echo "✗ No se encontraron procesos de Gunicorn ejecutándose"
else
    echo "Procesos Gunicorn encontrados: $GUNICORN_PIDS"
    echo ""
    echo "Puertos en uso:"
    for PID in $GUNICORN_PIDS; do
        echo "  PID $PID:"
        netstat -tlnp 2>/dev/null | grep "$PID" || ss -tlnp 2>/dev/null | grep "$PID"
    done
    echo ""
    echo "Todos los puertos en uso por procesos Python:"
    netstat -tlnp 2>/dev/null | grep python || ss -tlnp 2>/dev/null | grep python
fi
echo ""

# 4. Verificar logs recientes
echo "4. Logs recientes de Gunicorn (últimas 50 líneas):"
echo "-----------------------------------"
journalctl -u gunicorn --no-pager -n 50
echo ""

# 5. Verificar si hay errores en los logs
echo "5. Buscando errores en los logs:"
echo "-----------------------------------"
ERRORS=$(journalctl -u gunicorn --no-pager -n 200 | grep -i "error\|failed\|exception" | tail -10)
if [ -z "$ERRORS" ]; then
    echo "✓ No se encontraron errores recientes"
else
    echo "✗ Errores encontrados:"
    echo "$ERRORS"
fi
echo ""

# 6. Verificar configuración del servicio
echo "6. Información del servicio systemd:"
echo "-----------------------------------"
if [ -f "/etc/systemd/system/gunicorn.service" ]; then
    echo "Archivo de servicio encontrado:"
    cat /etc/systemd/system/gunicorn.service
elif [ -f "/etc/systemd/system/gunicorn.socket" ]; then
    echo "Socket encontrado:"
    cat /etc/systemd/system/gunicorn.socket
else
    echo "⚠ No se encontró archivo de configuración en /etc/systemd/system/"
    echo "Buscando en otros lugares..."
    find /etc/systemd -name "*gunicorn*" 2>/dev/null
fi
echo ""

# 7. Verificar Nginx (si está instalado)
echo "7. Estado de Nginx (proxy inverso):"
echo "-----------------------------------"
if command -v nginx &> /dev/null; then
    if systemctl is-active --quiet nginx; then
        echo "✓ Nginx está ACTIVO"
        echo ""
        echo "Configuración de Nginx relacionada con el proyecto:"
        grep -r "predicta\|gunicorn\|127.0.0.1" /etc/nginx/sites-enabled/ 2>/dev/null || echo "No se encontró configuración específica"
    else
        echo "✗ Nginx está INACTIVO"
        echo "Intentando iniciar Nginx..."
        sudo systemctl start nginx
    fi
else
    echo "Nginx no está instalado"
fi
echo ""

# 8. Recomendaciones
echo "=========================================="
echo "RECOMENDACIONES:"
echo "=========================================="
echo ""

if ! systemctl is-active --quiet gunicorn; then
    echo "→ El servicio Gunicorn no está corriendo. Ejecuta:"
    echo "  sudo systemctl start gunicorn"
    echo "  sudo systemctl enable gunicorn  # Para que inicie automáticamente"
    echo ""
fi

echo "→ Si el servicio está activo pero no responde, intenta reiniciarlo:"
echo "  sudo systemctl restart gunicorn"
echo ""

echo "→ Para ver los logs en tiempo real:"
echo "  sudo journalctl -u gunicorn -f"
echo ""

echo "→ Para verificar qué proceso está usando un puerto específico:"
echo "  sudo netstat -tlnp | grep :PUERTO"
echo "  o"
echo "  sudo ss -tlnp | grep :PUERTO"
echo ""

echo "→ Si necesitas verificar la configuración de Gunicorn:"
echo "  cd /var/www/predicta.com.co"
echo "  source venv/bin/activate"
echo "  gunicorn --check-config betting_bot.wsgi:application"
echo ""

echo "=========================================="
echo "Diagnóstico completado"
echo "=========================================="


