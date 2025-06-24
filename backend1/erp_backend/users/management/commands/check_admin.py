from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import Profile

class Command(BaseCommand):
    help = 'Check admin user and profile'

    def handle(self, *args, **options):
        try:
            admin_user = User.objects.get(username='admin')
            self.stdout.write(f'Admin user found: {admin_user.username}')
            self.stdout.write(f'Email: {admin_user.email}')
            self.stdout.write(f'Is active: {admin_user.is_active}')
            
            try:
                profile = admin_user.profile
                self.stdout.write(f'Profile role: {profile.role}')
                self.stdout.write(self.style.SUCCESS('Admin user and profile are properly configured'))
            except Profile.DoesNotExist:
                self.stdout.write(self.style.ERROR('Admin user exists but has no profile!'))
                
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Admin user does not exist!'))
            self.stdout.write('Run: python manage.py create_admin') 