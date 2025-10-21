document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("test-container");
  const questionText = document.getElementById("question-text");
  const optionsDiv = document.getElementById("options");
  const progressDiv = document.getElementById("progress");
  const nextBtn = document.getElementById("next-btn");
  const resultBox = document.getElementById("result-box");

  let questions = [];
  let currentIndex = 0;
  let answers = [];

  // Загружаем вопросы с сервера
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
      btn.addEventListener("click", () => selectOption(i + 1, btn));
      optionsDiv.appendChild(btn);
    });

    progressDiv.textContent = `Question ${currentIndex + 1} / ${questions.length}`;
    nextBtn.disabled = true;
  }

  function selectOption(value, button) {
    document.querySelectorAll(".options button").forEach((b) => b.classList.remove("selected"));
    button.classList.add("selected");
    answers[currentIndex] = { id: questions[currentIndex].id, value };
    nextBtn.disabled = false;
  }

  nextBtn.addEventListener("click", () => {
    currentIndex++;
    showQuestion();
  });

  function finishTest() {
    container.style.display = "none";
    resultBox.style.display = "block";

    fetch("/api/test/personality-submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers }),
    })
      .then((res) => res.json())
      .then((data) => {
        resultBox.innerHTML = `
          <h2>🎯 Your MBTI Type: ${data.mbti}</h2>
          <p>${data.recommendations}</p>
          <a href="/profile" class="btn orange mt-3">Go to Profile</a>
        `;
      })
      .catch(() => {
        resultBox.innerHTML = "<p>❌ Error saving results.</p>";
      });
  }
});
