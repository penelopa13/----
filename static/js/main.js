// static/js/main.js
document.addEventListener('DOMContentLoaded', () => {
  // Навигация (бургер-меню)
  const toggle = document.getElementById('nav-toggle');
  const nav = document.getElementById('nav');
  if (toggle && nav) {
    toggle.addEventListener('click', () => nav.classList.toggle('open'));
  }

  // FAQ (аккордеон)
  document.querySelectorAll('.faq-question').forEach(btn => {
    btn.addEventListener('click', () => {
      const ans = btn.nextElementSibling;
      btn.classList.toggle('active');
      if (ans.style.maxHeight) {
        ans.style.maxHeight = null;
      } else {
        ans.style.maxHeight = ans.scrollHeight + "px";
      }
    });
  });

  // Чат-бот
  const chatForm = document.getElementById('chat-form');
  if (chatForm) {
    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const input = document.getElementById('user-input');
      const messages = document.getElementById('messages');
      const userMsg = input.value.trim();
      if (!userMsg) return;
      messages.innerHTML += `<div class="message user">${userMsg}</div>`;
      input.value = '';
      try {
        const res = await fetch('/api/ai_chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: userMsg })
        });
        const data = await res.json();
        messages.innerHTML += `<div class="message bot">${data.reply}</div>`;
        messages.scrollTop = messages.scrollHeight;
      } catch (err) {
        messages.innerHTML += `<div class="message bot">Ошибка связи с ИИ</div>`;
        messages.scrollTop = messages.scrollHeight;
      }
    });

    // Голосовой ввод
    const voiceBtn = document.getElementById('voice-btn');
    if (voiceBtn) {
      const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
      recognition.lang = document.documentElement.lang || 'ru-RU';
      recognition.onresult = (event) => {
        document.getElementById('user-input').value = event.results[0][0].transcript;
      };
      voiceBtn.addEventListener('click', () => recognition.start());
    }
  }

  // Калькулятор баллов
  const calcForm = document.getElementById('calcForm');
  if (calcForm) {
    calcForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const vals = [
        parseFloat(calcForm.val1.value) || 0,
        parseFloat(calcForm.val2.value) || 0,
        parseFloat(calcForm.val3.value) || 0
      ];
      const result = document.getElementById('calcResult');
      try {
        const res = await fetch('/api/calc', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ vals })
        });
        const data = await res.json();
        result.textContent = `Общий балл: ${data.total}. ${data.message}`;
      } catch (err) {
        result.textContent = 'Ошибка расчёта';
      }
    });
  }

  // Проверка статуса заявки
  const statusForm = document.querySelector('.status-form');
  if (statusForm) {
    statusForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const input = statusForm.querySelector('input').value.trim();
      const result = document.querySelector('.status-result');
      if (!input) {
        result.textContent = 'Введите номер заявки или email';
        return;
      }
      result.textContent = 'Проверка...';
      try {
        const res = await fetch(`/api/status?q=${encodeURIComponent(input)}`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` }
        });
        if (res.status === 401) {
          result.textContent = 'Пожалуйста, войдите в систему';
          setTimeout(() => window.location.href = '/login', 2000);
          return;
        }
        const data = await res.json();
        result.textContent = data.message || `Статус: ${data.status} (Создано: ${data.created_at})`;
      } catch (err) {
        result.textContent = 'Ошибка проверки статуса';
      }
    });
  }

  // Контактная форма
  const contactForm = document.getElementById('contactForm');
  if (contactForm) {
    contactForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = contactForm.querySelector('input[name="name"]').value;
      const email = contactForm.querySelector('input[name="email"]').value;
      const message = contactForm.querySelector('textarea').value;
      const result = document.getElementById('formResult');
      const btn = contactForm.querySelector('button');
      btn.disabled = true;
      try {
        const res = await fetch('/api/contact', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, email, message })
        });
        const data = await res.json();
        result.textContent = data.message;
        if (data.status === 'ok') contactForm.reset();
      } catch (err) {
        result.textContent = 'Ошибка отправки';
      } finally {
        btn.disabled = false;
      }
    });
  }
});

// Прозрачность шапки при скролле
window.addEventListener('scroll', () => {
  const header = document.querySelector('.site-header');
  if (header) {
    if (window.scrollY > 50) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }
  }
});