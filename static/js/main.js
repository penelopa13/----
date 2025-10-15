// Ждём загрузки документа
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

  // Калькулятор баллов
  const calcForm = document.querySelector('.calculator-form');
  if (calcForm) {
    calcForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const inputs = calcForm.querySelectorAll('input[type="number"]');
      let sum = 0;
      inputs.forEach(i => sum += Number(i.value) || 0);
      const res = calcForm.querySelector('.calc-result') || document.querySelector('.calc-result');
      if (res) res.textContent = `Итоговые баллы: ${sum}`;
    });
  }

  // Проверка статуса заявки (AJAX)
  const statusForm = document.querySelector('.status-form');
  if (statusForm) {
    statusForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const q = statusForm.querySelector('input').value.trim();
      const out = document.querySelector('.status-result');
      if (!out) return;
      out.textContent = 'Проверка...';
      try {
        const resp = await fetch('/api/status?q=' + encodeURIComponent(q));
        const data = await resp.json();
        out.textContent = data.message || 'Нет данных';
      } catch (err) {
        out.textContent = 'Ошибка проверки статуса';
      }
    });
  }

  // Контактная форма (AJAX)
  const contactForm = document.querySelector('.contact-form');
  if (contactForm) {
    contactForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = contactForm.querySelector('input[type="text"]').value;
      const email = contactForm.querySelector('input[type="email"]').value;
      const message = contactForm.querySelector('textarea').value;
      const btn = contactForm.querySelector('button');
      btn.disabled = true;
      try {
        const resp = await fetch('/api/contact', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ name, email, message })
        });
        const d = await resp.json();
        alert(d.status || 'Отправлено');
      } catch (err) {
        alert('Ошибка отправки');
      } finally {
        btn.disabled = false;
      }
    });
  }
});

// Прозрачность шапки при скролле
window.addEventListener('scroll', () => {
  const header = document.querySelector('.site-header');
  if (!header) return;

  if (window.scrollY > 50) {
    // При скролле делаем более прозрачным
    header.classList.add('scrolled');
  } else {
    // Вверху страницы — тёмный фон
    header.classList.remove('scrolled');
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const elements = document.querySelectorAll(
    ".contact-title, .contact-details, .contact-form"
  );

  const observer = new IntersectionObserver(
    entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add("fade-in-up");
        }
      });
    },
    { threshold: 0.1 }
  );

  elements.forEach(el => observer.observe(el));
});

document.getElementById('contactForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const data = {
    name: form.name.value,
    email: form.email.value,
    message: form.message.value
  };
  const res = await fetch('/api/contact', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  const result = await res.json();
  document.getElementById('formResult').textContent = result.message;
  if(result.status === 'ok') form.reset();
});