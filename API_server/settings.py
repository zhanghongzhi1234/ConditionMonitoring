"""
Django settings for API_server project.

Generated by 'django-admin startproject' using Django 2.2.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'l%)_8^uq#@ta&bcfyp563zta!6tq0ao9swd6x^uc0!^rmx)15x'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
	'formatters': {
		'verbose': {
			'format':'{levelname} {asctime} {process:d} {thread:d} {message}',
			'style': '{',
			},
		'simple': {
			'format':'{levelname} {message}',
			'style': '{',
			},
        },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
       'file': {
           'level': 'ERROR',
           'class': 'logging.FileHandler',
           'filename': '/u01/transactive/cm/backend_service/logs/error.log',
		'formatter': 'verbose'
       },
    },
    'loggers': {
        'django': {
            'handlers': ['console','file'],
            'level': 'ERROR',
			'propagate': True,
        },
    },
}

REST_FRAMEWORK = {
	'DEFAULT_RENDERER_CLASSES': [
		'rest_framework.renderers.JSONRenderer'
	]
}

# DO NOT APPEND SLASH AT THE END
APPEND_SLASH = False

#ALLOWED_HOSTS = ['2.80.83.3']
ALLOWED_HOSTS = ['*']

#SECURE_SSL_REDIRECT = True

# To prevent "django.core.exceptions.ImproperlyConfigured: settings.DATABASES is improperly configured." error during test
# Doesnt work for django 2.2
#TEST_RUNNER = 'testing.DatabaselessTestRunner'

# Application definition



INSTALLED_APPS = [
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'backend'
]
 
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'corsheaders.middleware.CorsPostCsrfMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.common.CommonMiddleware'
]

#CORS_ORIGIN_WHITELIST=('10.1.44.69:8000','10.1.44.52:8000')
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = (
	'accept',
	'x-requested-with',
	'content-type',
	'origin'
)
CORS_ALLOW_METHODS = (
	'DELETE',
	'GET',
	'OPTIONS',
	'PATCH',
	'POST',
	'PUT'
)

ROOT_URLCONF = 'API_server.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'API_server.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases


DATABASES = {}


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Singapore'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
