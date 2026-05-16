import datetime
import os
import json
import re
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, request as flask_request, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask_mail import Mail, Message
# === GEMINI IMPORTS ===
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv


# Инициализация клиента

import sys
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
FILE_SEARCH_STORE_NAME = "fileSearchStores/zhubanov-university-knowled-qp4q7i4cfpv5"
# === ROLE DECORATORS ===


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.role not in roles and current_user.role != 'admin':
                flash(t('У вас нет доступа к этой странице.'), 'error')
                return redirect(url_for('profile'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

admin_required = role_required('admin')
staff_required = role_required('staff', 'admin')
applicant_required = role_required('applicant')

# === MULTILANG ===
try:
    with open('translations/translations.json', 'r', encoding='utf-8') as f:
        TRANS = json.load(f)
except FileNotFoundError:
    TRANS = {}

def t(key):
    if current_user.is_authenticated:
        lang = session.get('lang', current_user.language or 'ru')
    else:
        lang = session.get('lang', 'ru')
    return TRANS.get(key, {}).get(lang, key)

app = Flask(__name__)
FAQ_DATA = None
DIALOG_SCENARIOS = {}

app.jinja_env.globals['t'] = t
app.jinja_env.globals['lang'] = lambda: session.get('lang', current_user.language if current_user.is_authenticated else 'ru')


def load_faq_exact():
    global FAQ_DATA
    path = os.path.join('data', 'faq_exact.json')
    FAQ_DATA = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else []

def load_dialog_scenarios():
    global DIALOG_SCENARIOS
    path = os.path.join('data', 'dialog_scenarios.json')
    DIALOG_SCENARIOS = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}

@app.template_filter('from_json')
def from_json_filter(s):
    try:
        return json.loads(s)
    except Exception:
        return {}

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///dev.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
mail = Mail(app)

from flask_migrate import Migrate
migrate = Migrate(app, db)


# === MODELS ===

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(200), nullable=True)
    role = db.Column(db.String(20), default='applicant', nullable=False)

    eds_serial_number = db.Column(db.String(100), unique=True, nullable=True, index=True)
    eds_iin = db.Column(db.String(12), unique=True, nullable=True, index=True)
    eds_full_name = db.Column(db.String(200), nullable=True)
    eds_certificate_data = db.Column(db.JSON, nullable=True)

    ent_math = db.Column(db.Integer, default=0)
    ent_reading = db.Column(db.Integer, default=0)
    ent_history = db.Column(db.Integer, default=0)
    ent_profile1 = db.Column(db.Integer, default=0)
    ent_profile2 = db.Column(db.Integer, default=0)
    ent_subjects = db.Column(db.JSON)
    ent_total = db.Column(db.Integer, default=0)
    language = db.Column(db.String(10), default='ru')

    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    middle_name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    birth_date = db.Column(db.Date, nullable=True)
    iin = db.Column(db.String(12), nullable=True)
    address = db.Column(db.String(300), nullable=True)
    school_name = db.Column(db.String(200), nullable=True)
    graduation_year = db.Column(db.Integer, nullable=True)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, pw)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def is_staff(self):
        return self.role in ['staff', 'admin']

    def is_applicant(self):
        return self.role == 'applicant'


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
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    recipient = db.relationship('User', foreign_keys=[recipient_id], lazy='joined')

class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    education = db.Column(db.String(200), nullable=False)
    specialty = db.Column(db.String(200), nullable=False)
    education_level = db.Column(db.String(50), nullable=True)
    grant_or_paid = db.Column(db.String(50), nullable=False, server_default='paid')
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String(30), default='received', nullable=False)
    staff_note = db.Column(db.Text, nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], lazy='joined')


class ApplicationComment(db.Model):
    __tablename__ = 'application_comments'
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    application = db.relationship('Application', backref='comments', lazy=True)
    staff = db.relationship('User', foreign_keys=[staff_id], lazy='joined')


# === CONSTANTS ===

APP_STATUSES_DATA = {
    'received': {'step': 1, 'color': '#27ae60', 'labels': {
        'ru': 'Получено',        'kk': 'Қабылданды',       'en': 'Received'}},
    'checking': {'step': 2, 'color': '#3498db', 'labels': {
        'ru': 'На проверке',     'kk': 'Тексерілуде',      'en': 'Under Review'}},
    'review':   {'step': 3, 'color': '#3498db', 'labels': {
        'ru': 'На рассмотрении', 'kk': 'Қаралуда',         'en': 'In Review'}},
    'decided':  {'step': 4, 'color': '#3498db', 'labels': {
        'ru': 'Решение принято', 'kk': 'Шешім қабылданды', 'en': 'Decision Made'}},
    'approved': {'step': 5, 'color': '#27ae60', 'labels': {
        'ru': 'Одобрено',        'kk': 'Мақұлданды',       'en': 'Approved'}},
    'rejected': {'step': 5, 'color': '#e74c3c', 'labels': {
        'ru': 'Отклонено',       'kk': 'Қабылданбады',     'en': 'Rejected'}},
    'revision': {'step': 5, 'color': '#e67e22', 'labels': {
        'ru': 'На доработке',    'kk': 'Түзетуде',          'en': 'Revision'}},
}

FINAL_LABELS = {'ru': 'Итог', 'kk': 'Қорытынды', 'en': 'Final'}

def get_app_statuses(lang='ru'):
    """Возвращает APP_STATUSES с label на нужном языке. Не читает session."""
    result = {}
    for key, data in APP_STATUSES_DATA.items():
        result[key] = {
            'label': data['labels'].get(lang, data['labels']['ru']),
            'step':  data['step'],
            'color': data['color'],
        }
    return result

def get_tracker_steps(lang='ru'):
    s = get_app_statuses(lang)
    return [
        ('received', s['received']['label']),
        ('checking', s['checking']['label']),
        ('review',   s['review']['label']),
        ('decided',  s['decided']['label']),
        ('final',    FINAL_LABELS.get(lang, 'Итог')),
    ]

# Значения по умолчанию (ru) — используются до первого запроса
APP_STATUSES  = get_app_statuses('ru')
TRACKER_STEPS = get_tracker_steps('ru')

DOC_TYPES_DATA = {
    'iin_scan':            {'ru': 'Удостоверение личности (ИИН)', 'kk': 'Жеке куәлік (ЖСН)',          'en': 'ID Card (IIN)'},
    'photo_3x4':           {'ru': 'Фото 3×4',                    'kk': 'Фото 3×4',                    'en': 'Photo 3×4'},
    'school_certificate':  {'ru': 'Аттестат / Диплом',           'kk': 'Аттестат / Диплом',           'en': 'Certificate / Diploma'},
    'transcript':          {'ru': 'Табель успеваемости',          'kk': 'Үлгерім табелі',              'en': 'Academic Transcript'},
    'medical_certificate': {'ru': 'Медицинская справка (форма 075)', 'kk': 'Медициналық анықтама (075 нысаны)', 'en': 'Medical Certificate (form 075)'},
    'other':               {'ru': 'Другой документ',             'kk': 'Басқа құжат',                 'en': 'Other Document'},
}

def get_doc_types(lang='ru'):
    return {k: v.get(lang, v['ru']) for k, v in DOC_TYPES_DATA.items()}

DOC_TYPES = get_doc_types('ru')

ALLOWED_MIMES = {'application/pdf', 'image/jpeg', 'image/png', 'image/jpg'}
MAX_FILE_SIZE = 10 * 1024 * 1024

app.jinja_env.globals['APP_STATUSES'] = APP_STATUSES
app.jinja_env.globals['TRACKER_STEPS'] = TRACKER_STEPS
app.jinja_env.globals['DOC_TYPES'] = DOC_TYPES


class UserDocument(db.Model):
    __tablename__ = 'user_documents'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doc_type = db.Column(db.String(50), nullable=False)
    display_name = db.Column(db.String(200), nullable=True)
    filename = db.Column(db.String(200), nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user = db.relationship('User', backref='documents', lazy=True)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def load_mbti_data():
    path = os.path.join('data', 'mbti.json')
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_questions(lang='ru'):
    path = os.path.join('data', f'questions_{lang}.json')
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    for q in questions:
        q['text'] = q.get('question', '')
    return questions

def calculate_ent_total(ent_data):
    total = sum([ent_data.get(key, 0) for key in ['math', 'reading', 'history', 'profile1', 'profile2']])
    return min(total, 140)


@app.before_request
def before_request():
    if current_user.is_authenticated and 'lang' not in session:
        session['lang'] = current_user.language or 'ru'
    lang = session.get('lang', 'ru')
    app.jinja_env.globals['APP_STATUSES']  = get_app_statuses(lang)
    app.jinja_env.globals['TRACKER_STEPS'] = get_tracker_steps(lang)
    app.jinja_env.globals['DOC_TYPES']     = get_doc_types(lang)

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang not in ['ru', 'kk', 'en']:
        lang = 'ru'
    session['lang'] = lang
    if current_user.is_authenticated:
        current_user.language = lang
        db.session.commit()
    return redirect(flask_request.referrer or url_for('home'))


# === MAIN ROUTES ===

@app.route('/')
def home():
    if current_user.is_authenticated:
        init_chat_state()
    return render_template('index.html')

@app.route('/university')
def university():
    return render_template('university.html')

@app.route('/programs')
def programs():
    return render_template('programs.html')

@app.route('/calculator')
@login_required
def calculator():
    return render_template('calculator.html')

@app.route('/api/calculator/recommend', methods=['POST'])
@login_required
def calculator_recommend():
    if current_user.role in ['staff', 'admin']:
        return jsonify({'error': 'Доступно только абитуриентам'}), 403

    data = request.get_json() or {}
    program  = data.get('program', '')
    faculty  = data.get('faculty', '')
    total    = int(data.get('total', 0))
    grant    = int(data.get('grant', 0))
    contract = int(data.get('contract', 0))
    lang     = data.get('lang', session.get('lang', 'ru'))

    if total >= grant and grant > 0:
        status_ru = 'Проходит на грант!'
        status_kk = 'Грантқа өтеді!'
        status_en = 'Qualifies for grant!'
    elif total >= contract and contract > 0:
        status_ru = 'Проходит на контракт.'
        status_kk = 'Ақылы оқуға өтеді.'
        status_en = 'Qualifies for paid education.'
    else:
        status_ru = f'Не проходит (нужно ещё {contract - total} баллов для контракта).'
        status_kk = f'Өтпейді (контрактқа {contract - total} балл жетіспейді).'
        status_en = f'Does not qualify ({contract - total} more points needed for contract).'

    prompts = {
        'ru': f"""Ты — дружелюбный ИИ-консультант для абитуриентов АРГУ им. Жубанова.

Данные абитуриента:
- Специальность: {program}
- Факультет: {faculty}
- Набранный балл ЕНТ: {total}
- Проходной балл на грант: {grant}
- Проходной балл на контракт: {contract}
- Статус: {status_ru}

Дай персональный практический совет: что делать дальше, на что обратить внимание, как повысить шансы. 
Будь позитивным, конкретным и кратким (4–6 предложений).""",

        'kk': f"""Сен — Жұбанов университетіне түсушілерге арналған ЖИ кеңесші.

Деректер:
- Мамандық: {program}
- Факультет: {faculty}
- ҰБТ балы: {total}
- Грантқа өтпелі балл: {grant}
- Ақылыға өтпелі балл: {contract}
- Мәртебе: {status_kk}

Жеке кеңес бер: не істеу керек, құжаттарға нені назар аудару керек, балл жетпесе қалай мүмкіндікті арттыруға болады. 
Нақты, оң және қысқа бол (4–6 сөйлем).""",

        'en': f"""You are a friendly AI consultant for applicants to Zhubanov University.

Applicant data:
- Specialty: {program}
- Faculty: {faculty}
- ENT score: {total}
- Grant threshold: {grant}
- Contract threshold: {contract}
- Status: {status_en}

Give practical personalized advice on next steps. Be positive, specific and concise (4-6 sentences)."""
    }

    prompt = prompts.get(lang, prompts['ru'])

    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",   # или gemini-flash-latest
            contents=[prompt]
        )
        text = response.text.strip() if response.text else ''
        return jsonify({'recommendation': text, 'ok': True})

    except Exception as e:
        print('Calculator recommend error:', e)
        fallback = {
            'ru': 'Сервис рекомендаций временно недоступен. Попробуйте позже.',
            'kk': 'Ұсыным қызметі уақытша қолжетімсіз. Кейінірек қайталаңыз.',
            'en': 'Recommendation service temporarily unavailable.'
        }
        return jsonify({'recommendation': fallback.get(lang, fallback['ru']), 'ok': False})
@app.route('/contact')
def contact():
    return render_template('contact.html')


# === APPLICANT STATUS PAGE ===

@app.route('/status')
@login_required
def status():
    docs = UserDocument.query.filter_by(user_id=current_user.id).all()
    docs_by_type = {d.doc_type: d for d in docs}
    u = current_user
    profile_complete = all([u.first_name, u.last_name, u.phone, u.iin, u.school_name])
    existing_app = Application.query.filter_by(user_id=current_user.id)\
                    .order_by(Application.created_at.desc()).first()
    return render_template('status.html',
                           user=u,
                           doc_types=DOC_TYPES,
                           docs_by_type=docs_by_type,
                           profile_complete=profile_complete,
                           existing_app=existing_app)


# === PROFILE ===

@app.route('/profile')
@login_required
def profile():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))

    lang = session.get('lang', current_user.language or 'ru')

    result = TestResult.query.filter_by(user_id=current_user.id)\
                            .order_by(TestResult.created_at.desc()).first()
    result_data = None
    if result:
        mbti_data = load_mbti_data()
        result_info = mbti_data.get(result.mbti_type, {})
        result_data = {
            'mbti_type': result.mbti_type,
            'recommended_programs': {
                'title':       (result_info.get('title') or {}).get(lang, result.mbti_type),
                'description': (result_info.get('description') or {}).get(lang, ''),
                'strengths':   (result_info.get('strengths') or {}).get(lang, '—'),
                'percentages': result_info.get('percentages', {}),
                'professions': (result_info.get('professions') or {}).get(lang, []),
            },
            'created_at': result.created_at
        }

    docs = UserDocument.query.filter_by(user_id=current_user.id).all()
    docs_by_type = {d.doc_type: d for d in docs}

    existing_app = Application.query.filter_by(user_id=current_user.id)\
                    .order_by(Application.created_at.desc()).first()

    notifications = Notification.query.filter_by(recipient_id=current_user.id)\
                    .order_by(Notification.created_at.desc()).limit(20).all()
    unread_count = Notification.query.filter_by(recipient_id=current_user.id, is_read=False).count()

    return render_template('profile.html',
                           user=current_user,
                           result=result_data,
                           doc_types=DOC_TYPES,
                           docs_by_type=docs_by_type,
                           existing_app=existing_app,
                           notifications=notifications,
                           unread_count=unread_count)


@app.route('/profile/edit', methods=['POST'])
@login_required
def profile_edit():
    u = current_user
    iin_val = request.form.get('iin', '').strip() or None

    if iin_val:
        conflict = User.query.filter(User.iin == iin_val, User.id != u.id).first()
        if conflict:
            flash(t('Этот ИИН уже зарегистрирован в системе за другим пользователем.'), 'error')
            return redirect(url_for('profile'))

    u.first_name    = request.form.get('first_name', '').strip() or None
    u.last_name     = request.form.get('last_name',  '').strip() or None
    u.middle_name   = request.form.get('middle_name', '').strip() or None
    u.phone         = request.form.get('phone',      '').strip() or None
    u.iin           = iin_val
    u.address       = request.form.get('address',    '').strip() or None
    u.school_name   = request.form.get('school_name', '').strip() or None

    birth_str = request.form.get('birth_date', '').strip()
    if birth_str:
        try:
            u.birth_date = datetime.datetime.strptime(birth_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    grad_str = request.form.get('graduation_year', '').strip()
    if grad_str.isdigit():
        u.graduation_year = int(grad_str)

    db.session.commit()
    flash(t('Профиль успешно обновлён!'), 'success')
    return redirect(url_for('profile'))


@app.route('/profile/documents/upload', methods=['POST'])
@login_required
def upload_document():
    doc_type = request.form.get('doc_type')
    file = request.files.get('file')

    if not doc_type or doc_type not in DOC_TYPES:
        flash(t('Неверный тип документа'), 'error')
        return redirect(url_for('profile'))

    if not file or file.filename == '':
        flash(t('Файл не выбран'), 'error')
        return redirect(url_for('profile'))

    if file.mimetype not in ALLOWED_MIMES:
        flash(t('Разрешены только PDF, JPG и PNG файлы'), 'error')
        return redirect(url_for('profile'))

    file_data = file.read()
    if len(file_data) > MAX_FILE_SIZE:
        flash(t('Файл слишком большой (максимум 10 МБ)'), 'error')
        return redirect(url_for('profile'))

    existing = UserDocument.query.filter_by(user_id=current_user.id, doc_type=doc_type).first()
    if existing:
        db.session.delete(existing)

    doc = UserDocument(
        user_id=current_user.id,
        doc_type=doc_type,
        display_name=DOC_TYPES[doc_type],
        filename=file.filename,
        file_data=file_data,
        mime_type=file.mimetype,
        file_size=len(file_data),
    )
    db.session.add(doc)
    db.session.commit()
    flash(t('Документ успешно загружен') + f': «{DOC_TYPES[doc_type]}»', 'success')
    return redirect(url_for('profile') + '#documents')

import urllib.parse

@app.route('/profile/documents/<int:doc_id>')
@login_required
def serve_document(doc_id):
    doc = UserDocument.query.get_or_404(doc_id)
    if doc.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'forbidden'}), 403

    # Правильная обработка кириллицы в имени файла
    filename = doc.filename
    encoded_filename = urllib.parse.quote(filename)

    return Response(
        doc.file_data,
        mimetype=doc.mime_type,
        headers={
            'Content-Disposition': f'inline; filename="{encoded_filename}"',
            # Лучший вариант для современных браузеров:
            # 'Content-Disposition': f'inline; filename*=UTF-8\'\'{encoded_filename}',
            'Content-Length': str(doc.file_size or len(doc.file_data))
        }
    )


@app.route('/profile/documents/<int:doc_id>/delete', methods=['POST'])
@login_required
def delete_document(doc_id):
    doc = UserDocument.query.get_or_404(doc_id)
    if doc.user_id != current_user.id:
        return jsonify({'error': 'forbidden'}), 403
    db.session.delete(doc)
    db.session.commit()
    flash(t('Документ удалён'), 'info')
    return redirect(url_for('profile') + '#documents')


# === APPLICATION SUBMISSION ===

@app.route('/submit_application', methods=['POST'])
@login_required
def submit_application():
    u = current_user
    specialty = request.form.get('specialty', '').strip()
    education_level = request.form.get('education_level', '').strip()
    grant_or_paid = request.form.get('grant_or_paid') or 'paid'

    if not specialty:
        flash(t('Выберите специальность'), 'error')
        return redirect(url_for('status'))

    # IIN duplicate check across same specialty
    if u.iin:
        iin_users = User.query.filter(User.iin == u.iin).all()
        for iin_user in iin_users:
            existing = Application.query.filter_by(user_id=iin_user.id, specialty=specialty).first()
            if existing:
                flash(t('Заявка на данную программу уже была подана с этим ИИН.'), 'error')
                return redirect(url_for('status'))

    app_entry = Application(
        user_id=u.id,
        first_name=u.first_name or '',
        last_name=u.last_name or '',
        phone=u.phone or '',
        email=u.email or '',
        education=u.school_name or '',
        education_level=education_level,
        specialty=specialty,
        grant_or_paid=grant_or_paid,
        comment=request.form.get('comment'),
        status='received',
    )
    db.session.add(app_entry)
    db.session.commit()

    try:
        msg = Message(
            subject=f"Новая заявка: {app_entry.first_name} {app_entry.last_name}",
            sender=app.config['MAIL_USERNAME'],
            recipients=['dilnaz22112005@gmail.com'],
            body=f"""Новая заявка на поступление:

Имя: {app_entry.first_name} {app_entry.last_name}
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

    flash(t('Заявка успешно подана!'), 'success')
    return redirect(url_for('status'))


# === STAFF INTERFACE ===

@app.route('/staff')
@staff_required
def staff_dashboard():
    total = Application.query.count()
    by_status = {}
    for s in APP_STATUSES:
        by_status[s] = Application.query.filter_by(status=s).count()

    status_filter = request.args.get('status', '')
    search = request.args.get('search', '').strip()

    query = Application.query
    if status_filter and status_filter in APP_STATUSES:
        query = query.filter_by(status=status_filter)
    if search:
        query = query.join(User, Application.user_id == User.id, isouter=True).filter(
            db.or_(
                Application.first_name.ilike(f'%{search}%'),
                Application.last_name.ilike(f'%{search}%'),
                Application.email.ilike(f'%{search}%'),
                User.iin.ilike(f'%{search}%'),
            )
        )

    applications = query.order_by(Application.created_at.desc()).all()

    return render_template('staff/dashboard.html',
                           applications=applications,
                           total=total,
                           by_status=by_status,
                           status_filter=status_filter,
                           search=search)


@app.route('/staff/applications/<int:app_id>')
@staff_required
def staff_application_detail(app_id):
    application = Application.query.get_or_404(app_id)
    applicant = User.query.get(application.user_id) if application.user_id else None
    docs = UserDocument.query.filter_by(user_id=application.user_id).all() if application.user_id else []
    docs_by_type = {d.doc_type: d for d in docs}
    comments = ApplicationComment.query.filter_by(application_id=app_id)\
                .order_by(ApplicationComment.created_at.asc()).all()

    return render_template('staff/application_detail.html',
                           application=application,
                           applicant=applicant,
                           docs_by_type=docs_by_type,
                           comments=comments)


@app.route('/staff/applications/<int:app_id>/status', methods=['POST'])
@staff_required
def staff_update_status(app_id):
    application = Application.query.get_or_404(app_id)
    new_status = request.form.get('status')

    if new_status not in APP_STATUSES:
        flash(t('Неверный статус'), 'error')
        return redirect(url_for('staff_application_detail', app_id=app_id))

    application.status = new_status
    staff_note = request.form.get('staff_note', '').strip()
    if staff_note:
        application.staff_note = staff_note

    if application.user_id:
        status_label = t(APP_STATUSES[new_status]['label_key'])
        notif_type = 'success' if new_status == 'approved' else ('error' if new_status == 'rejected' else 'info')
        notif = Notification(
            title='Статус вашей заявки изменён',
            message=f'Ваша заявка на специальность «{application.specialty}» перешла в статус: {status_label}.',
            notif_type=notif_type,
            recipient_id=application.user_id
        )
        db.session.add(notif)

    db.session.commit()
    flash(t('Статус заявки обновлён') + f': {t(APP_STATUSES[new_status]["label_key"])}', 'success')
    return redirect(url_for('staff_application_detail', app_id=app_id))


@app.route('/staff/applications/<int:app_id>/comment', methods=['POST'])
@staff_required
def staff_add_comment(app_id):
    application = Application.query.get_or_404(app_id)
    text = request.form.get('comment_text', '').strip()

    if not text:
        flash(t('Комментарий не может быть пустым'), 'error')
        return redirect(url_for('staff_application_detail', app_id=app_id))

    comment = ApplicationComment(
        application_id=app_id,
        staff_id=current_user.id,
        text=text
    )
    db.session.add(comment)

    if application.user_id:
        notif = Notification(
            title='Новый комментарий к вашей заявке',
            message=f'Сотрудник приёмной комиссии оставил комментарий к вашей заявке на специальность «{application.specialty}».',
            notif_type='info',
            recipient_id=application.user_id
        )
        db.session.add(notif)

    db.session.commit()
    flash(t('Комментарий добавлен'), 'success')
    return redirect(url_for('staff_application_detail', app_id=app_id))


@app.route('/staff/documents/<int:doc_id>')
@staff_required
def staff_serve_document(doc_id):
    doc = UserDocument.query.get_or_404(doc_id)
    
    # Правильная обработка кириллицы в имени файла
    import urllib.parse
    encoded_filename = urllib.parse.quote(doc.filename)

    return Response(
        doc.file_data,
        mimetype=doc.mime_type,
        headers={
            'Content-Disposition': f'attachment; filename="{encoded_filename}"',
            'Content-Length': str(doc.file_size or len(doc.file_data))
        }
    )
# === ADMIN ===

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash(t('Доступ запрещён.'), 'error')
        return redirect(url_for('profile'))

    users = User.query.all()
    results = TestResult.query.join(User, TestResult.user_id == User.id)\
                      .add_columns(
                          TestResult.id, TestResult.mbti_type, TestResult.created_at,
                          User.id.label('user_id'), User.name.label('user_name'), User.email.label('user_email')
                      ).order_by(TestResult.created_at.desc()).limit(50).all()

    contact_messages = ContactMessage.query.order_by(ContactMessage.id.desc()).all()
    notifications = Notification.query.order_by(Notification.created_at.desc()).limit(100).all()
    applications = Application.query.order_by(Application.created_at.desc()).limit(100).all()

    return render_template('admin/dashboard.html',
                           users=users, results=results,
                           contact_messages=contact_messages,
                           notifications=notifications,
                           applications=applications)


@app.route('/api/admin/delete/<string:table>/<int:item_id>', methods=['DELETE'])
@login_required
def admin_delete(table, item_id):
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': 'forbidden'}), 403

    models = {
        'users': User, 'results': TestResult, 'messages': ContactMessage,
        'notifications': Notification, 'applications': Application
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


# === AUTH ===

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            flash(t('Пользователь с таким Email уже существует'), 'error')
            return redirect(url_for('register'))
        
        if not password or len(password) < 8:
            flash(t('Пароль должен содержать не менее 8 символов'), 'error')
            return redirect(url_for('register'))
        
        u = User(name=name, email=email, role='applicant', language=session.get('lang', 'ru'))
        u.set_password(password)
        db.session.add(u)
        db.session.commit()

        login_user(u)
        flash(t('Регистрация прошла успешно!'), 'success')
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
            flash(t('Добро пожаловать') + f', {u.name or u.email}!', 'success')
            if u.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif u.role == 'staff':
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('profile'))

        flash(t('Неверный логин или пароль'), 'error')
    return render_template('login.html')


@app.route('/register-eds', methods=['GET', 'POST'])
def register_eds():
    if request.method == 'GET':
        return render_template('register_eds.html')
    data = request.get_json() or {}
    eds_serial = data.get('eds_serial_number')
    eds_iin = data.get('eds_iin')
    full_name = data.get('full_name')

    if not eds_serial or not eds_iin:
        return jsonify({'status': 'error', 'message': 'Данные ЭЦП не получены'}), 400

    if User.query.filter_by(eds_serial_number=eds_serial).first() or \
       User.query.filter_by(eds_iin=eds_iin).first():
        return jsonify({'status': 'error', 'message': 'Пользователь с этим ЭЦП уже зарегистрирован'}), 400

    u = User(name=full_name, role='applicant', eds_serial_number=eds_serial,
             eds_iin=eds_iin, eds_full_name=full_name,
             eds_certificate_data=data.get('certificate_data'),
             language=session.get('lang', 'ru'))
    db.session.add(u)
    db.session.commit()
    login_user(u)
    return jsonify({'status': 'ok', 'redirect': url_for('profile')})


@app.route('/login-eds', methods=['GET', 'POST'])
def login_eds():
    if request.method == 'GET':
        return render_template('login_eds.html')
    data = request.get_json() or {}
    eds_iin = data.get('eds_iin')
    if not eds_iin:
        return jsonify({'status': 'error', 'message': 'Данные ЭЦП не получены'}), 400
    u = User.query.filter_by(eds_iin=eds_iin).first()
    if not u:
        return jsonify({'status': 'error', 'message': 'Пользователь не найден. Пожалуйста, зарегистрируйтесь.'}), 404
    login_user(u)
    redirect_url = url_for('admin_dashboard') if u.role == 'admin' else url_for('profile')
    return jsonify({'status': 'ok', 'redirect': redirect_url})


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash(t('Вы вышли из системы.'), 'info')
    return redirect(url_for('home'))


# === NOTIFICATIONS API ===

@app.route('/api/notifications')
@login_required
def get_notifications():
    notifs = Notification.query.filter_by(recipient_id=current_user.id)\
                .order_by(Notification.created_at.desc()).all()
    return jsonify([{
        'id': n.id, 'title': n.title, 'message': n.message,
        'type': n.notif_type, 'is_read': n.is_read,
        'created_at': n.created_at.strftime('%d.%m.%Y %H:%M')
    } for n in notifs])


@app.route('/api/notifications/read/<int:notif_id>', methods=['POST'])
@login_required
def mark_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.recipient_id != current_user.id:
        return jsonify({'status': 'error'}), 403
    notif.is_read = True
    db.session.commit()
    return jsonify({'status': 'ok'})


@app.route('/api/notifications/read-all', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(recipient_id=current_user.id, is_read=False)\
        .update({'is_read': True})
    db.session.commit()
    return jsonify({'status': 'ok'})


# === ADMIN NOTIFY ===

@app.route('/api/admin/notify', methods=['POST'])
@login_required
def admin_notify():
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': t('Доступ запрещен')}), 403

    data = request.get_json() or {}
    title = data.get('title')
    message = data.get('message')
    notif_type = data.get('type', 'info')
    recipient = data.get('recipient')

    if not title or not message:
        return jsonify({'status': 'error', 'message': t('Заполните все поля')}), 400

    if recipient == 'all':
        users = User.query.all()
        for u in users:
            db.session.add(Notification(title=title, message=message,
                                        notif_type=notif_type, recipient_id=u.id))
            try:
                mail.send(Message(subject=title, recipients=[u.email],
                                  body=f"{message}\n\nУниверситет Жубанова"))
            except Exception as e:
                print("Email error:", e)
    else:
        user = User.query.get(int(recipient))
        if not user:
            return jsonify({'status': 'error', 'message': t('Пользователь не найден')}), 404
        db.session.add(Notification(title=title, message=message,
                                    notif_type=notif_type, recipient_id=user.id))
        try:
            mail.send(Message(subject=title, recipients=[user.email],
                              body=f"{message}\n\nУниверситет Жубанова"))
        except Exception as e:
            print("Email error:", e)

    db.session.commit()
    return jsonify({'status': 'ok', 'message': t('Уведомление отправлено')})


# === CONTACT ===

@app.route('/api/contact', methods=['POST'])
def api_contact():
    data = request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    message = data.get('message')
    if not (name and email and message):
        return jsonify({'status': 'error', 'message': t('Заполните все поля')}), 400
    db.session.add(ContactMessage(name=name, email=email, message=message))
    db.session.commit()
    return jsonify({'status': 'ok', 'message': t('Спасибо, мы свяжемся с вами.')})


# === PSY TEST ===

@app.route('/test_psy')
@login_required
def test_psy():
    lang = session.get('lang', current_user.language or 'ru')
    result = TestResult.query.filter_by(user_id=current_user.id)\
                            .order_by(TestResult.created_at.desc()).first()
    if result:
        mbti_data = load_mbti_data()
        result_info = mbti_data.get(result.mbti_type, {})
        recommended = {
            'title':       (result_info.get('title') or {}).get(lang, result.mbti_type),
            'description': (result_info.get('description') or {}).get(lang, ''),
            'strengths':   (result_info.get('strengths') or {}).get(lang, '—'),
            'percentages': result_info.get('percentages', {}),
            'professions': (result_info.get('professions') or {}).get(lang, []),
        }
        return render_template('test_psy.html', result={
            'mbti_type': result.mbti_type,
            'recommended_programs': recommended,
            'created_at': result.created_at
        })
    questions = load_questions(lang)
    return render_template('test_psy.html', questions=questions, lang=lang)


@app.route('/api/test/questions', methods=['GET'])
@login_required
def get_questions():
    lang = session.get('lang', current_user.language)
    return jsonify(load_questions(lang))


def calculate_mbti(answers, questions):
    if len(answers) < 25:
        return "INTP"
    def safe_sum(sl):
        valid = [x for x in sl if x is not None]
        return sum(valid) if valid else 0
    ei_score = safe_sum(answers[0:7])
    ns_score = safe_sum(answers[7:14])
    tf_score = safe_sum(answers[14:21])
    jp_score = safe_sum(answers[21:25])
    mid_ei = 3.5 * min(len([x for x in answers[0:7] if x is not None]), 7)
    mid_ns = 3.5 * min(len([x for x in answers[7:14] if x is not None]), 7)
    mid_tf = 3.5 * min(len([x for x in answers[14:21] if x is not None]), 7)
    mid_jp = 3.5 * min(len([x for x in answers[21:25] if x is not None]), 5)
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
    rec = {
        'title': (result_info.get('title') or {}).get(lang, mbti),
        'description': (result_info.get('description') or {}).get(lang, 'Описание временно недоступно.'),
        'strengths': (result_info.get('strengths') or {}).get(lang, '—'),
        'percentages': result_info.get('percentages', {}),
        'professions': (result_info.get('professions') or {}).get(lang, ['Нет рекомендаций']),
    }
    db.session.add(TestResult(
        user_id=current_user.id,
        answers=json.dumps(answers, ensure_ascii=False),
        recommended_programs=json.dumps(rec, ensure_ascii=False),
        mbti_type=mbti
    ))
    db.session.commit()
    return jsonify({'mbti': mbti, 'recommendations': rec})


# === CHAT ===

def is_admission_question(text):
    keywords = ["поступ", "прием", "грант", "ент", "құжат", "оқуға",
                "универ", "бакалавр", "магистратура", "admission",
                "apply", "grant", "documents", "application"]
    return any(k in text.lower() for k in keywords)

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

def init_chat_state():
    if "chat_history" not in session:
        session["chat_history"] = ["level_select"]
        session["chat_state"] = "level_select"

def push_state(state):
    hist = session.get("chat_history", ["level_select"])
    if hist[-1] != state:
        hist.append(state)
        session["chat_history"] = hist
    session["chat_state"] = state

def pop_state():
    hist = session.get("chat_history", ["level_select"])
    if len(hist) > 1:
        hist.pop()
        session["chat_history"] = hist
    session["chat_state"] = hist[-1] if hist else "level_select"
    return session["chat_state"]


@app.route('/api/chat/options')
def chat_options():
    if not current_user.is_authenticated:
        return jsonify({'options': []})
    init_chat_state()
    state = session.get("chat_state", "level_select")
    lang = session.get('lang', 'ru')
    options = DIALOG_SCENARIOS.get(state, {}).get(lang, [])
    history = session.get("chat_history", [])
    if len(history) > 1:
        back_text = {"ru": "Назад", "kk": "Артқа", "en": "Back"}[lang]
        options = [back_text] + options
    return jsonify({"options": options})


@app.route('/api/chat', methods=['POST'])
def api_chat():
    if current_user.is_authenticated:
        init_chat_state()
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"reply": t("Пустое сообщение.")})

    msg = user_message.lower()
    lang = session.get('lang') or detect_language(user_message)

    # === ТВОЯ СТАРАЯ ЛОГИКА (полностью сохранена) ===
    free_question_variants = ["задать свой вопрос", "өз сұрауыңызды жіберіңіз",
                               "өз сұрағыңызды қою", "ask your question"]
    if msg.strip() in free_question_variants:
        hint = {"ru": "💬 Напишите ваш вопрос — я отвечу!",
                "kk": "💬 Сұрағыңызды жазыңыз — жауап беремін!",
                "en": "💬 Write your question — I'll answer it!"}
        return jsonify({"reply": hint.get(lang, hint["ru"]), "options": [], "markdown": False})

    if msg in ["назад", "артқа", "back", "◀ назад", "◀"]:
        current_state = pop_state()
        options = DIALOG_SCENARIOS.get(current_state, {}).get(lang, [])
        return jsonify({"reply": t("Вы вернулись назад."), "options": options,
                        "update_options": True, "markdown": True})

    # Level selection (бакалавриат, магистратура и т.д.)
    level_map = {
        "бакалавриат": "bachelor_menu", "магистратура": "master_menu",
        "докторантура": "doctorate_menu", "bachelor": "bachelor_menu",
        "master": "master_menu", "phd": "doctorate_menu", "doctorate": "doctorate_menu",
        "бакалавр": "bachelor_menu",
    }
    msg_clean = msg.strip().lower()
    for keyword, state in level_map.items():
        if keyword == msg_clean:
            push_state(state)
            options = DIALOG_SCENARIOS.get(state, {}).get(lang, [])
            return jsonify({"reply": t("Отлично! Вы выбрали раздел.") + "\n\n" + t("Выберите тему:"),
                            "options": options, "update_options": True, "markdown": True})

    # Submenu selection
    submenu_map = {
        "после 11 класса": "bachelor_after_school", "после колледжа": "bachelor_after_college",
        "после армии": "bachelor_after_army", "after school": "bachelor_after_school",
        "after college": "bachelor_after_college", "after army": "bachelor_after_army",
        "творческие программы": "bachelor_creative", "обычные программы": "bachelor_regular",
        "программы": "master_programs", "гранты": "master_grants",
        "требования": "doctorate_requirements",
    }
    for keyword, state in submenu_map.items():
        if keyword in msg:
            push_state(state)
            options = DIALOG_SCENARIOS.get(state, {}).get(lang, [])
            return jsonify({"reply": t("Вы выбрали:") + f" {user_message}\n\n" + t("Выберите вопрос:"),
                            "options": options, "update_options": True, "markdown": True})

    # === ТВОЙ СТАРЫЙ FAQ EXACT MATCH ===
    if FAQ_DATA:
        msg_lower = user_message.lower()
        for item in FAQ_DATA:
            keywords = [k.lower() for k in item.get("keywords", [])]
            if any(kw in msg_lower for kw in keywords):
                answer = item.get(f"answer_{lang}") or item.get("answer_ru", "Ответ временно недоступен.")
                if current_user.is_authenticated:
                    db.session.add(ChatHistory(user_id=current_user.id, message=user_message, response=answer))
                    db.session.commit()
                return jsonify({"reply": answer, "options": [], "markdown": True})

    # === НОВЫЙ RAG (Google File Search) ===
    try:
        file_search_tool = types.Tool(
            file_search=types.FileSearch(
                file_search_store_names=[FILE_SEARCH_STORE_NAME]
            )
        )

        system_prompt = f"""
        Ты — официальный ИИ-консультант приёмной комиссии университета им. К. Жубанова (Актобе).
        Отвечай только на языке вопроса пользователя ({lang.upper()}).
        Будь вежливым, точным и лаконичным.
        Используй только информацию из загруженных документов.
        Если точного ответа нет — честно скажи, что этой информации нет в базе или посоветуй обратиться в приёмную комиссию.
        """

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[user_message],
            config=types.GenerateContentConfig(
                tools=[file_search_tool],
                temperature=0.3,
                system_instruction=system_prompt,
            )
        )

        reply = response.text.strip() if hasattr(response, 'text') and response.text else "Извините, не удалось получить ответ."

        # Сохраняем в историю
        db.session.add(ChatHistory(
            user_id=current_user.id,
            message=user_message,
            response=reply
        ))
        db.session.commit()

        return jsonify({"reply": reply, "options": [], "markdown": True})

    except Exception as e:
        print("Gemini File Search Error:", str(e))
        fallback = {
            'ru': "Сервис временно недоступен. Попробуйте позже.",
            'kk': "Қызмет уақытша қолжетімсіз. Кейінірек көріңіз.",
            'en': "Service temporarily unavailable."
        }
        return jsonify({"reply": fallback.get(lang, fallback['ru']), "markdown": True})
    


@app.route('/api/chat/history')
@login_required
def chat_history():
    history = ChatHistory.query.filter_by(user_id=current_user.id).order_by(ChatHistory.timestamp).all()
    return jsonify([{"message": h.message, "response": h.response,
                     "timestamp": h.timestamp.strftime('%d.%m.%Y %H:%M')} for h in history])


# === INIT ===

def create_admin():
    admin = User.query.filter_by(email='admin@site.com').first()
    if not admin:
        admin = User(name='Администратор', email='admin@site.com', role='admin', language='ru')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("✅ Администратор создан")
    elif admin.role != 'admin':
        admin.role = 'admin'
        db.session.commit()

def create_staff():
    staff = User.query.filter_by(email='staff@site.com').first()
    
    if not staff:
        staff = User(
            name='Сотрудник Приёмной Комиссии',
            email='staff@site.com',
            role='staff',
            language='ru'
        )
        staff.set_password('staff123')   # ← пароль можно легко поменять
        db.session.add(staff)
        db.session.commit()
        print("✅ Создан Staff аккаунт: staff@site.com / staff123")
    else:
        if staff.role != 'staff':
            staff.role = 'staff'
            db.session.commit()
            print("✅ Роль пользователя staff@site.com обновлена на 'staff'")

def fix_existing_users():
    db.session.execute(db.text("""
        UPDATE "user" SET role = 'applicant' WHERE role IS NULL OR role = ''
    """))
    db.session.commit()

with app.app_context():
    db.create_all()
    create_admin()
    load_faq_exact()
    create_staff()          # ← добавь эту строку
    load_dialog_scenarios()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin()
        load_faq_exact()
        create_staff()          # ← добавь эту строку
        load_dialog_scenarios()
    app.run(debug=True)