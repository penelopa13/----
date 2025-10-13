# app.py
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user, UserMixin
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length
from flask_babel import Babel, _

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:ndd@localhost/talapker')  # Замени на свои данные PostgreSQL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['BABEL_DEFAULT_LOCALE'] = 'ru'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
csrf = CSRFProtect(app)
babel = Babel(app)

@babel.localeselector_function  # Исправлено: правильный декоратор
def get_locale():
    return request.args.get('lang', 'ru')

# --- Models ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), default='abiturient')  # abiturient, parent, student, employee

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    message = db.Column(db.Text)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, accepted, rejected
    documents = db.Column(db.Text)  # JSON или строка с путями к файлам
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- Forms ---
class RegisterForm(FlaskForm):
    name = StringField(_('Имя'), validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField(_('Email'), validators=[DataRequired(), Email()])
    password = PasswordField(_('Пароль'), validators=[DataRequired(), Length(min=6)])
    role = SelectField(_('Роль'), choices=[('abiturient', _('Абитуриент')), ('parent', _('Родитель')), ('student', _('Студент')), ('employee', _('Сотрудник'))])
    submit = SubmitField(_('Зарегистрироваться'))

class LoginForm(FlaskForm):
    email = StringField(_('Email'), validators=[DataRequired(), Email()])
    password = PasswordField(_('Пароль'), validators=[DataRequired()])
    submit = SubmitField(_('Войти'))

# --- User loader ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Основные страницы ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/university')
def university():
    return render_template('university.html')

@app.route('/status')
def status():
    return render_template('status.html')

@app.route('/programs')
def programs():
    return render_template('programs.html')

@app.route('/calculator')
def calculator():
    return render_template('calculator.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# --- Profile ---
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

# --- Auth routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash(_('Пользователь с таким Email уже существует'), 'error')
            return redirect(url_for('register'))
        u = User(name=form.name.data, email=form.email.data, role=form.role.data)
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.commit()
        login_user(u)
        flash(_('Регистрация прошла успешно'), 'success')
        return redirect(url_for('profile'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        u = User.query.filter_by(email=form.email.data).first()
        if u and u.check_password(form.password.data):
            login_user(u)
            return redirect(url_for('profile'))
        flash(_('Неверный логин или пароль'), 'error')
        return redirect(url_for('login'))
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# --- API endpoints ---
@app.route('/api/status')
@login_required
def api_status():
    user = current_user
    application = Application.query.filter_by(user_id=user.id).first()
    if not application:
        return jsonify({'message': _('Заявка не найдена')}), 404
    return jsonify({'status': application.status, 'created_at': application.created_at.isoformat()})

@app.route('/api/contact', methods=['POST'])
def api_contact():
    data = request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    message = data.get('message')
    if not (name and email and message):
        return jsonify({'status':'error','message': _('Заполните все поля')}), 400
    cm = ContactMessage(name=name, email=email, message=message)
    db.session.add(cm)
    db.session.commit()
    return jsonify({'status':'ok','message': _('Спасибо, мы свяжемся с вами.')})

@app.route('/api/calc', methods=['POST'])
def api_calc():
    data = request.get_json() or {}
    vals = data.get('vals', [])
    if not vals or not all(isinstance(v, (int, float)) for v in vals):
        return jsonify({'status': 'error', 'message': _('Некорректные данные')}), 400
    total = sum(float(v) for v in vals)
    passing_score = 50  # Замени на реальный порог для поступления
    return jsonify({
        'total': total,
        'can_apply': total >= passing_score,
        'message': _('Достаточно баллов для поступления') if total >= passing_score else _('Недостаточно баллов')
    })

@app.route('/api/ai_chat', methods=['POST'])
def ai_chat():
    return jsonify({'reply': _('Это заглушка AI. Интеграция OpenAI здесь.')})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)