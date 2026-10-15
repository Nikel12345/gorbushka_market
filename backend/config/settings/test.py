from .dev import *  # noqa: F401,F403

# Быстрый хешер: в тестах стойкость не нужна, а PBKDF2 замедляет их в разы
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
