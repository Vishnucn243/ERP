from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import Profile

class Command(BaseCommand):
    help = 'Creates a default admin user for testing'

    def handle(self, *args, **options):
        # Check if admin user already exists
        if User.objects.filter(username='admin').exists():
            self.stdout.write(
                self.style.WARNING('Admin user already exists')
            )
            return

        # Create admin user
        user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123',
            first_name='Admin',
            last_name='User'
        )

        # Create admin profile
        Profile.objects.create(user=user, role='Admin')

        self.stdout.write(
            self.style.SUCCESS('Successfully created admin user')
        )
        self.stdout.write('Username: admin')
        self.stdout.write('Password: admin123') 