#  This module is for Django settings only

INSTALLED_APPS = [
    'src'
]

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': "db.sqlite3",
    }
}