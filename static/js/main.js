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
      ans.style.maxHeight = ans.style.maxHeight ? null : ans.scrollHeight + 'px';
    });
  });

  // Калькулятор баллов
  const calcForm = document.querySelector('.calculator-form');
  if (calcForm) {
    calcForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const inputs = calcForm.querySelectorAll('input[type="number"]');
      const sum = Array.from(inputs).reduce((acc, i) => acc + (Number(i.value) || 0), 0);
      const res = calcForm.querySelector('.calc-result');
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
      } catch {
        out.textContent = 'Ошибка проверки статуса';
      }
    });
  }

  // Контактная форма (AJAX)
  const contactForm = document.querySelector('.contact-form, #contactForm');
  if (contactForm) {
    contactForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = e.target;
      const name = form.querySelector('[name="name"]')?.value || '';
      const email = form.querySelector('[name="email"]')?.value || '';
      const message = form.querySelector('[name="message"]')?.value || '';
      const btn = form.querySelector('button');
      if (btn) btn.disabled = true;

      try {
        const resp = await fetch('/api/contact', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, email, message })
        });
        const data = await resp.json();
        const resultBlock = document.getElementById('formResult');
        if (resultBlock) resultBlock.textContent = data.message || 'Отправлено';
        else alert(data.message || 'Отправлено');
        if (data.status === 'ok') form.reset();
      } catch {
        alert('Ошибка отправки');
      } finally {
        if (btn) btn.disabled = false;
      }
    });
  }

  // Анимация появления элементов на странице контактов
  const animatedElements = document.querySelectorAll(
    '.contact-title, .contact-details, .contact-form'
  );
  if (animatedElements.length > 0) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) entry.target.classList.add('fade-in-up');
      });
    }, { threshold: 0.1 });

    animatedElements.forEach(el => observer.observe(el));
  }

  // === Панель уведомлений ===
  const notifBtn = document.getElementById("notifBtn");
  const notifPanel = document.getElementById("notifPanel");
  const closeNotif = document.getElementById("closeNotif");
  const overlay = document.getElementById("overlay");

  if (notifBtn && notifPanel && closeNotif && overlay) {
    notifBtn.addEventListener("click", (e) => {
      e.preventDefault();
      notifPanel.classList.add("active");
      overlay.classList.add("active");

      // 👇 Убираем бейдж при открытии панели
      const badge = notifBtn.querySelector(".notif-badge");
      if (badge) badge.style.display = "none";
    });

    const closePanel = () => {
      notifPanel.classList.remove("active");
      overlay.classList.remove("active");
    };

    closeNotif.addEventListener("click", closePanel);
    overlay.addEventListener("click", closePanel);
  }

});

// Прозрачность шапки при скролле
window.addEventListener('scroll', () => {
  const header = document.querySelector('.site-header');
  if (!header) return;
  header.classList.toggle('scrolled', window.scrollY > 50);
});
