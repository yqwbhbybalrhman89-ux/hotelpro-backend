import os
from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hotelsmart.settings")

application = get_wsgi_application()

# Applique automatiquement les tables dans la base Vercel
try:
    call_command("migrate")
except Exception as e:
    print(f"Migration error: {e}")