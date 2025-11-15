"""
Comando para resetear la contraseña de un usuario
Uso: python manage.py reset_user_password <username>
"""
from django.core.management.base import BaseCommand, CommandError
from cuentas.models import Usuario
import getpass


class Command(BaseCommand):
    help = 'Resetea la contraseña de un usuario existente'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username del usuario')
        parser.add_argument(
            '--password',
            type=str,
            help='Nueva contraseña (si no se proporciona, se pedirá interactivamente)',
        )

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            usuario = Usuario.objects.get(username=username)
        except Usuario.DoesNotExist:
            raise CommandError(f'Usuario "{username}" no existe en la base de datos.')
        
        # Obtener contraseña
        if options['password']:
            password = options['password']
        else:
            password = getpass.getpass('Nueva contraseña: ')
            password_confirm = getpass.getpass('Confirmar contraseña: ')
            
            if password != password_confirm:
                raise CommandError('Las contraseñas no coinciden.')
            
            if len(password) < 8:
                self.stdout.write(
                    self.style.WARNING(
                        '⚠ Advertencia: La contraseña tiene menos de 8 caracteres.'
                    )
                )
                confirm = input('¿Continuar de todas formas? (s/N): ')
                if confirm.lower() != 's':
                    raise CommandError('Operación cancelada.')
        
        # Establecer nueva contraseña
        usuario.set_password(password)
        usuario.save()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Contraseña actualizada para el usuario "{username}" ({usuario.email}).'
            )
        )

