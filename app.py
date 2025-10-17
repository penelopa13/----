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
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///dev.db') + '?sslmode=require&channel_binding=require'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Models ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)
    ent_math = db.Column(db.Integer, default=0)  # 0-40
    ent_reading = db.Column(db.Integer, default=0)  # 0-40
    ent_history = db.Column(db.Integer, default=0)  # 0-20
    ent_profile1 = db.Column(db.Integer, default=0)  # 0-30
    ent_profile2 = db.Column(db.Integer, default=0)  # 0-30
    ent_subjects = db.Column(db.JSON)  # {"profile1": "Физика", "profile2": "Математика"}
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
    __tablename__ = 'test_results'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    answers = db.Column(db.JSON)
    mbti_type = db.Column(db.String(4))
    recommended_programs = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=db.func.now())

class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
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

# --- Utilities ---
def load_questions(lang='ru'):
    file_path = os.path.join('data', f'questions_{lang}.json')
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    random.shuffle(questions)
    return questions[:50]

def calculate_ent_total(ent_data):
    total = sum([ent_data.get(key, 0) for key in ['math', 'reading', 'history', 'profile1', 'profile2']])
    return min(total, 140)  # Ограничение 140 баллов

def calculate_mbti(answers, questions):
    dichotomies = {'I/E': 0, 'S/N': 0, 'T/F': 0, 'J/P': 0}
    for ans in answers:
        question = next((q for q in questions if q['id'] == ans['id']), None)
        if question:
            score = ans['value'] - 4
            if question['dichotomy'][0] in ['I', 'S', 'T', 'J']:
                score = -score
            dichotomies[question['dichotomy']] += score * (question.get('scale', 1))
    mbti = ''.join(['E' if dichotomies[k] > 0 else k[0] for k in dichotomies])
    return mbti

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

@app.route('/api/calc', methods=['POST'])
def api_calc():
    data = request.get_json() or {}
    vals = data.get('vals', [])
    total = sum([float(v or 0) for v in vals])
    return jsonify({'total': total})

@app.route('/api/test/questions', methods=['GET'])
@login_required
def get_questions():
    lang = session.get('lang', current_user.language)
    questions = load_questions(lang)
    return jsonify(questions)

@app.route('/api/test/ent-submit', methods=['POST'])
@login_required
def submit_ent():
    data = request.get_json() or {}
    ent_data = {
        'math': data.get('math', 0),
        'reading': data.get('reading', 0),
        'history': data.get('history', 0),
        'profile1': data.get('profile1', 0),
        'profile2': data.get('profile2', 0)
    }
    current_user.ent_math = ent_data['math']
    current_user.ent_reading = ent_data['reading']
    current_user.ent_history = ent_data['history']
    current_user.ent_profile1 = ent_data['profile1']
    current_user.ent_profile2 = ent_data['profile2']
    current_user.ent_subjects = data.get('subjects', {})
    current_user.ent_total = calculate_ent_total(ent_data)
    db.session.commit()
    return jsonify({'total': current_user.ent_total, 'message': 'Баллы сохранены'})

@app.route('/api/test/personality-submit', methods=['POST'])
@login_required
def submit_personality():
    data = request.get_json() or {}
    answers = data.get('answers', [])
    lang = session.get('lang', current_user.language)
    questions = load_questions(lang)
    mbti = calculate_mbti(answers, questions)
    openai.api_key = os.getenv('OPENAI_API_KEY')
    ai_prompt = f"Ты — ИИ-консультант «Талапкер» АРУ им. Жубанова. Рекомендуй 3–5 программ на основе MBTI: {mbti}, ЕНТ: {current_user.ent_total} баллов, предметы: {current_user.ent_subjects}. Отвечай на {lang}."
    ai_response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "Ты консультант АRU. Рекомендуй программы."}, {"role": "user", "content": ai_prompt}]
    ).choices[0].message.content
    new_result = TestResult(user_id=current_user.id, answers=json.dumps(answers), mbti_type=mbti, recommended_programs=json.dumps({'ai_suggestions': ai_response}))
    db.session.add(new_result)
    db.session.commit()
    return jsonify({'mbti': mbti, 'recommendations': ai_response})

@app.route('/api/test/combined-result', methods=['GET'])
@login_required
def get_combined_result():
    result = TestResult.query.filter_by(user_id=current_user.id).order_by(TestResult.created_at.desc()).first()
    return jsonify({
        'ent_total': current_user.ent_total,
        'ent_subjects': current_user.ent_subjects,
        'mbti': result.mbti_type if result else None,
        'recommendations': result.recommended_programs if result else None
    })

@app.route('/api/ai_chat', methods=['POST'])
def ai_chat():
    data = request.get_json() or {}
    user_msg = data.get('message', '')
    lang = session.get('lang', 'ru')
    openai.api_key = os.getenv('OPENAI_API_KEY')
    system_prompt = f"Ты — ИИ-консультант «Талапкер» АРУ им. Жубанова. Отвечай вежливо и понятно на {lang}."
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg}]
    ).choices[0].message.content
    new_chat = ChatHistory(user_id=current_user.id, message=user_msg, response=response)
    db.session.add(new_chat)
    db.session.commit()
    return jsonify({'reply': response})

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in ['ru', 'kk', 'en']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)