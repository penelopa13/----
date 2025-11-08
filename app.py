import datetime
import os
import json
import random
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user, UserMixin
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import openai

load_dotenv()
app = Flask(__name__)
# --- Custom Jinja filter ---
@app.template_filter('from_json')
def from_json_filter(s):
    """Преобразует JSON-строку в объект Python (dict/list)"""
    try:
        return json.loads(s)
    except Exception:
        return {}

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///dev.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

from flask_migrate import Migrate
migrate = Migrate(app, db)

# --- Models ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)
    ent_math = db.Column(db.Integer, default=0)
    ent_reading = db.Column(db.Integer, default=0)
    ent_history = db.Column(db.Integer, default=0)
    ent_profile1 = db.Column(db.Integer, default=0)
    ent_profile2 = db.Column(db.Integer, default=0)
    ent_subjects = db.Column(db.JSON)
    ent_total = db.Column(db.Integer, default=0)
    language = db.Column(db.String(10), default='ru')

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class FAQ(db.Model):
    __tablename__ = 'faq'
    id = db.Column(db.Integer, primary_key=True)
    question_ru = db.Column(db.Text)
    question_kz = db.Column(db.Text)
    question_en = db.Column(db.Text)
    answer_ru = db.Column(db.Text)
    answer_kz = db.Column(db.Text)
    answer_en = db.Column(db.Text)

class TestQuestion(db.Model):
    __tablename__ = 'test_questions'
    id = db.Column(db.Integer, primary_key=True)
    text_ru = db.Column(db.Text)
    text_kz = db.Column(db.Text)
    text_en = db.Column(db.Text)
    category = db.Column(db.String(50))

class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    answers = db.Column(db.Text)
    recommended_programs = db.Column(db.Text)
    mbti_type = db.Column(db.String(10))  # добавляем тип MBTI
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)


class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.Text)
    response = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=db.func.now())

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    message = db.Column(db.Text)

# --- User loader ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def load_mbti_data():
    file_path = os.path.join('data', 'mbti.json')
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# --- Utilities ---
def load_questions(lang='ru'):
    file_path = os.path.join('data', f'questions_{lang}.json')
    if not os.path.exists(file_path):
        print("❌ Файл не найден:", file_path)
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    for q in questions:
        q['text'] = q.get('question', '')
    print(f"✅ Загружено {len(questions)} вопросов для языка {lang}")
    return questions


def calculate_ent_total(ent_data):
    total = sum([ent_data.get(key, 0) for key in ['math', 'reading', 'history', 'profile1', 'profile2']])
    return min(total, 140)

# --- Routes ---
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
@login_required
def calculator():
    return render_template('calculator.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/test_psy')
@login_required
def test_psy():
    lang = session.get('lang', current_user.language)
    questions = load_questions(lang)
    return render_template('test_psy.html', questions=questions, lang=lang)

@app.route('/profile')
@login_required
def profile():
    result = TestResult.query.filter_by(user_id=current_user.id).order_by(TestResult.created_at.desc()).first()
    return render_template('profile.html', user=current_user, result=result)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким Email уже существует', 'error')
            return redirect(url_for('register'))
        u = User(name=name, email=email, language=session.get('lang', 'ru'))
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        login_user(u)
        flash('Регистрация прошла успешно', 'success')
        return redirect(url_for('profile'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        pw = request.form.get('password')
        u = User.query.filter_by(email=email).first()
        if u and u.check_password(pw):
            login_user(u)
            return redirect(url_for('profile'))
        flash('Неверный логин или пароль', 'error')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# --- API Endpoints ---
@app.route('/api/status')
def api_status():
    q = request.args.get('q', '')
    if q == '':
        return jsonify({'message': 'Введите номер заявки или Email'}), 400
    return jsonify({'message': f'Статус для "{q}": Заявка принята, ожидает проверки.'})

@app.route('/api/contact', methods=['POST'])
def api_contact():
    data = request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    message = data.get('message')
    if not (name and email and message):
        return jsonify({'status': 'error', 'message': 'Заполните все поля'}), 400
    cm = ContactMessage(name=name, email=email, message=message)
    db.session.add(cm)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': 'Спасибо, мы свяжемся с вами.'})

@app.route('/api/test/questions', methods=['GET'])
@login_required
def get_questions():
    lang = session.get('lang', current_user.language)
    questions = load_questions(lang)
    return jsonify(questions)


# --- Психологический тест ---
def calculate_mbti(answers, questions):
    """
    На основе ответов считает количество баллов по 4 осям MBTI
    и возвращает тип, например 'INTJ'
    """
    # Каждая пара осей MBTI
    mbti_axes = {
        'EI': 0,  # Extroversion / Introversion
        'SN': 0,  # Sensing / Intuition
        'TF': 0,  # Thinking / Feeling
        'JP': 0   # Judging / Perceiving
    }

    # Для простоты: категории вопросов должны быть связаны с одной из осей
    mapping = {
        'extroversion': 'EI',
        'introversion': 'EI',
        'sensing': 'SN',
        'intuition': 'SN',
        'thinking': 'TF',
        'feeling': 'TF',
        'judging': 'JP',
        'perceiving': 'JP'
    }

    # Пробегаем по ответам
    for a in answers:
        qid = a.get('id')
        value = int(a.get('value', 0))
        question = next((q for q in questions if q['id'] == qid), None)
        if not question:
            continue

        cat = question.get('category', '').lower()
        axis = mapping.get(cat, None)
        if not axis:
            continue

        # Чем выше значение (4-5) — тем сильнее "первое" направление оси
        if axis == 'EI':
            mbti_axes['EI'] += (value - 3) if cat == 'extroversion' else -(value - 3)
        elif axis == 'SN':
            mbti_axes['SN'] += (value - 3) if cat == 'sensing' else -(value - 3)
        elif axis == 'TF':
            mbti_axes['TF'] += (value - 3) if cat == 'thinking' else -(value - 3)
        elif axis == 'JP':
            mbti_axes['JP'] += (value - 3) if cat == 'judging' else -(value - 3)

    # Определяем буквы по осям
    result = ''
    result += 'E' if mbti_axes['EI'] >= 0 else 'I'
    result += 'S' if mbti_axes['SN'] >= 0 else 'N'
    result += 'T' if mbti_axes['TF'] >= 0 else 'F'
    result += 'J' if mbti_axes['JP'] >= 0 else 'P'

    return result


@app.route('/api/test/submit', methods=['POST'])
@login_required
def submit_test():
    """Получает ответы, считает результат, сохраняет в БД"""
    data = request.get_json() or {}
    answers = data.get('answers', [])
    lang = session.get('lang', current_user.language)

    # Загружаем вопросы
    questions = load_questions(lang)
    mbti = calculate_mbti(answers, questions)

    # Загружаем рекомендации
    mbti_data = load_mbti_data()
    result_info = mbti_data.get(mbti, None)
    if result_info:
        rec = {
            'title': result_info['title'][lang],
            'description': result_info['description'][lang],
            'programs': result_info['recommended_programs'][lang]
        }
    else:
        rec = {'title': 'Не определено', 'description': 'Попробуйте снова', 'programs': []}

    # Сохраняем
    result = TestResult(
        user_id=current_user.id,
        answers=json.dumps(answers, ensure_ascii=False),
        recommended_programs=json.dumps(rec, ensure_ascii=False),
        mbti_type=mbti  # добавляем сам тип
    )

    db.session.add(result)
    db.session.commit()

    return jsonify({'mbti': mbti, 'recommendations': rec})

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in ['ru', 'kk', 'en']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
