import datetime
import keyword
import os
import json
import re
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, request as flask_request
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user, UserMixin
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import google.generativeai as genai
from flask_mail import Mail, Message

load_dotenv()
# ==================== МУЛЬТИЯЗЫЧНОСТЬ ====================
try:
    with open('translations/translations.json', 'r', encoding='utf-8') as f:
        TRANS = json.load(f)
except FileNotFoundError:
    print("ВНИМАНИЕ: translations/translations.json не найден!")
    TRANS = {}
    
def t(key):
    """Функция перевода, доступна в шаблонах как {{ t('Ключ') }}"""
    if current_user.is_authenticated:
        lang = session.get('lang', current_user.language or 'ru')
    else:
        lang = session.get('lang', 'ru')
    
    return TRANS.get(key, {}).get(lang, key)

app = Flask(__name__)
# Добавь в начало app.py (после импортов)
FAQ_DATA = None
# Делаем функцию t() и текущий язык доступными во всех шаблонах
app.jinja_env.globals['t'] = t
app.jinja_env.globals['lang'] = lambda: session.get('lang', current_user.language if current_user.is_authenticated else 'ru')

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def load_faq_exact():
    global FAQ_DATA
    path = os.path.join('data', 'faq_exact.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            FAQ_DATA = json.load(f)
    else:
        FAQ_DATA = []

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
    mbti_type = db.Column(db.String(10))
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

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notif_type = db.Column(db.String(20), default='info')
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # null = всем пользователям
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    education = db.Column(db.String(200), nullable=False)
    specialty = db.Column(db.String(200), nullable=False)
    grant_or_paid = db.Column(db.String(50), nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


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
        print("Файл не найден:", file_path)
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    for q in questions:
        q['text'] = q.get('question', '')
    print(f"Загружено {len(questions)} вопросов для языка {lang}")
    return questions

def calculate_ent_total(ent_data):
    total = sum([ent_data.get(key, 0) for key in ['math', 'reading', 'history', 'profile1', 'profile2']])
    return min(total, 140)

# Добавь это один раз — где-то после моделей и before_request
@app.before_request
def before_request():
    if current_user.is_authenticated:
        session['lang'] = current_user.language

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang not in ['ru', 'kk', 'en']:
        lang = 'ru'
    session['lang'] = lang
    if current_user.is_authenticated:
        current_user.language = lang
        db.session.commit()
    return redirect(flask_request.referrer or url_for('home'))

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

def is_admission_question(text: str) -> bool:
    keywords = [
        "поступ", "прием", "грант", "ент", "құжат", "оқуға",
        "универ", "бакалавр", "магистратура", "admission",
        "apply", "grant", "documents", "application"
    ]
    text = text.lower()
    return any(k in text for k in keywords)


def detect_language(text):
    # Определяем язык по кириллице и характерным буквам
    text = text.lower()
    kazakh_chars = 'әғқңөұүһі'
    russian_chars = 'ыэё'
    if any(c in text for c in kazakh_chars):
        return 'kk'
    if any(c in text for c in russian_chars):
        return 'ru'
    if re.search(r'[a-z]', text) and not re.search(r'[а-яё]', text):
        return 'en'
    return 'ru'  # по умолчанию

def detect_language(text):
    text = text.lower()
    kazakh_chars = 'әғқңөұүһі'
    russian_chars = 'ыэё'
    if any(c in text for c in kazakh_chars):
        return 'kk'
    if any(c in text for c in russian_chars):
        return 'ru'
    if re.search(r'[a-z]', text) and not re.search(r'[а-яё]', text):
        return 'en'
    return 'ru'

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    
    if not user_message:
        return jsonify({"reply": "Пустое сообщение."})

    # Определяем язык вопроса
    question_lang = detect_language(user_message)

    # Проверяем точные совпадения в faq_exact.json
    if FAQ_DATA:
        msg_lower = user_message.lower()
        for item in FAQ_DATA:
            keywords = [k.lower() for k in item.get("keywords", [])]
            if any(kw in msg_lower for kw in keywords):
                answer = item.get(f"answer_{question_lang}") or item.get("answer_ru") or item.get("answer_kk", "Ответ временно недоступен.")
                
                # Сохраняем в историю
                db.session.add(ChatHistory(
                    user_id=current_user.id,
                    message=user_message,
                    response=answer
                ))
                db.session.commit()
                
                return jsonify({"reply": answer, "markdown": True})

    # Если нет точного ответа — Gemini
    try:
        prompt = f"""
Ты — ИИ-консультант по поступлению в АРГУ им. К. Жубанова.
ОТВЕЧАЙ ТОЛЬКО НА ТОМ ЖЕ ЯЗЫКЕ, на котором задан вопрос ({question_lang}).

Вопрос пользователя: {user_message}

Правила:
- Отвечай кратко и по делу
- Используй Markdown (списки, жирный текст, заголовки)
- Отвечай ТОЛЬКО по теме поступления, грантов, документов, сроков, общежития и т.д.
- Если вопрос не по теме — скажи: "Я могу отвечать только на вопросы о поступлении."

Ответ на {question_lang} языке:
"""

        model = genai.GenerativeModel('gemini-flash-latest')
        response = model.generate_content(prompt)
        reply = response.text.strip() if response.text else "Кешіріңіз, жауап бере алмадым."

        # Сохраняем в историю
        db.session.add(ChatHistory(
            user_id=current_user.id,
            message=user_message,
            response=reply
        ))
        db.session.commit()

        return jsonify({"reply": reply, "markdown": True})

    except Exception as e:
        print("Gemini error:", e)
        fallback = {
            'ru': "Сервис временно недоступен. Попробуйте позже.",
            'kk': "Қызмет уақытша қолжетімсіз. Кейін қайталап көріңіз.",
            'en': "Service temporarily unavailable. Try again later."
        }
        return jsonify({"reply": fallback.get(question_lang, fallback['ru']), "markdown": True})    

@app.route('/api/chat/history')
@login_required
def chat_history():
    history = ChatHistory.query.filter_by(user_id=current_user.id).order_by(ChatHistory.timestamp).all()
    return jsonify([
        {
            "message": h.message,
            "response": h.response,
            "timestamp": h.timestamp.strftime('%d.%m.%Y %H:%M')
        } for h in history
    ])


# === ЛИЧНЫЙ КАБИНЕТ ПОЛЬЗОВАТЕЛЯ ===
@app.route('/profile')
@login_required
def profile():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    result = TestResult.query.filter_by(user_id=current_user.id).order_by(TestResult.created_at.desc()).first()
    return render_template('profile.html', user=current_user, result=result)

# === АДМИН-ПАНЕЛЬ ===
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Доступ запрещён. Только для администраторов.', 'error')
        return redirect(url_for('profile'))

    users = User.query.all()
    results = TestResult.query.order_by(TestResult.created_at.desc()).limit(10).all()
    contact_messages = ContactMessage.query.order_by(ContactMessage.id.desc()).all()

    return render_template('admin/dashboard.html',
                           users=users,
                           results=results,
                           contact_messages=contact_messages)
@app.route('/api/admin/delete/<string:table>/<int:item_id>', methods=['DELETE'])
@login_required
def admin_delete(table, item_id):
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': 'forbidden'}), 403

    models = {
        'users': User,
        'results': TestResult,
        'messages': ContactMessage
    }

    model = models.get(table)
    if not model:
        return jsonify({'status': 'error', 'message': 'bad table'}), 400

    obj = model.query.get(item_id)
    if not obj:
        return jsonify({'status': 'error', 'message': 'not found'}), 404

    db.session.delete(obj)
    db.session.commit()

    return jsonify({'status': 'ok'})

# === РЕГИСТРАЦИЯ ===
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
        return redirect(url_for('profile'))  # Всегда в профиль
    return render_template('register.html')

# === ВХОД С ПЕРЕНАПРАВЛЕНИЕМ ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        pw = request.form.get('password')
        u = User.query.filter_by(email=email).first()
        if u and u.check_password(pw):
            login_user(u)
            flash(f'Добро пожаловать, {u.name or u.email}!', 'success')
            # ПЕРЕНАПРАВЛЕНИЕ ПО РОЛИ
            if u.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('profile'))
        flash('Неверный логин или пароль', 'error')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('home'))

# --- API Endpoints ---

# --- Настройка почты ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # dilnaz_utegenova@mail.ru
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # пароль или app password
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')  # обязательно!

mail = Mail(app)

@app.route('/submit_application', methods=['POST'])
def submit_application():
    data = request.form
    # Создаём заявку
    app_entry = Application(
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        phone=data.get('phone'),
        email=data.get('email'),
        education=data.get('education'),
        specialty=data.get('specialty'),
        grant_or_paid=data.get('grant_or_paid'),
        comment=data.get('comment')
    )
    db.session.add(app_entry)
    db.session.commit()

    # Отправка на почту
    try:
        msg = Message(
            subject=f"Новая заявка: {app_entry.first_name} {app_entry.last_name}",
            sender=app.config['MAIL_USERNAME'],
            recipients=['dilnaz22112005@gmail.com'],  # сюда
            body=f"""
Новая заявка на поступление:

Имя: {app_entry.first_name}
Фамилия: {app_entry.last_name}
Телефон: {app_entry.phone}
Email: {app_entry.email}
Образование: {app_entry.education}
Специальность: {app_entry.specialty}
Форма обучения: {app_entry.grant_or_paid}
Комментарий: {app_entry.comment or 'нет'}
            """
        )
        mail.send(msg)
    except Exception as e:
        print("Ошибка при отправке письма:", e)

    flash('Заявка успешно отправлена!', 'success')
    return redirect(url_for('home'))

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

def calculate_mbti(answers, questions):
    if len(answers) < 25:
        return "INTP"  # fallback

    # Фильтруем None и считаем только валидные ответы
    def safe_sum(slice_answers):
        valid = [x for x in slice_answers if x is not None]
        return sum(valid) if valid else 0

    # Делим вопросы по осям (по 7 на первые три, 5 на последнюю — стандартно)
    ei_score = safe_sum(answers[0:7])      # вопросы 1–7 → E/I
    ns_score = safe_sum(answers[7:14])     # 8–14 → S/N
    tf_score = safe_sum(answers[14:21])    # 15–21 → T/F
    jp_score = safe_sum(answers[21:25])    # 22–25 → J/P

    # Средний балл по оси (если все ответы — 3, то 21 для 7 вопросов)
    mid_ei = 3.5 * min(len([x for x in answers[0:7] if x is not None]), 7)
    mid_ns = 3.5 * min(len([x for x in answers[7:14] if x is not None]), 7)
    mid_tf = 3.5 * min(len([x for x in answers[14:21] if x is not None]), 7)
    mid_jp = 3.5 * min(len([x for x in answers[21:25] if x is not None]), 5)

    # Формируем тип
    result = ""
    result += "E" if ei_score > mid_ei else "I"
    result += "S" if ns_score > mid_ns else "N"
    result += "T" if tf_score > mid_tf else "F"
    result += "J" if jp_score > mid_jp else "P"

    return result

@app.route('/api/test/submit', methods=['POST'])
@login_required
def submit_test():
    data = request.get_json() or {}
    answers = data.get('answers', [])
    lang = session.get('lang', current_user.language)
    questions = load_questions(lang)
    mbti = calculate_mbti(answers, questions)

    mbti_data = load_mbti_data()
    result_info = mbti_data.get(mbti, {})

    # ← ВОТ ЭТО ГЛАВНОЕ ИСПРАВЛЕНИЕ!
    rec = {
        'title': (result_info.get('title') or {}).get(lang, mbti),
        'description': (result_info.get('description') or {}).get(lang, 'Описание временно недоступно.'),
        'strengths': (result_info.get('strengths') or {}).get(lang, '—'),
        'percentages': result_info.get('percentages', {}),
        'professions': (result_info.get('professions') or {}).get(lang, ['Нет рекомендаций']),
    }

    result = TestResult(
        user_id=current_user.id,
        answers=json.dumps(answers, ensure_ascii=False),
        recommended_programs=json.dumps(rec, ensure_ascii=False),
        mbti_type=mbti
    )
    db.session.add(result)
    db.session.commit()

    return jsonify({
        'mbti': mbti,
        'recommendations': rec
    })


# === ИНИЦИАЛИЗАЦИЯ АДМИНА ===
def create_admin():
    if not User.query.filter_by(email='admin@site.com').first():
        admin = User(
            name='Администратор',
            email='admin@site.com',
            is_admin=True,
            language='ru'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Админ создан: admin@site.com / admin123")

@app.route('/api/admin/notify', methods=['POST'])
@login_required
def admin_notify():
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': 'Доступ запрещен'}), 403

    data = request.get_json() or {}
    title = data.get('title')
    message = data.get('message')
    notif_type = data.get('type')
    recipient = data.get('recipient')  # "all" или user_id

    if not title or not message:
        return jsonify({'status': 'error', 'message': 'Заполните все поля'}), 400

    if recipient == 'all':
        users = User.query.all()
        for u in users:
            notif = Notification(
                title=title,
                message=message,
                notif_type=notif_type,
                recipient_id=u.id
            )
            db.session.add(notif)

            # ← отправка email каждому
            try:
                msg = Message(
                    subject=title,
                    recipients=[u.email],
                    body=f"{message}\n\nУниверситет Жубанова"
                )
                mail.send(msg)
            except Exception as e:
                print("Ошибка email:", e)

    else:
        user = User.query.get(int(recipient))
        if not user:
            return jsonify({'status': 'error', 'message': 'Пользователь не найден'}), 404

        notif = Notification(
            title=title,
            message=message,
            notif_type=notif_type,
            recipient_id=user.id
        )
        db.session.add(notif)

        # отправка email конкретному
        try:
            msg = Message(
                subject=title,
                recipients=[user.email],
                body=f"{message}\n\nУниверситет Жубанова"
            )
            mail.send(msg)
        except Exception as e:
            print("Ошибка email:", e)


    db.session.commit()
    return jsonify({'status': 'ok', 'message': 'Уведомление отправлено'})


@app.route('/api/notifications')
@login_required
def get_notifications():
    notifs = Notification.query.filter_by(recipient_id=current_user.id).order_by(Notification.created_at.desc()).all()
    
    return jsonify([
        {
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.notif_type,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%d.%m.%Y %H:%M')
        }
        for n in notifs
    ])

@app.route('/api/notifications/read/<int:notif_id>', methods=['POST'])
@login_required
def mark_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.recipient_id != current_user.id:
        return jsonify({'status': 'error'}), 403
    notif.is_read = True
    db.session.commit()
    return jsonify({'status': 'ok'})

with app.app_context():
    db.create_all()
    create_admin()
    load_faq_exact()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin()
    app.run(debug=True)