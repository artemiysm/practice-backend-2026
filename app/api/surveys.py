from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.survey import Survey, Question, Option, SurveyStatus, QuestionType
from app.models.answer import Response, Answer
from app.extensions import db

surveys_bp = Blueprint('surveys', __name__, url_prefix='/api/surveys')


def _check_authorship(survey, current_user_id):
    """
    Хелпер для проверки авторства.
    Сравнивает author_id (int из БД) с identity из токена (str) через приведение к строке.
    """
    if current_user_id is None:
        return False
    return str(survey.author_id) == str(current_user_id)


@surveys_bp.route('', methods=['POST'])
@jwt_required()
def create_survey():
    """Создать новый опрос (черновик)"""
    data = request.get_json()
    
    if not data.get('title'):
        return jsonify({'error': 'Title is required'}), 400
    
    # get_jwt_identity() возвращает строку, но БД ждёт int для author_id
    author_id = int(get_jwt_identity())
    
    survey = Survey(
        title=data['title'],
        description=data.get('description', ''),
        author_id=author_id,
        status=SurveyStatus.DRAFT
    )
    
    db.session.add(survey)
    db.session.commit()
    
    return jsonify(survey.to_dict()), 201


@surveys_bp.route('', methods=['GET'])
@jwt_required()
def list_surveys():
    """Получить список опросов с фильтрацией, сортировкой и пагинацией"""
    current_user_id = get_jwt_identity()
    
    # === ФИЛЬТРЫ ===
    # Для запросов к БД преобразуем identity в int (SQLAlchemy обработает корректно)
    query = Survey.query.filter_by(author_id=int(current_user_id))
    
    # Фильтр по статусу
    status_filter = request.args.get('status', 'mine')
    if status_filter == 'active':
        query = query.filter_by(status=SurveyStatus.PUBLISHED)
    elif status_filter == 'completed':
        query = query.filter_by(status=SurveyStatus.CLOSED)
    
    # === СОРТИРОВКА ===
    sort_by = request.args.get('sort', 'created_desc')
    if sort_by == 'created_asc':
        query = query.order_by(Survey.created_at.asc())
    elif sort_by == 'answers_desc':
        from sqlalchemy import func
        query = query.outerjoin(Response).group_by(Survey.id)\
                     .order_by(func.count(Response.id).desc(), Survey.created_at.desc())
    else:  # created_desc (по умолчанию)
        query = query.order_by(Survey.created_at.desc())
    
    # === ПАГИНАЦИЯ ===
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    per_page = min(per_page, 50)
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Формируем ответ
    surveys_data = []
    for survey in pagination.items:
        s_dict = survey.to_dict()
        s_dict['responses_count'] = Response.query.filter_by(survey_id=survey.id).count()
        surveys_data.append(s_dict)
    
    return jsonify({
        'surveys': surveys_data,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    }), 200


@surveys_bp.route('/<int:survey_id>', methods=['GET'])
def get_survey(survey_id):
    """Получить опрос для прохождения (публичный эндпоинт)"""
    survey = Survey.query.get_or_404(survey_id)
    
    # Можно проходить только опубликованные опросы
    if survey.status != SurveyStatus.PUBLISHED:
        # Автор может видеть свой черновик
        current_user_id = get_jwt_identity(optional=True)
        #  сравнение через str()
        if current_user_id is None or str(survey.author_id) != str(current_user_id):
            return jsonify({'error': 'Survey not published'}), 403
    
    return jsonify(survey.to_dict(include_questions=True)), 200


@surveys_bp.route('/<int:survey_id>', methods=['PUT'])
@jwt_required()
def update_survey(survey_id):
    """Редактировать опрос (только черновик)"""
    current_user_id = get_jwt_identity()
    survey = Survey.query.get_or_404(survey_id)
    
    # проверка авторства через хелпер
    if not _check_authorship(survey, current_user_id):
        return jsonify({'error': 'Forbidden'}), 403
    
    # Редактировать можно только черновик
    if survey.status != SurveyStatus.DRAFT:
        return jsonify({'error': 'Cannot edit published or closed survey'}), 400
    
    data = request.get_json()
    
    if 'title' in data:
        survey.title = data['title']
    if 'description' in data:
        survey.description = data['description']
    
    db.session.commit()
    return jsonify(survey.to_dict()), 200


@surveys_bp.route('/<int:survey_id>', methods=['DELETE'])
@jwt_required()
def delete_survey(survey_id):
    """Удалить опрос (только автор, только черновик)"""
    current_user_id = get_jwt_identity()
    survey = Survey.query.get_or_404(survey_id)
    
    if not _check_authorship(survey, current_user_id):
        return jsonify({'error': 'Forbidden'}), 403
    
    if survey.status != SurveyStatus.DRAFT:
        return jsonify({'error': 'Cannot delete published survey'}), 400
    
    db.session.delete(survey)
    db.session.commit()
    return jsonify({'message': 'Survey deleted'}), 200


@surveys_bp.route('/<int:survey_id>/questions', methods=['POST'])
@jwt_required()
def add_question(survey_id):
    """Добавить вопрос к опросу"""
    current_user_id = get_jwt_identity()
    survey = Survey.query.get_or_404(survey_id)
    
    
    if not _check_authorship(survey, current_user_id) or survey.status != SurveyStatus.DRAFT:
        return jsonify({'error': 'Forbidden or survey not in draft'}), 403
    
    data = request.get_json()
    
    if not data.get('text') or not data.get('type'):
        return jsonify({'error': 'Text and type are required'}), 400
    
    q_type_str = data['type']
    
    if q_type_str not in [t.value for t in QuestionType]:
        return jsonify({'error': f'Invalid question type: {q_type_str}'}), 400
    
    if q_type_str == QuestionType.TEXT.value and data.get('options'):
        return jsonify({'error': 'Text questions cannot have options'}), 400
    
    if q_type_str in [QuestionType.SINGLE.value, QuestionType.MULTIPLE.value]:
        if not data.get('options') or not isinstance(data['options'], list) or len(data['options']) < 2:
            return jsonify({'error': 'Choice questions need at least 2 options'}), 400
    
    question = Question(
        survey_id=survey.id,
        text=data['text'],
        q_type=QuestionType(q_type_str),
        order=data.get('order', 0)
    )
    
    db.session.add(question)
    db.session.flush()
    
    if data.get('options'):
        for opt_text in data['options']:
            if opt_text:
                option = Option(question_id=question.id, text=opt_text.strip())
                db.session.add(option)
    
    db.session.commit()
    return jsonify(question.to_dict()), 201


@surveys_bp.route('/<int:survey_id>/questions/<int:question_id>', methods=['PUT'])
@jwt_required()
def update_question(survey_id, question_id):
    """Редактировать вопрос (только черновик)"""
    current_user_id = get_jwt_identity()
    survey = Survey.query.get_or_404(survey_id)
    
    if not _check_authorship(survey, current_user_id) or survey.status != SurveyStatus.DRAFT:
        return jsonify({'error': 'Forbidden or survey not in draft'}), 403
    
    question = Question.query.get_or_404(question_id)
    if question.survey_id != survey.id:
        return jsonify({'error': 'Question does not belong to this survey'}), 400
    
    data = request.get_json()
    
    if 'text' in data:
        question.text = data['text']
    if 'order' in data:
        question.order = data['order']
    
    db.session.commit()
    return jsonify(question.to_dict()), 200


@surveys_bp.route('/<int:survey_id>/questions/<int:question_id>', methods=['DELETE'])
@jwt_required()
def delete_question(survey_id, question_id):
    """Удалить вопрос (только черновик)"""
    current_user_id = get_jwt_identity()
    survey = Survey.query.get_or_404(survey_id)
    
    if not _check_authorship(survey, current_user_id) or survey.status != SurveyStatus.DRAFT:
        return jsonify({'error': 'Forbidden or survey not in draft'}), 403
    
    question = Question.query.get_or_404(question_id)
    if question.survey_id != survey.id:
        return jsonify({'error': 'Question does not belong to this survey'}), 400
    
    db.session.delete(question)
    db.session.commit()
    return jsonify({'message': 'Question deleted'}), 200


@surveys_bp.route('/<int:survey_id>/publish', methods=['POST'])
@jwt_required()
def publish_survey(survey_id):
    """Опубликовать опрос"""
    current_user_id = get_jwt_identity()
    survey = Survey.query.get_or_404(survey_id)
    
    if not _check_authorship(survey, current_user_id):
        return jsonify({'error': 'Forbidden'}), 403
    
    if survey.status != SurveyStatus.DRAFT:
        return jsonify({'error': 'Survey must be in draft to publish'}), 400
    
    if not survey.questions:
        return jsonify({'error': 'Survey must have at least one question'}), 400
    
    survey.status = SurveyStatus.PUBLISHED
    db.session.commit()
    
    return jsonify({'message': 'Survey published', 'survey': survey.to_dict()}), 200


@surveys_bp.route('/<int:survey_id>/close', methods=['POST'])
@jwt_required()
def close_survey(survey_id):
    """Закрыть опрос"""
    current_user_id = get_jwt_identity()
    survey = Survey.query.get_or_404(survey_id)
    
    if not _check_authorship(survey, current_user_id):
        return jsonify({'error': 'Forbidden'}), 403
    
    if survey.status != SurveyStatus.PUBLISHED:
        return jsonify({'error': 'Only published surveys can be closed'}), 400
    
    survey.status = SurveyStatus.CLOSED
    db.session.commit()
    
    return jsonify({'message': 'Survey closed'}), 200


@surveys_bp.route('/<int:survey_id>/submit', methods=['POST'])
@jwt_required()
def submit_response(survey_id):
    """Пройти опрос и отправить ответы с полной валидацией"""
    current_user_id = get_jwt_identity()  # str
    survey = Survey.query.get_or_404(survey_id)
    
    # 1. Можно проходить только опубликованные опросы
    if survey.status != SurveyStatus.PUBLISHED:
        return jsonify({'error': 'Survey is not active'}), 400
    
    # 2. Защита от повторного прохождения
    # ✅ Исправлено: преобразуем user_id к int для запроса к БД
    if Response.query.filter_by(survey_id=survey.id, user_id=int(current_user_id)).first():
        return jsonify({'error': 'You have already responded to this survey'}), 400
    
    data = request.get_json()
    answers_data = data.get('answers', [])
    
    if not answers_data:
        return jsonify({'error': 'No answers provided'}), 400
    
    # 3. Валидация: все обязательные вопросы должны быть отвечены
    question_ids = {q.id for q in survey.questions}
    answered_ids = {a.get('question_id') for a in answers_data if a.get('question_id')}
    
    if question_ids != answered_ids:
        missing = question_ids - answered_ids
        return jsonify({'error': f'Missing answers for questions: {list(missing)}'}), 400
    
    # Создаём запись о прохождении
    response = Response(survey_id=survey.id, user_id=int(current_user_id))
    db.session.add(response)
    db.session.flush()
    
    # 4. Обработка и валидация каждого ответа
    for ans_data in answers_data:
        question_id = ans_data.get('question_id')
        question = Question.query.get(question_id)
        
        if not question or question.survey_id != survey.id:
            return jsonify({'error': f'Invalid question_id: {question_id}'}), 400
        
        answer = Answer(response_id=response.id, question_id=question.id)
        
        if question.q_type == QuestionType.TEXT:
            text_val = ans_data.get('value', '').strip()
            if not text_val:
                return jsonify({'error': f'Text answer required for question {question_id}'}), 400
            answer.text_value = text_val
            
        elif question.q_type in [QuestionType.SINGLE, QuestionType.MULTIPLE]:
            option_id = ans_data.get('option_id')
            if not option_id:
                return jsonify({'error': f'Option required for question {question_id}'}), 400
            
            option = Option.query.get(option_id)
            if not option or option.question_id != question.id:
                return jsonify({'error': f'Invalid option_id for question {question_id}'}), 400
            answer.option_id = option_id
        else:
            return jsonify({'error': f'Unknown question type: {question.q_type}'}), 400
        
        db.session.add(answer)
    
    db.session.commit()
    return jsonify({'message': 'Response submitted', 'response_id': response.id}), 201


@surveys_bp.route('/<int:survey_id>/results', methods=['GET'])
@jwt_required()
def get_results(survey_id):
    """Получить аналитику по опросу (только автор)"""
    current_user_id = get_jwt_identity()
    survey = Survey.query.get_or_404(survey_id)
    
    if not _check_authorship(survey, current_user_id):
        return jsonify({'error': 'Forbidden'}), 403
    
    total_responses = Response.query.filter_by(survey_id=survey.id).count()
    
    results = {
        'survey_id': survey.id,
        'total_responses': total_responses,
        'questions': []
    }
    
    for question in survey.questions:
        q_result = {
            'question_id': question.id,
            'text': question.text,
            'type': question.q_type.value
        }
        
        if question.q_type == QuestionType.TEXT:
            text_answers = db.session.query(Answer.text_value)\
                .join(Response)\
                .filter(
                    Answer.question_id == question.id,
                    Response.survey_id == survey.id,
                    Answer.text_value != None
                ).all()
            q_result['answers'] = [a[0] for a in text_answers if a[0]]
        else:
            options_stats = []
            for option in question.options:
                count = db.session.query(Answer)\
                    .join(Response)\
                    .filter(
                        Answer.option_id == option.id,
                        Response.survey_id == survey.id
                    ).count()
                
                percent = (count / total_responses * 100) if total_responses > 0 else 0
                options_stats.append({
                    'option_id': option.id,
                    'text': option.text,
                    'count': count,
                    'percentage': round(percent, 2)
                })
            q_result['options'] = options_stats
        
        results['questions'].append(q_result)
    
    return jsonify(results), 200


@surveys_bp.route('/<int:survey_id>/results/export', methods=['GET'])
@jwt_required()
def export_results(survey_id):
    """Экспорт результатов в JSON"""
    current_user_id = get_jwt_identity()
    survey = Survey.query.get_or_404(survey_id)
    
    if not _check_authorship(survey, current_user_id):
        return jsonify({'error': 'Forbidden'}), 403
    
    responses = Response.query.filter_by(survey_id=survey.id).all()
    
    export_data = {
        'survey': survey.to_dict(),
        'responses': []
    }
    
    for resp in responses:
        resp_data = {
            'user_id': resp.user_id,
            'submitted_at': resp.submitted_at.isoformat() if resp.submitted_at else None,
            'answers': []
        }
        
        for answer in resp.answers:
            ans_data = {
                'question_id': answer.question_id,
                'question_text': answer.question.text if answer.question else None,
                'question_type': answer.question.q_type.value if answer.question else None
            }
            
            if answer.question and answer.question.q_type == QuestionType.TEXT:
                ans_data['value'] = answer.text_value
            elif answer.option:
                ans_data['value'] = answer.option.text
            
            resp_data['answers'].append(ans_data)
        
        export_data['responses'].append(resp_data)
    
    return jsonify(export_data), 200