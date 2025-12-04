document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("test-container");
  const questionText = document.getElementById("question-text");
  const optionsDiv = document.getElementById("options");
  const progressDiv = document.getElementById("progress");
  const prevBtn = document.getElementById("prev-btn");
  const resultBox = document.getElementById("result-box");
  const loadingText = document.getElementById("loading-text");
  const finalResult = document.getElementById("final-result");
  const mbtiType = document.getElementById("mbti-type");
  const description = document.getElementById("description");
  const strengthsEl = document.getElementById("strengths");
  const professionsGrid = document.getElementById("professions-grid");

  let questions = [];
  let currentIndex = 0;
  let answers = [];

  fetch("/api/test/questions")
    .then(res => res.json())
    .then(data => {
      questions = data;
      answers = new Array(questions.length).fill(null);
      showQuestion();
    });

  function showQuestion() {
    if (currentIndex >= questions.length) {
      finishTest();
      return;
    }

    const q = questions[currentIndex];
    questionText.textContent = q.text || q.question;
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
        }, 250);
      };
      optionsDiv.appendChild(btn);
    });

    progressDiv.textContent = `Вопрос ${currentIndex + 1} из ${questions.length}`;
    prevBtn.disabled = currentIndex === 0;
  }

  prevBtn.onclick = () => {
    if (currentIndex > 0) {
      currentIndex--;
      showQuestion();
    }
  };

  function finishTest() {
    container.style.display = "none";
    resultBox.style.display = "block";
    loadingText.style.display = "block";
    finalResult.style.display = "none";

    fetch("/api/test/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers })
    })
    .then(res => res.json())
    .then(data => {
      loadingText.style.display = "none";
      finalResult.style.display = "block";

      const lang = document.documentElement.lang || 'ru';
      const rec = data.recommendations;

      // ← ЭТО ГЛАВНОЕ — теперь всё берётся правильно!
      mbtiType.textContent = rec.title || data.mbti;
      description.textContent = rec.description || "";
      strengthsEl.textContent = rec.strengths || "";

      // Радар-диаграмма
      const canvas = document.getElementById("radarChart");
      if (window.myRadar) window.myRadar.destroy();

      const p = rec.percentages || {};
      window.myRadar = new Chart(canvas.getContext("2d"), {
        type: "radar",
        data: {
          labels: ["E/I", "S/N", "T/F", "J/P"],
          datasets: [{
            data: [
              p.E || (100 - (p.I || 50)),
              p.S || (100 - (p.N || 50)),
              p.T || (100 - (p.F || 50)),
              p.J || (100 - (p.P || 50))
            ],
            backgroundColor: "rgba(255, 179, 15, 0.2)",
            borderColor: "#ffb30f",
            borderWidth: 3,
            pointBackgroundColor: "#ffb30f"
          }]
        },
        options: {
          scales: { r: { ticks: { display: false }, grid: { color: "rgba(255,255,255,0.1)" }, pointLabels: { color: "#fff" } } },
          plugins: { legend: { display: false } }
        }
      });

      // Профессии — карточки
      professionsGrid.innerHTML = "";
      const profs = rec.professions || [];
      if (profs.length === 0) {
        professionsGrid.innerHTML = "<p style='color:#aaa'>Рекомендаций нет</p>";
      } else {
        profs.forEach(p => {
          const card = document.createElement("div");
          card.className = "profession-card";
          card.innerHTML = `<h5>▸ ${p}</h5>`;
          professionsGrid.appendChild(card);
        });
      }
    })
    .catch(err => {
      console.error(err);
      loadingText.textContent = "Ошибка соединения";
    });
  }
});