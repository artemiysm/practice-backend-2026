import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Конфигурация приложения"""
    # Секретный ключ для сессий и подписи куки
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key')
    # URI подключения к базе данных
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Секретный ключ для подписи JWT токенов
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key')
    # Время жизни токена (опционально)
    JWT_ACCESS_TOKEN_EXPIRES = 3600