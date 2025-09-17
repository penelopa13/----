// nav toggle
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('nav-toggle');
  const nav = document.getElementById('nav');
  toggle.addEventListener('click', () => nav.classList.toggle('open'));

  // FAQ accordion
  document.querySelectorAll('.faq-question').forEach(btn => {
    btn.addEventListener('click', () => {
      const ans = btn.nextElementSibling;
      btn.classList.toggle('active');
      if (ans.style.maxHeight) ans.style.maxHeight = null;
      else ans.style.maxHeight = ans.scrollHeight + "px";
    });
  });

  // Calculator (if exists)
  const calcForm = document.querySelector('.calculator-form');
  if (calcForm) {
    calcForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const inputs = calcForm.querySelectorAll('input[type="number"]');
      let sum = 0;
      inputs.forEach(i => sum += Number(i.value) || 0);
      const res = calcForm.querySelector('.calc-result') || document.querySelector('.calc-result');
      res.textContent = `Итоговые баллы: ${sum}`;
      // Можно отправить на сервер через fetch если нужно
    });
  }

  // Status check (AJAX)
  const statusForm = document.querySelector('.status-form');
  if (statusForm) {
    statusForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const q = statusForm.querySelector('input').value.trim();
      const out = document.querySelector('.status-result');
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

  // Contact form (AJAX)
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
          body: JSON.stringify({name, email, message})
        });
        const d = await resp.json();
        alert(d.status || 'Отправлено');
      } catch (err) {
        alert('Ошибка отправки');
      } finally { btn.disabled = false; }
    });
  }
});
