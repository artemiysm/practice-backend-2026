import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.survey import Survey

@pytest.fixture(scope='function')
def app():
    """Создание приложения для тестов с PostgreSQL"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:qweryt123@localhost:5432/survey_db'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['JWT_SECRET_KEY'] = 'testing-secret'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()  # Очищаем после каждого теста

@pytest.fixture
def client(app):
    """Тестовый клиент"""
    return app.test_client()

@pytest.fixture
def auth_token(client):
    """Хелпер для получения токена авторизации"""
    
    # Регистрируем пользователя
    register_resp = client.post('/api/auth/register', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    # Логинимся
    login_resp = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    # Отладка: если логин не удался
    if login_resp.status_code != 200:
        print(f"\nLOGIN FAILED: {login_resp.get_json()}")
        pytest.fail(f"Не удалось получить токен: {login_resp.get_json()}")
    
    data = login_resp.get_json()
    
    # Поддержка разных форматов ответа
    token = data.get('access_token') or data.get('token')
    
    if not token:
        print(f"\nNO TOKEN IN RESPONSE: {data}")
        pytest.fail("Ответ не содержит access_token или token")
    
    return token

@pytest.fixture
def auth_header(auth_token):
    """Заголовки с токеном"""
    return {'Authorization': f'Bearer {auth_token}'}