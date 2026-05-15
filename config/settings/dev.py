from .base import *  # noqa: F401,F403


DEBUG = env("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "0.0.0.0"])

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
