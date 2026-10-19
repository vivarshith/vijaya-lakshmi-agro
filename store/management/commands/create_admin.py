
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create an admin account using environment variables."

    def handle(self, *args, **options):
        username = os.environ.get("ADMIN_USERNAME")
        email = os.environ.get("ADMIN_EMAIL")
        password = os.environ.get("ADMIN_PASSWORD")

        if not all((username, email, password)):
            raise CommandError(
                "Set ADMIN_USERNAME, ADMIN_EMAIL, and ADMIN_PASSWORD "
                "in the service environment first."
            )

        User = get_user_model()

        if User.objects.filter(username=username).exists():
            self.stdout.write("That username already exists.")
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(self.style.SUCCESS("Admin account created."))
