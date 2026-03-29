"""
Запуск:
    python seed.py

Создаваемые данные:
- 3 тестовых пользователя (автор + 2 респондента)
- 3 опроса в разных статусах (DRAFT, PUBLISHED, CLOSED)
- Вопросы всех типов (SINGLE, MULTIPLE, TEXT)
"""

from app import create_app
from app.extensions import db
from datetime import datetime, timedelta, timezone


def create_test_data(app):
    """
    Основная функция создания тестовых данных.
    """
    
    # === ВАЖНО: Импорты моделей ВНУТРИ функции ===
    # Это гарантирует, что модели импортируются ПОСЛЕ инициализации db.init_app(app)
    from app.models.user import User
    from app.models.survey import Survey, Question, Option, SurveyStatus, QuestionType
    from app.models.answer import Response, Answer
    
    print("Начинаем создание тестовых данных...")
    
    with app.app_context():
        # === ШАГ 1: ОЧИСТКА БАЗЫ ===
        # Важно: удаляем в порядке, обратном внешним ключам
        print("Очистка существующих данных...")
        db.session.query(Answer).delete()
        db.session.query(Response).delete()
        db.session.query(Option).delete()
        db.session.query(Question).delete()
        db.session.query(Survey).delete()
        db.session.query(User).delete()
        db.session.commit()
        
        # === ШАГ 2: СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ ===
        print("Создаем пользователей...")
        
        # Автор опросов (основной тестовый аккаунт)
        user1 = User(email='author@example.com')
        user1.set_password('password123')  # Пароль хешируется через bcrypt
        db.session.add(user1)
        
        # Респондент 1 (для тестирования прохождения опросов)
        user2 = User(email='respondent@example.com')
        user2.set_password('password123')
        db.session.add(user2)
        
        # Респондент 2 (для тестирования уникальности ответов)
        user3 = User(email='test@example.com')
        user3.set_password('password123')
        db.session.add(user3)
        
        db.session.commit()
        print(f"Создано {User.query.count()} пользователей")
    
        # === ШАГ 3: СОЗДАНИЕ ОПРОСОВ ===
        print("Создаем опросы...")
        
        # ── Опрос 1: Опубликованный (для прохождения) ──
        survey1 = Survey(
            title='Удовлетворенность клиентов',
            description='Пожалуйста, ответьте на несколько вопросов о нашем сервисе',
            author_id=user1.id,
            status=SurveyStatus.PUBLISHED,  # СТАТУС: доступен всем
            created_at=datetime.now(timezone.utc) - timedelta(days=7)
        )
        db.session.add(survey1)
        db.session.flush()  # Получаем ID до commit
        
        # Вопрос 1.1: Одиночный выбор (radio)
        q1_1 = Question(
            survey_id=survey1.id,
            text='Как вы оцениваете наш сервис?',
            q_type=QuestionType.SINGLE,  # ТИП: один вариант из списка
            order=1
        )
        db.session.add(q1_1)
        db.session.flush()
        
        # Варианты ответа для вопроса 1.1
        options_1_1 = [
            Option(question_id=q1_1.id, text='Отлично'),
            Option(question_id=q1_1.id, text='Хорошо'),
            Option(question_id=q1_1.id, text='Удовлетворительно'),
            Option(question_id=q1_1.id, text='Плохо'),
        ]
        db.session.add_all(options_1_1)
        
        # Вопрос 1.2: Множественный выбор (checkbox)
        q1_2 = Question(
            survey_id=survey1.id,
            text='Что вам понравилось больше всего? (можно выбрать несколько)',
            q_type=QuestionType.MULTIPLE,  # ТИП: несколько вариантов
            order=2
        )
        db.session.add(q1_2)
        db.session.flush()
        
        options_1_2 = [
            Option(question_id=q1_2.id, text='Скорость работы'),
            Option(question_id=q1_2.id, text='Качество обслуживания'),
            Option(question_id=q1_2.id, text='Цена'),
            Option(question_id=q1_2.id, text='Ассортимент'),
        ]
        db.session.add_all(options_1_2)
        
        # Вопрос 1.3: Текстовый ответ
        q1_3 = Question(
            survey_id=survey1.id,
            text='Ваши пожелания и комментарии',
            q_type=QuestionType.TEXT,  # ТИП: свободный текст
            order=3
        )
        db.session.add(q1_3)
        
        # ── Опрос 2: Черновик (редактируемый) ──
        survey2 = Survey(
            title='Опрос о новых функциях (Черновик)',
            description='Этот опрос еще не опубликован',
            author_id=user1.id,
            status=SurveyStatus.DRAFT,  # СТАТУС: виден только автору
            created_at=datetime.now(timezone.utc) - timedelta(days=2)
        )
        db.session.add(survey2)
        db.session.flush()
        
        q2_1 = Question(
            survey_id=survey2.id,
            text='Какую функцию вы хотели бы видеть?',
            q_type=QuestionType.TEXT,
            order=1
        )
        db.session.add(q2_1)
        
        # ── Опрос 3: Закрытый (архив) ──
        survey3 = Survey(
            title='Опрос о продукте (Закрыт)',
            description='Этот опрос завершен',
            author_id=user1.id,
            status=SurveyStatus.CLOSED,  # СТАТУС: нельзя проходить, только статистика
            created_at=datetime.now(timezone.utc) - timedelta(days=30)
        )
        db.session.add(survey3)
        db.session.flush()
        
        q3_1 = Question(
            survey_id=survey3.id,
            text='Вам нравится наш продукт?',
            q_type=QuestionType.SINGLE,
            order=1
        )
        db.session.add(q3_1)
        db.session.flush()
        
        options_3_1 = [
            Option(question_id=q3_1.id, text='Да'),
            Option(question_id=q3_1.id, text='Нет'),
        ]
        db.session.add_all(options_3_1)
        
        db.session.commit()
        print(f"Создано {Survey.query.count()} опросов")
        
        # === ШАГ 4: СОЗДАНИЕ ОТВЕТОВ (прохождения опросов) ===
        print("Создаем ответы респондентов...")
        
        # Прохождение опроса 1 пользователем 2
        response1 = Response(
            survey_id=survey1.id,
            user_id=user2.id,
            submitted_at=datetime.now(timezone.utc) - timedelta(days=5)
        )
        db.session.add(response1)
        db.session.flush()
        
        # Ответы на вопросы опроса 1
        db.session.add(Answer(response_id=response1.id, question_id=q1_1.id, option_id=options_1_1[0].id))  # "Отлично"
        db.session.add(Answer(response_id=response1.id, question_id=q1_2.id, option_id=options_1_2[0].id))  # "Скорость"
        db.session.add(Answer(response_id=response1.id, question_id=q1_3.id, text_value='Отличный сервис, рекомендую!'))
        
        # Прохождение опроса 1 пользователем 3
        response2 = Response(
            survey_id=survey1.id,
            user_id=user3.id,
            submitted_at=datetime.now(timezone.utc) - timedelta(days=3)
        )
        db.session.add(response2)
        db.session.flush()
        
        db.session.add(Answer(response_id=response2.id, question_id=q1_1.id, option_id=options_1_1[1].id))  # "Хорошо"
        # Множественный выбор: два ответа на один вопрос
        db.session.add(Answer(response_id=response2.id, question_id=q1_2.id, option_id=options_1_2[1].id))  # "Качество"
        db.session.add(Answer(response_id=response2.id, question_id=q1_2.id, option_id=options_1_2[2].id))  # "Цена"
        db.session.add(Answer(response_id=response2.id, question_id=q1_3.id, text_value='Все хорошо, но можно улучшить поддержку'))
        
        db.session.commit()
        print(f"Создано {Response.query.count()} прохождений опросов")
        
        # === ШАГ 5: ВЫВОД СТАТИСТИКИ ===
        print("\n ИТОГОВАЯ СТАТИСТИКА:")
        print(f"   Пользователей: {User.query.count()}")
        print(f"   Опросов: {Survey.query.count()}")
        print(f"      • Опубликованных: {Survey.query.filter_by(status=SurveyStatus.PUBLISHED).count()}")
        print(f"      • Черновиков: {Survey.query.filter_by(status=SurveyStatus.DRAFT).count()}")
        print(f"      • Закрытых: {Survey.query.filter_by(status=SurveyStatus.CLOSED).count()}")
        print(f"   Вопросов: {Question.query.count()}")
        print(f"   Вариантов ответов: {Option.query.count()}")
        print(f"   Прохождений опросов: {Response.query.count()}")
        print(f"   Ответов на вопросы: {Answer.query.count()}")
        
        # === ШАГ 6: УЧЕТНЫЕ ДАННЫЕ ДЛЯ ВХОДА ===
        print("\n ДАННЫЕ ДЛЯ ВХОДА:")
        print("      Автор (создает опросы):")
        print("      Email: author@example.com")
        print("      Password: password123")
        print("\n    Респондент 1:")
        print("      Email: respondent@example.com")
        print("      Password: password123")
        print("\n    Респондент 2:")
        print("      Email: test@example.com")
        print("      Password: password123")
        
        print("\nТестовые данные успешно созданы!")


# Точка входа для запуска скрипта напрямую: python seed.py
if __name__ == '__main__':
    app = create_app()  # Создаём приложение — здесь вызывается db.init_app(app)
    create_test_data(app)  # Передаём app в функцию — импорты моделей внутри неё уже безопасны