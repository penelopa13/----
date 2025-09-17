import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///dev.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    message = db.Column(db.Text)

# Зарузка пользователя
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Основные страницы ---
@app.route('/')
def home(): return render_template('index.html')

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


# --- Auth routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким Email уже существует', 'error')
            return redirect(url_for('register'))
        u = User(name=name, email=email)
        u.set_password(password)  # РЕКОМЕНДУЮ ХЕШИРОВАТЬ
        db.session.add(u); db.session.commit()
        flash('Регистрация прошла успешно. Войдите в систему.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email'); pw = request.form.get('password')
        u = User.query.filter_by(email=email).first()
        if u and u.check_password(pw):
            login_user(u)
            return redirect(url_for('home'))
        flash('Неверный логин или пароль', 'error')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# --- API endpoints (AJAX) ---
@app.route('/api/status')
def api_status():
    q = request.args.get('q', '')
    # Здесь нужно подключение к вашей CRM/таблице заявок. Пока заглушка:
    if q == '':
        return jsonify({'message': 'Введите номер заявки или Email'}), 400
    # Пример заглушки
    return jsonify({'message': f'Статус для "{q}": Заявка принята, ожидает проверки.'})

@app.route('/api/contact', methods=['POST'])
def api_contact():
    data = request.get_json() or {}
    name = data.get('name'); email = data.get('email'); message = data.get('message')
    if not (name and email and message):
        return jsonify({'status':'error','message':'Заполните все поля'}), 400
    cm = ContactMessage(name=name, email=email, message=message)
    db.session.add(cm); db.session.commit()
    return jsonify({'status':'ok','message':'Спасибо, мы свяжемся с вами.'})

# Optional: калькулятор (server-side)
@app.route('/api/calc', methods=['POST'])
def api_calc():
    data = request.get_json() or {}
    vals = data.get('vals', [])
    total = sum([float(v or 0) for v in vals])
    return jsonify({'total': total})

# Stub для OpenAI (позже интегрируешь)
@app.route('/api/ai_chat', methods=['POST'])
def ai_chat():
    # Прим.: храните OPENAI_API_KEY в .env и используйте openai python SDK на сервере
    return jsonify({'reply': 'Это заглушка AI. Интеграция OpenAI здесь.'})

if __name__ == '__main__':
    # Создать таблицы (только при dev)
    with app.app_context():
        db.create_all()
    app.run(debug=True)
