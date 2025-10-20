document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("testForm");
    const resultBox = document.getElementById("resultBox");
    const resultText = document.getElementById("resultText");

    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        const sliders = document.querySelectorAll(".answer-slider");
        const answers = Array.from(sliders).map(slider => ({
            category: slider.dataset.category,
            value: parseInt(slider.value)
        }));

        const response = await fetch("/api/test/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ answers })
        });

        const data = await response.json();

        if (data.recommendations) {
            resultText.textContent = data.recommendations;
            resultBox.style.display = "block";
            window.scrollTo({ top: resultBox.offsetTop, behavior: "smooth" });
        } else {
            alert("Ошибка при обработке теста");
        }
    });
});
