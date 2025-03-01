import django
import os

# initialize django (sqlite ORM only)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

def run():
    # start app here
    pass

run()
