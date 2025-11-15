"""
Middleware personalizado para manejar la autenticación
"""

from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from django.conf import settings


class AuthenticationMiddleware:
    """
    Middleware que verifica la autenticación y redirige al login
    con mensaje informativo si es necesario.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # URLs que no requieren autenticación
        self.exempt_urls = [
            '/',  # Landing page
            '/cuentas/login/',
            '/cuentas/logout/',
            '/admin/',
            '/static/',
            '/media/',
        ]
    
    def __call__(self, request):
        # Verificar si la URL actual requiere autenticación
        if self.requires_authentication(request):
            if not request.user.is_authenticated:
                # Agregar mensaje informativo
                messages.info(request, 'Debes iniciar sesión para acceder a esta página.')
                return redirect('cuentas:login')
        
        response = self.get_response(request)
        return response
    
    def requires_authentication(self, request):
        """
        Determina si la URL actual requiere autenticación
        """
        path = request.path
        
        # No requerir autenticación para URLs exentas
        for exempt_url in self.exempt_urls:
            if path.startswith(exempt_url):
                return False
        
        # No requerir autenticación para el admin de Django
        if path.startswith('/admin/'):
            return False
        
        # Requerir autenticación para todas las demás URLs
        return True



