import pytest

def test_register_user(client):
    """Тест успешной регистрации"""
    response = client.post('/api/auth/register', json={
        'email': 'newuser@test.com',
        'password': 'securepass'
    })
    assert response.status_code == 201
    data = response.get_json()
    assert 'message' in data
    assert data['message'] == 'User created'

def test_register_duplicate_email(client, auth_header):
    """Тест регистрации с существующим email"""
    # Первый раз
    client.post('/api/auth/register', json={
        'email': 'dup@test.com',
        'password': 'pass'
    })
    # Второй раз
    response = client.post('/api/auth/register', json={
        'email': 'dup@test.com',
        'password': 'pass'
    })
    assert response.status_code == 400
    assert response.get_json()['error'] == 'Email already exists'

def test_login_success(client):
    """Тест успешного входа"""
    # Регистрируемся
    client.post('/api/auth/register', json={
        'email': 'login@test.com',
        'password': 'pass123'
    })
    # Входим
    response = client.post('/api/auth/login', json={
        'email': 'login@test.com',
        'password': 'pass123'
    })
    assert response.status_code == 200
    assert 'access_token' in response.get_json()

def test_login_invalid_password(client):
    """Тест входа с неверным паролем"""
    client.post('/api/auth/register', json={
        'email': 'fail@test.com',
        'password': 'correct'
    })
    response = client.post('/api/auth/login', json={
        'email': 'fail@test.com',
        'password': 'wrong'
    })
    assert response.status_code == 401
    assert response.get_json()['error'] == 'Invalid credentials'

def test_protected_route_without_token(client):
    """Тест доступа к защищенному эндпоинту без токена"""
    response = client.get('/api/surveys')
    assert response.status_code == 401  # Unauthorized