from app.extensions import db, bcrypt

class User(db.Model):
    """Модель Пользователя системы"""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Связи: созданные опросы и пройденные опросы
    surveys = db.relationship('Survey', backref='author', lazy=True)
    responses = db.relationship('Response', backref='respondent', lazy=True)

    def set_password(self, password):
        """Хеширование пароля перед сохранением"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Проверка пароля при входе"""
        return bcrypt.check_password_hash(self.password_hash, password)