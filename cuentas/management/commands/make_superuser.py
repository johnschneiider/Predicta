"""
Comando para convertir un usuario existente en superusuario
Uso: python manage.py make_superuser <username>
"""
from django.core.management.base import BaseCommand, CommandError
from cuentas.models import Usuario


class Command(BaseCommand):
    help = 'Convierte un usuario existente en superusuario y staff'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username del usuario a convertir')

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            usuario = Usuario.objects.get(username=username)
        except Usuario.DoesNotExist:
            raise CommandError(f'Usuario "{username}" no existe en la base de datos.')
        
        # Convertir en superusuario y staff
        usuario.is_superuser = True
        usuario.is_staff = True
        usuario.save()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'[OK] Usuario "{username}" ({usuario.email}) ahora es superusuario y staff.'
            )
        )

