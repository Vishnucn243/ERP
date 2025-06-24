from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import Profile

class Command(BaseCommand):
    help = 'Ensure every user has a Profile. Creates missing profiles with default role Employee.'

    def handle(self, *args, **options):
        users = User.objects.all()
        created = 0
        fixed = 0
        for user in users:
            try:
                profile = user.profile
                # Optionally, fix admin role if needed
                if user.username in ['admin', 'admin11'] and profile.role != 'Admin':
                    profile.role = 'Admin'
                    profile.save()
                    self.stdout.write(self.style.SUCCESS(f'Fixed role for {user.username} to Admin'))
                    fixed += 1
            except Profile.DoesNotExist:
                # Set role to Admin for known admin usernames, else Employee
                role = 'Admin' if user.username in ['admin', 'admin11'] else 'Employee'
                Profile.objects.create(user=user, role=role)
                self.stdout.write(self.style.SUCCESS(f'Created profile for {user.username} with role {role}'))
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Profiles created: {created}, roles fixed: {fixed}')) 