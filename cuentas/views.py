from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
# from django.contrib.auth.decorators import login_required  # Temporalmente deshabilitado
from django.contrib import messages
from django.views import View
from django.utils.decorators import method_decorator
from django.http import JsonResponse

from .forms import FormularioLogin, FormularioRegistro

class VistaLogin(View):
    """
    Vista para el login de usuarios
    """
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('cuentas:dashboard')
        
        form = FormularioLogin()
        return render(request, 'cuentas/login.html', {'form': form})
    
    def post(self, request):
        form = FormularioLogin(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'¡Bienvenido, {user.get_full_name()}!')
            return redirect('cuentas:dashboard')
        else:
            messages.error(request, 'Credenciales inválidas. Intenta de nuevo.')
        
        return render(request, 'cuentas/login.html', {'form': form})

class VistaRegistro(View):
    """
    Vista para el registro de usuarios
    """
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('cuentas:dashboard')
        
        form = FormularioRegistro()
        return render(request, 'cuentas/registro.html', {'form': form})
    
    def post(self, request):
        form = FormularioRegistro(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'¡Cuenta creada exitosamente! Bienvenido, {user.get_full_name()}.')
            return redirect('cuentas:dashboard')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
        
        return render(request, 'cuentas/registro.html', {'form': form})

# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
class VistaDashboard(View):
    """
    Vista del dashboard principal
    """
    def get(self, request):
        context = {
            'usuario': request.user,
        }
        return render(request, 'cuentas/dashboard.html', context)

def vista_logout(request):
    """
    Vista para cerrar sesión
    """
    logout(request)
    messages.info(request, 'Has cerrado sesión exitosamente.')
    return redirect('cuentas:login')