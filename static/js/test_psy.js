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
  const recommendationsList = document.getElementById("recommendations-list");

  let questions = [];
  let currentIndex = 0;
  let answers = [];

  // === Загружаем вопросы с сервера ===
  fetch("/api/test/questions")
    .then((res) => res.json())
    .then((data) => {
      questions = data;
      showQuestion();
    })
    .catch(() => {
      questionText.textContent = "Ошибка загрузки теста 😞";
    });

  function showQuestion() {
    if (currentIndex >= questions.length) {
      finishTest();
      return;
    }

    const q = questions[currentIndex];
    questionText.textContent = q.text;
    optionsDiv.innerHTML = "";

    q.options.forEach((opt, i) => {
      const btn = document.createElement("button");
      btn.textContent = opt;
      if (answers[currentIndex] && answers[currentIndex].value === i + 1) {
        btn.classList.add("selected");
      }
      btn.addEventListener("click", () => {
        answers[currentIndex] = { id: q.id, value: i + 1 };
        // Переходим к следующему вопросу автоматически
        currentIndex++;
        if (currentIndex < questions.length) {
          showQuestion();
        } else {
          finishTest();
        }
      });
      optionsDiv.appendChild(btn);
    });

    progressDiv.textContent = `Вопрос ${currentIndex + 1} из ${questions.length}`;
    prevBtn.disabled = currentIndex === 0;
  }

  // Кнопка "Назад"
  prevBtn.addEventListener("click", () => {
    if (currentIndex > 0) {
      currentIndex--;
      showQuestion();
    }
  });

  // === Завершение теста и показ результата ===
  function finishTest() {
    container.style.display = "none";
    resultBox.style.display = "block";
    loadingText.style.display = "block";
    finalResult.style.display = "none";

    fetch("/api/test/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers }),
    })
      .then((res) => res.json())
      .then((data) => {
        loadingText.style.display = "none";
        finalResult.style.display = "block";

        mbtiType.textContent = `${data.mbti} — ${data.recommendations.title}`;
        description.textContent = data.recommendations.description;

        recommendationsList.innerHTML = "";
        if (data.recommendations.programs?.length > 0) {
          data.recommendations.programs.forEach((p) => {
            const li = document.createElement("li");
            li.textContent = p;
            recommendationsList.appendChild(li);
          });
        } else {
          recommendationsList.innerHTML = "<li>Рекомендации не найдены.</li>";
        }
      })
      .catch(() => {
        loadingText.textContent = "❌ Ошибка при сохранении результатов.";
      });
  }
});
