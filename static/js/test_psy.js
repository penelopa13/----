document.addEventListener("DOMContentLoaded", () => {

  // === ЭЛЕМЕНТЫ ===
  const testContainer = document.getElementById("test-container");
  const finalResult = document.getElementById("final-result");

  const mbtiTypeEl = document.getElementById("mbti-type");
  const descriptionEl = document.getElementById("description");
  const strengthsEl = document.getElementById("strengths");
  const professionsGrid = document.getElementById("professions-grid");

  let questions = [];
  let currentIndex = 0;
  let answers = [];
  let radarChart = null;

  // Если результат уже есть (от бэкенда)
  if (finalResult && finalResult.style.display !== "none") {
    initImprovedRadarChart();
    return;
  }

  // === ЗАПУСК ТЕСТА ===
  fetch("/api/test/questions")
    .then(res => res.json())
    .then(data => {
      questions = data;
      answers = new Array(questions.length).fill(null);
      showQuestion();
    })
    .catch(err => console.error("Ошибка загрузки вопросов:", err));

  function showQuestion() {
    if (currentIndex >= questions.length) {
      finishTest();
      return;
    }

    const q = questions[currentIndex];
    document.getElementById("question-text").textContent = q.text || q.question;

    const optionsDiv = document.getElementById("options");
    optionsDiv.innerHTML = "";

    q.options.forEach((opt, i) => {
      const btn = document.createElement("button");
      btn.textContent = opt;
      if (answers[currentIndex] === i + 1) btn.classList.add("selected");

      btn.onclick = () => {
        answers[currentIndex] = i + 1;
        document.querySelectorAll("#options button").forEach(b => b.classList.remove("selected"));
        btn.classList.add("selected");

        setTimeout(() => {
          currentIndex++;
          showQuestion();
        }, 280);
      };
      optionsDiv.appendChild(btn);
    });

    document.getElementById("progress").textContent = `Вопрос ${currentIndex + 1} из ${questions.length}`;
    document.getElementById("prev-btn").disabled = currentIndex === 0;
  }

  document.getElementById("prev-btn").onclick = () => {
    if (currentIndex > 0) {
      currentIndex--;
      showQuestion();
    }
  };

  function finishTest() {
    testContainer.style.display = "none";
    if (finalResult) finalResult.style.display = "block";

    fetch("/api/test/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers })
    })
    .then(res => res.json())
    .then(data => {
      const rec = data.recommendations || {};

      if (mbtiTypeEl) mbtiTypeEl.textContent = rec.title || data.mbti || "—";
      if (descriptionEl) descriptionEl.textContent = rec.description || "";
      if (strengthsEl) strengthsEl.innerHTML = rec.strengths || "—";

      // Профессии
      if (professionsGrid) {
        professionsGrid.innerHTML = "";
        (rec.professions || []).forEach(prof => {
          const card = document.createElement("div");
          card.className = "profession-card";
          card.innerHTML = `<h5>▸ ${prof}</h5>`;
          professionsGrid.appendChild(card);
        });
      }

      // ← УЛУЧШЕННЫЙ РАДАР
      initImprovedRadarChart(rec.percentages || {});

    })
    .catch(err => console.error("Ошибка отправки теста:", err));
  }

  // ====================== УЛУЧШЕННАЯ РАДАРНАЯ ДИАГРАММА ======================
  function initImprovedRadarChart(percentages = {}) {
    const canvas = document.getElementById("radarChart");
    if (!canvas) return;

    if (radarChart) radarChart.destroy();

    // Подготовка данных (E/I, S/N, T/F, J/P)
    const data = {
      labels: [
        "Экстраверсия (E)", 
        "Интуиция (N)", 
        "Мышление (T)", 
        "Планирование (J)"
      ],
      datasets: [{
        label: "Ваш уровень",
        data: [
          percentages.E || 50,
          percentages.N || 50,
          percentages.T || 50,
          percentages.J || 50
        ],
        backgroundColor: "rgba(255, 179, 15, 0.28)",
        borderColor: "#ffb30f",
        borderWidth: 4,
        pointBackgroundColor: "#ffffff",
        pointBorderColor: "#ffb30f",
        pointBorderWidth: 2,
        pointHoverRadius: 8,
        pointHoverBorderWidth: 3
      }]
    };

    radarChart = new Chart(canvas, {
      type: "radar",
      data: data,
      options: {
        maintainAspectRatio: true,
        aspectRatio: 1.1,

        scales: {
          r: {
            min: 0,
            max: 100,
            stepSize: 20,
            ticks: {
              color: "#bbbbbb",
              font: { size: 12 },
              backdropColor: "transparent"
            },
            grid: {
              color: "rgba(255, 255, 255, 0.15)"
            },
            angleLines: {
              color: "rgba(255, 255, 255, 0.18)"
            },
            pointLabels: {
              color: "#eeeeee",
              font: {
                size: 14,
                weight: "500"
              },
              padding: 15
            }
          }
        },

        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: "rgba(15, 23, 42, 0.95)",
            titleColor: "#ffb30f",
            bodyColor: "#ddd",
            borderColor: "#ffb30f",
            borderWidth: 1,
            padding: 12,
            displayColors: false,
            callbacks: {
              label: (context) => ` ${context.raw}%`
            }
          }
        },

        animation: {
          duration: 1200,
          easing: "easeOutQuart"
        }
      }
    });
  }

});