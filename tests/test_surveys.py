import pytest
from app.models.survey import SurveyStatus

def test_create_survey_draft(client, auth_header):
    response = client.post('/api/surveys', json={
        'title': 'Test Draft Survey',
        'description': 'Test description'
    }, headers=auth_header)
    
    # === ОТЛАДКА: выводим ответ ===
    print(f"\nSTATUS: {response.status_code}")
    print(f"RESPONSE: {response.get_json()}")
    # ==============================
    
    assert response.status_code == 201
    assert response.get_json()['title'] == 'Test Draft Survey'
    assert response.get_json()['status'] == 'draft'
    
def test_publish_survey(client, auth_header):
    """Публикация опроса с вопросом"""
    
    # 1. Создаём опрос
    create_resp = client.post('/api/surveys', json={
        'title': 'Test Publish Survey',
        'description': 'Test',
        'status': 'draft'
    }, headers=auth_header)
    
    assert create_resp.status_code == 201
    survey_id = create_resp.get_json()['id']
    print(f"Created survey ID: {survey_id}")
    
    # 2. ДОБАВЛЯЕМ ВОПРОС (обязательно для публикации!)
    question_resp = client.post(f'/api/surveys/{survey_id}/questions', json={
        'text': 'How satisfied are you?',
        'type': 'single',  # 'single', 'multiple', или 'text'
        'options': ['Very', 'Somewhat', 'Not at all'],  # Обязательно для single/multiple
        'order': 1
    }, headers=auth_header)
    
    # Отладка если вопрос не создался
    if question_resp.status_code != 201:
        print(f"Question creation failed: {question_resp.get_json()}")
        pytest.fail("Не удалось добавить вопрос для теста публикации")
    
    print(f" Added question ID: {question_resp.get_json()['id']}")
    
    # 3. Теперь публикуем (теперь опрос имеет вопросы)
    pub_resp = client.post(f'/api/surveys/{survey_id}/publish', headers=auth_header)
    
    print(f"\n PUBLISH STATUS: {pub_resp.status_code}")
    print(f"PUBLISH RESPONSE: {pub_resp.get_json()}")
    
    # 4. Проверяем результат
    assert pub_resp.status_code == 200
    assert pub_resp.get_json()['survey']['status'] == 'published'

def test_cannot_edit_published_survey(client, auth_header):
    """Запрет на редактирование опубликованного опроса"""
    # Создаем и публикуем
    create_resp = client.post('/api/surveys', json={'title': 'Locked'}, headers=auth_header)
    survey_id = create_resp.get_json()['id']
    client.post(f'/api/surveys/{survey_id}/questions', json={'text': 'Q', 'type': 'text'}, headers=auth_header)
    client.post(f'/api/surveys/{survey_id}/publish', headers=auth_header)
    
    # Пытаемся изменить
    response = client.put(f'/api/surveys/{survey_id}', json={'title': 'Hacked'}, headers=auth_header)
    assert response.status_code == 400
    assert 'Cannot edit published' in response.get_json()['error']

def test_submit_response(client, auth_header):
    """Прохождение опроса пользователем"""
    # Подготовка опроса
    create_resp = client.post('/api/surveys', json={'title': 'Active'}, headers=auth_header)
    survey_id = create_resp.get_json()['id']
    client.post(f'/api/surveys/{survey_id}/questions', json={'text': 'How are you?', 'type': 'text'}, headers=auth_header)
    client.post(f'/api/surveys/{survey_id}/publish', headers=auth_header)
    
    # Отправка ответа
    submit_resp = client.post(f'/api/surveys/{survey_id}/submit', json={
        'answers': [
            {'question_id': 1, 'value': 'Good'}
        ]
    }, headers=auth_header)
    
    assert submit_resp.status_code == 201

def test_duplicate_response_forbidden(client, auth_header):
    """Запрет на повторное прохождение опроса"""
    # Создаем и публикуем
    create_resp = client.post('/api/surveys', json={'title': 'OneTime'}, headers=auth_header)
    survey_id = create_resp.get_json()['id']
    client.post(f'/api/surveys/{survey_id}/questions', json={'text': 'Q', 'type': 'text'}, headers=auth_header)
    client.post(f'/api/surveys/{survey_id}/publish', headers=auth_header)
    
    # Первый ответ
    client.post(f'/api/surveys/{survey_id}/submit', json={'answers': [{'question_id': 1, 'value': 'A'}]}, headers=auth_header)
    
    # Второй ответ (должен упасть)
    response = client.post(f'/api/surveys/{survey_id}/submit', json={'answers': [{'question_id': 1, 'value': 'B'}]}, headers=auth_header)
    assert response.status_code == 400
    assert 'already responded' in response.get_json()['error']

def test_view_results_author_only(client, auth_header):
    """Просмотр результатов доступен только автору"""
    # Создаем опрос
    create_resp = client.post('/api/surveys', json={'title': 'Stats'}, headers=auth_header)
    survey_id = create_resp.get_json()['id']
    
    # Автор может видеть
    res = client.get(f'/api/surveys/{survey_id}/results', headers=auth_header)
    assert res.status_code == 200
    
    # Создаем другого пользователя (через прямой запрос без хелпера для чистоты)
    client.post('/api/auth/register', json={'email': 'other@test.com', 'password': 'pass'})
    other_login = client.post('/api/auth/login', json={'email': 'other@test.com', 'password': 'pass'})
    other_token = other_login.get_json()['access_token']
    other_header = {'Authorization': f'Bearer {other_token}'}
    
    # Чужак не может видеть
    res_forbidden = client.get(f'/api/surveys/{survey_id}/results', headers=other_header)
    assert res_forbidden.status_code == 403