document.addEventListener("DOMContentLoaded", function() {
    const form = document.getElementById("testForm");
    const progress = document.getElementById("progress");
    const resultDiv = document.getElementById("test-result");
    const totalQuestions = parseInt(form.dataset.total);
    const lang = form.dataset.lang;

    function getProgressText(answered) {
        if (lang === "kk") return `Сұрақтар: ${answered}/${totalQuestions}`;
        if (lang === "en") return `Questions: ${answered}/${totalQuestions}`;
        return `Вопросы: ${answered}/${totalQuestions}`;
    }

    window.updateProgress = function() {
        const sliders = document.querySelectorAll(".slider");
        let answered = 0;
        sliders.forEach(slider => {
            if (parseInt(slider.value) !== 4) answered++;
        });
        progress.innerText = getProgressText(answered);
    }

    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();

            const answers = [];
            const sliders = document.querySelectorAll(".slider");
            sliders.forEach(slider => {
                const qid = parseInt(slider.name.split("_")[1]);
                answers.push({ id: qid, value: parseInt(slider.value) });
            });

            try {
                const response = await fetch("/api/test/personality-submit", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ answers })
                });
                const result = await response.json();

                if (result.mbti) {
                    if (lang === "kk") {
                        resultDiv.innerHTML = `
                            <p>Сіздің типіңіз: ${result.mbti}</p>
                            <p>Ұсыныстар: ${result.recommendations}</p>
                        `;
                    } else if (lang === "en") {
                        resultDiv.innerHTML = `
                            <p>Your type: ${result.mbti}</p>
                            <p>Recommendations: ${result.recommendations}</p>
                        `;
                    } else {
                        resultDiv.innerHTML = `
                            <p>Ваш тип: ${result.mbti}</p>
                            <p>Рекомендации: ${result.recommendations}</p>
                        `;
                    }
                } else {
                    resultDiv.textContent = lang === "kk"
                        ? "Қате"
                        : lang === "en"
                        ? "Error"
                        : "Ошибка";
                }
            } catch (err) {
                resultDiv.textContent = "Network error";
            }
        });
    }
});
