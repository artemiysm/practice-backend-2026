from flask import Flask
from app.config import Config
from app.extensions import db, migrate, jwt, bcrypt
from app.models.user import User 
from app.models.survey import Survey, Question, Option
from app.models.answer import Response, Answer
from app.api.auth import auth_bp
from app.api.surveys import surveys_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    
    # Регистрация блюпринтов
    app.register_blueprint(auth_bp)
    app.register_blueprint(surveys_bp)
    
    return app