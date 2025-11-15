#!/bin/bash

# Script rápido para reiniciar el servicio Gunicorn cuando se desconecta el puerto
# Uso: ./reiniciar_servicio.sh

echo "Reiniciando servicio Gunicorn..."

# Reiniciar Gunicorn
sudo systemctl restart gunicorn

# Esperar un momento
sleep 2

# Verificar estado
if systemctl is-active --quiet gunicorn; then
    echo "✓ Servicio Gunicorn reiniciado correctamente"
    echo ""
    echo "Estado del servicio:"
    systemctl status gunicorn --no-pager -l | head -15
else
    echo "✗ Error: El servicio no se pudo iniciar"
    echo ""
    echo "Revisa los logs con:"
    echo "  journalctl -u gunicorn --no-pager -n 50"
fi

echo ""
echo "Para ver logs en tiempo real:"
echo "  journalctl -u gunicorn -f"


