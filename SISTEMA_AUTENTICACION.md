# Sistema de Autenticación - Predicta

## 🔐 Descripción General

El sistema de autenticación de Predicta está diseñado para ser completamente controlado por administradores. Solo los superusuarios pueden crear, editar y gestionar usuarios del sistema.

## 🚫 Características de Seguridad

### **Acceso Restringido**
- ✅ **Solo administradores pueden crear usuarios**
- ✅ **No hay registro público disponible**
- ✅ **Todas las páginas requieren autenticación**
- ✅ **Redirección automática al login si no estás autenticado**

### **Protección Implementada**

#### **1. Decoradores de Vista**
Todas las vistas del proyecto están protegidas con `@method_decorator(login_required, name='dispatch')`:

```python
@method_decorator(login_required, name='dispatch')
class MiVista(View):
    def get(self, request):
        # Solo usuarios autenticados pueden acceder
        pass
```

#### **2. Middleware de Autenticación**
Se implementó un middleware personalizado que:
- Verifica la autenticación en cada request
- Redirige automáticamente al login si no estás autenticado
- Muestra mensajes informativos al usuario
- Excluye URLs que no requieren autenticación (login, admin, static, media)

#### **3. URLs Exentas de Autenticación**
- `/cuentas/login/` - Página de login
- `/cuentas/logout/` - Cerrar sesión
- `/admin/` - Panel de administración de Django
- `/static/` - Archivos estáticos
- `/media/` - Archivos de media

## 👥 Gestión de Usuarios

### **Panel de Administración**
Solo los superusuarios pueden acceder a:
- **URL**: `/cuentas/admin/usuarios/`
- **Funcionalidades**:
  - Crear nuevos usuarios con contraseñas asignadas
  - Editar información de usuarios existentes
  - Cambiar contraseñas de usuarios
  - Activar/desactivar usuarios
  - Eliminar usuarios
  - Buscar usuarios por nombre, apellido o email

### **Crear Usuarios**
1. Inicia sesión como superusuario
2. Ve al dashboard y haz clic en "Panel de Usuarios"
3. Haz clic en "Crear Nuevo Usuario"
4. Completa los datos del usuario
5. Asigna una contraseña
6. El usuario puede hacer login inmediatamente

## 🔧 Configuración Técnica

### **Archivos Modificados**

#### **Decoradores Aplicados:**
- `ai_predictions/views.py` - 11 clases de vista
- `odds/views.py` - 7 clases de vista  
- `football_data/views.py` - 12 clases de vista
- `cuentas/views.py` - VistaDashboard

#### **Middleware:**
- `betting_bot/middleware.py` - Middleware personalizado
- `betting_bot/settings.py` - Configuración del middleware

#### **Templates:**
- `templates/403.html` - Página de error personalizada
- `cuentas/templates/cuentas/login.html` - Actualizado sin registro público

## 🚀 Cómo Usar

### **Para Administradores:**
1. Inicia sesión con tu cuenta de superusuario
2. Accede al "Panel de Administración" en el dashboard
3. Gestiona usuarios desde "Panel de Usuarios"

### **Para Usuarios:**
1. Ve a `/cuentas/login/`
2. Usa las credenciales proporcionadas por el administrador
3. Accede a todas las funcionalidades del sistema

## ⚠️ Notas Importantes

- **No hay registro público**: Solo los administradores pueden crear cuentas
- **Todas las páginas están protegidas**: Excepto login, logout, admin y archivos estáticos
- **Redirección automática**: Si intentas acceder sin autenticación, serás redirigido al login
- **Mensajes informativos**: El sistema te informa cuando necesitas autenticarte

## 🔒 Seguridad Adicional

El sistema incluye:
- Validación de formularios
- Protección CSRF
- Decoradores de seguridad en todas las vistas
- Middleware de autenticación personalizado
- Confirmación antes de eliminar usuarios
- Búsqueda y filtrado seguro de usuarios















