"""
Comando para listar todos los usuarios en la base de datos
Uso: python manage.py list_users
"""
from django.core.management.base import BaseCommand
from cuentas.models import Usuario


class Command(BaseCommand):
    help = 'Lista todos los usuarios en la base de datos'

    def handle(self, *args, **options):
        usuarios = Usuario.objects.all().order_by('username')
        
        if not usuarios.exists():
            self.stdout.write(self.style.WARNING('No hay usuarios en la base de datos.'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'\nTotal de usuarios: {usuarios.count()}\n'))
        self.stdout.write('-' * 80)
        self.stdout.write(f'{"Username":<20} {"Email":<30} {"Superuser":<10} {"Staff":<10} {"Active":<10}')
        self.stdout.write('-' * 80)
        
        for usuario in usuarios:
            superuser = 'SI' if usuario.is_superuser else 'NO'
            staff = 'SI' if usuario.is_staff else 'NO'
            active = 'SI' if usuario.is_active else 'NO'
            
            self.stdout.write(
                f'{usuario.username:<20} {usuario.email:<30} {superuser:<10} {staff:<10} {active:<10}'
            )
        
        self.stdout.write('-' * 80)
        self.stdout.write('\n')

