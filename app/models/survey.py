from app.extensions import db
from datetime import datetime
from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum

# === СТАТУСЫ ОПРОСА ===
# Жизненный цикл опроса:
# 1. DRAFT (Черновик) - Создан автором, виден только автору, можно редактировать.
# 2. PUBLISHED (Опубликован) - Виден всем, можно проходить, нельзя редактировать.
# 3. CLOSED (Закрыт) - Прохождение запрещено, доступна только статистика.
class SurveyStatus(Enum):
    DRAFT = 'draft'
    PUBLISHED = 'published'
    CLOSED = 'closed'

# === ТИПЫ ВОПРОСОВ ===
class QuestionType(Enum):
    SINGLE = 'single'      # Один вариант ответа (Radio)
    MULTIPLE = 'multiple'  # Несколько вариантов (Checkbox) - в данной реализации упрощено до одного choice в Answer
    TEXT = 'text'          # Текстовое поле

class Survey(db.Model):
    """Модель Опроса"""
    __tablename__ = 'surveys'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    # Статус опроса (см. SurveyStatus)
    status = db.Column(
        SQLAlchemyEnum(SurveyStatus, name='survey_status', create_type=False), 
        default=SurveyStatus.DRAFT,
        nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # ID автора (создателя) опроса
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Связи: вопросы и ответы удаляются каскадно при удалении опроса
    questions = db.relationship('Question', backref='survey', lazy=True, cascade='all, delete-orphan')
    responses = db.relationship('Response', backref='survey', lazy=True, cascade='all, delete-orphan')

    def to_dict(self, include_questions=False):
        """Сериализация опроса в JSON"""
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'author_id': self.author_id
        }
        if include_questions:
            data['questions'] = [q.to_dict() for q in self.questions]
        return data


class Question(db.Model):
    """Модель Вопроса внутри опроса"""
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('surveys.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    # Тип вопроса (см. QuestionType)
    q_type = db.Column(
        SQLAlchemyEnum(QuestionType, name='question_type', create_type=False),
        nullable=False
    )
    order = db.Column(db.Integer, default=0) # Порядок отображения

    options = db.relationship('Option', backref='question', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'type': self.q_type.value,
            'order': self.order,
            'options': [opt.to_dict() for opt in self.options] if self.options else None
        }


class Option(db.Model):
    """Модель Варианта ответа для вопросов с выбором"""
    __tablename__ = 'options'
    
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    text = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {'id': self.id, 'text': self.text}