# 🔧 Solución de Problemas en VPS

## Problema 1: Error al crear superusuario - Usuario ya existe

### Error:
```
sqlite3.IntegrityError: UNIQUE constraint failed: usuarios.username
```

### Solución 1: Verificar usuarios existentes

En la VPS, ejecuta:

```bash
cd /var/www/predicta.com.co
source venv/bin/activate
python manage.py shell
```

Luego en el shell de Django:

```python
from cuentas.models import Usuario

# Ver todos los usuarios
usuarios = Usuario.objects.all()
for u in usuarios:
    print(f"Username: {u.username}, Email: {u.email}, Superuser: {u.is_superuser}, Staff: {u.is_staff}")

# Salir del shell
exit()
```

### Solución 2: Convertir usuario existente en superusuario

Si el usuario "admin" ya existe pero no es superusuario:

```bash
python manage.py shell
```

```python
from cuentas.models import Usuario

# Obtener el usuario admin
usuario = Usuario.objects.get(username='admin')

# Convertirlo en superusuario y staff
usuario.is_superuser = True
usuario.is_staff = True
usuario.save()

print(f"Usuario {usuario.username} ahora es superusuario")
exit()
```

### Solución 3: Cambiar contraseña del usuario existente

Si el usuario existe pero no recuerdas la contraseña:

```bash
python manage.py changepassword admin
```

### Solución 4: Crear superusuario con otro username

Si prefieres crear un nuevo superusuario con otro nombre:

```bash
python manage.py createsuperuser
```

Y usar un username diferente, por ejemplo:
- Username: `administrator`
- Username: `admin_predicta`
- Username: `root_admin`

---

## Problema 2: Git Push - Autenticación fallida

### Error:
```
remote: Invalid username or token. Password authentication is not supported for Git operations.
fatal: Authentication failed
```

### Solución: Usar Personal Access Token (PAT)

GitHub ya no acepta contraseñas para Git. Necesitas un **Personal Access Token**.

#### Paso 1: Crear un Personal Access Token en GitHub

1. Ve a GitHub.com → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. O directamente: https://github.com/settings/tokens
3. Click en "Generate new token" → "Generate new token (classic)"
4. Configura:
   - **Note**: "Predicta VPS" (o el nombre que prefieras)
   - **Expiration**: Elige una duración (90 días, 1 año, etc.)
   - **Scopes**: Marca al menos `repo` (para acceso completo a repositorios)
5. Click en "Generate token"
6. **⚠️ IMPORTANTE**: Copia el token inmediatamente (solo se muestra una vez)

#### Paso 2: Configurar Git para usar el token

**Opción A: Usar el token directamente en el push (temporal)**

```bash
# En lugar de tu contraseña, usa el token cuando te lo pida
git push origin main
# Username: johnschneiider
# Password: [pega aquí tu token, NO tu contraseña]
```

**Opción B: Guardar el token en la URL del remoto (más seguro)**

```bash
# Configurar el remoto con el token
git remote set-url origin https://johnschneiider:TU_TOKEN_AQUI@github.com/johnschneiider/Predicta.git

# Ahora puedes hacer push sin autenticarte cada vez
git push origin main
```

**⚠️ NOTA**: Si guardas el token en la URL, cualquier persona con acceso al servidor puede verlo. Considera usar SSH en su lugar.

#### Opción C: Usar SSH (Recomendado para producción)

1. **Generar clave SSH en la VPS** (si no tienes una):

```bash
ssh-keygen -t ed25519 -C "predicta-vps@predicta.com.co"
# Presiona Enter para usar la ubicación por defecto
# Opcional: agrega una passphrase para mayor seguridad
```

2. **Ver la clave pública**:

```bash
cat ~/.ssh/id_ed25519.pub
```

3. **Agregar la clave SSH a GitHub**:
   - Copia el contenido de `~/.ssh/id_ed25519.pub`
   - Ve a GitHub.com → Settings → SSH and GPG keys
   - Click en "New SSH key"
   - Pega la clave y guarda

4. **Cambiar el remoto a SSH**:

```bash
git remote set-url origin git@github.com:johnschneiider/Predicta.git
```

5. **Probar la conexión**:

```bash
ssh -T git@github.com
# Debería decir: "Hi johnschneiider! You've successfully authenticated..."
```

6. **Hacer push**:

```bash
git push origin main
```

---

## Comandos Rápidos para la VPS

### Verificar usuarios en la base de datos (NUEVO - Comando personalizado):
```bash
cd /var/www/predicta.com.co
source venv/bin/activate
python manage.py list_users
```

### Convertir usuario en superusuario (NUEVO - Comando personalizado):
```bash
python manage.py make_superuser admin
```

### Cambiar contraseña de usuario (NUEVO - Comando personalizado):
```bash
python manage.py reset_user_password admin
# O con contraseña directa:
python manage.py reset_user_password admin --password "tu_contraseña_segura"
```

### Cambiar contraseña (método tradicional de Django):
```bash
python manage.py changepassword admin
```

### Métodos alternativos (usando shell de Django):
```bash
# Verificar usuarios
python manage.py shell -c "from cuentas.models import Usuario; [print(f'{u.username} - {u.email} - Superuser: {u.is_superuser}') for u in Usuario.objects.all()]"

# Convertir usuario en superusuario
python manage.py shell -c "from cuentas.models import Usuario; u = Usuario.objects.get(username='admin'); u.is_superuser = True; u.is_staff = True; u.save(); print('Usuario convertido a superusuario')"
```

### Verificar configuración de Git:
```bash
git remote -v
```

### Configurar Git con token (temporal):
```bash
git remote set-url origin https://johnschneiider:TU_TOKEN@github.com/johnschneiider/Predicta.git
```

---

## Recomendaciones de Seguridad

1. **Para Git**: Usa SSH en lugar de tokens en URLs
2. **Para tokens**: Si usas tokens, configúralos con expiración
3. **Para usuarios**: No uses "admin" como username en producción
4. **Para contraseñas**: Usa contraseñas fuertes (mínimo 12 caracteres, mezcla de mayúsculas, minúsculas, números y símbolos)

---

*Documento de solución de problemas - Actualizar según sea necesario*

