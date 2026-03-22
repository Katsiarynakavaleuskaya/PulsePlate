"""Legacy embedded BMI calculator HTML (historically served at ``GET /``)."""

from __future__ import annotations

from fastapi.responses import HTMLResponse
from starlette.requests import Request


def render_legacy_bmi_calculator_page(request: Request) -> HTMLResponse:
    """Serve the standalone HTML BMI form with CSP nonce slots when middleware sets them."""
    nonce = getattr(request.state, "csp_nonce", "")
    nonce_attr = f' nonce="{nonce}"' if nonce else ""

    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>BMI Calculator</title>
        <style{nonce_attr}>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;
                   padding: 20px; }
            form { margin-bottom: 20px; }
            input, button, select { display: block; margin: 10px 0; padding: 10px; width: 100%; }
            .result { margin-top: 20px; padding: 10px; border: 1px solid #ccc; }
            .language-selector { position: absolute; top: 20px; right: 20px; }
        </style>
    </head>
    <body>
        <div class="language-selector">
            <label for="language">Language:</label>
            <select id="language">
                <option value="en">English</option>
                <option value="ru">Русский</option>
                <option value="es">Español</option>
            </select>
        </div>

        <h1 id="title">BMI Calculator</h1>
        <form id="bmiForm">
            <label for="weight" id="label_weight">Weight (kg):</label>
            <input type="number" id="weight" step="0.1" required>

            <label for="height" id="label_height">Height (m):</label>
            <input type="number" id="height" step="0.01" required>

            <label for="age" id="label_age">Age:</label>
            <input type="number" id="age" required>

            <label for="gender" id="label_gender">Gender:</label>
            <select id="gender" required>
                <option value="male" id="option_male">Male</option>
                <option value="female" id="option_female">Female</option>
            </select>

            <label for="pregnant" id="label_pregnant">Pregnant:</label>
            <select id="pregnant">
                <option value="no" id="option_pregnant_no">No</option>
                <option value="yes" id="option_pregnant_yes">Yes</option>
            </select>

            <label for="athlete" id="label_athlete">Athlete:</label>
            <select id="athlete">
                <option value="no" id="option_athlete_no">No</option>
                <option value="yes" id="option_athlete_yes">Yes</option>
            </select>

            <label for="waist" id="label_waist">Waist (cm, optional):</label>
            <input type="number" id="waist" step="0.1">

            <button type="submit" id="button_calculate">Calculate BMI</button>
        </form>

        <div id="result" class="result" style="display:none;"></div>

        <script{nonce_attr}>
            // Language translations
            const translations = {
                en: {
                    title: "BMI Calculator",
                    result_bmi: "BMI",
                    result_category: "Category",
                    result_note: "Note",
                    result_error: "Error calculating BMI",
                    label_weight: "Weight (kg):",
                    label_height: "Height (m):",
                    label_age: "Age:",
                    label_gender: "Gender:",
                    option_male: "Male",
                    option_female: "Female",
                    label_pregnant: "Pregnant:",
                    option_pregnant_no: "No",
                    option_pregnant_yes: "Yes",
                    label_athlete: "Athlete:",
                    option_athlete_no: "No",
                    option_athlete_yes: "Yes",
                    label_waist: "Waist (cm, optional):",
                    button_calculate: "Calculate BMI"
                },
                ru: {
                    title: "Калькулятор ИМТ",
                    result_bmi: "ИМТ",
                    result_category: "Категория",
                    result_note: "Примечание",
                    result_error: "Ошибка расчёта ИМТ",
                    label_weight: "Вес (кг):",
                    label_height: "Рост (м):",
                    label_age: "Возраст:",
                    label_gender: "Пол:",
                    option_male: "Мужской",
                    option_female: "Женский",
                    label_pregnant: "Беременность:",
                    option_pregnant_no: "Нет",
                    option_pregnant_yes: "Да",
                    label_athlete: "Спортсмен:",
                    option_athlete_no: "Нет",
                    option_athlete_yes: "Да",
                    label_waist: "Талия (см, опционально):",
                    button_calculate: "Рассчитать ИМТ"
                },
                es: {
                    title: "Calculadora de IMC",
                    result_bmi: "IMC",
                    result_category: "Categoría",
                    result_note: "Nota",
                    result_error: "Error al calcular el IMC",
                    label_weight: "Peso (kg):",
                    label_height: "Altura (m):",
                    label_age: "Edad:",
                    label_gender: "Género:",
                    option_male: "Masculino",
                    option_female: "Femenino",
                    label_pregnant: "Embarazada:",
                    option_pregnant_no: "No",
                    option_pregnant_yes: "Sí",
                    label_athlete: "Atleta:",
                    option_athlete_no: "No",
                    option_athlete_yes: "Sí",
                    label_waist: "Cintura (cm, opcional):",
                    button_calculate: "Calcular IMC"
                }
            };

            const ALLOWED_LANGS = new Set(['en', 'ru', 'es']);

            /** Allowlist URL/cookie lang to prevent cookie injection / odd payloads. */
            function normalizeLang(raw) {
                const code = String(raw || '').trim().toLowerCase();
                return ALLOWED_LANGS.has(code) ? code : 'en';
            }

            // Set language from cookie or URL parameter
            function getLanguage() {
                const urlParams = new URLSearchParams(window.location.search);
                if (urlParams.has('lang')) {
                    return normalizeLang(urlParams.get('lang'));
                }
                const cookies = document.cookie.split(';');
                for (let cookie of cookies) {
                    const [name, value] = cookie.trim().split('=');
                    if (name === 'lang') {
                        return normalizeLang(value);
                    }
                }
                return 'en';
            }

            // Update UI based on selected language
            function updateUILanguage(lang) {
                const langCode = normalizeLang(lang);
                const t = translations[langCode];

                // Update text elements
                document.getElementById('title').textContent = t.title;
                document.getElementById('label_weight').textContent = t.label_weight;
                document.getElementById('label_height').textContent = t.label_height;
                document.getElementById('label_age').textContent = t.label_age;
                document.getElementById('label_gender').textContent = t.label_gender;
                document.getElementById('option_male').textContent = t.option_male;
                document.getElementById('option_female').textContent = t.option_female;
                document.getElementById('label_pregnant').textContent = t.label_pregnant;
                document.getElementById('option_pregnant_no').textContent = t.option_pregnant_no;
                document.getElementById('option_pregnant_yes').textContent = t.option_pregnant_yes;
                document.getElementById('label_athlete').textContent = t.label_athlete;
                document.getElementById('option_athlete_no').textContent = t.option_athlete_no;
                document.getElementById('option_athlete_yes').textContent = t.option_athlete_yes;
                document.getElementById('label_waist').textContent = t.label_waist;
                document.getElementById('button_calculate').textContent = t.button_calculate;

                // Set language selector
                document.getElementById('language').value = langCode;
            }

            // Set language selector based on current language
            const currentLang = getLanguage();
            updateUILanguage(currentLang);
            document.getElementById('language').addEventListener('change', changeLanguage);

            // Change language function
            function changeLanguage() {
                const lang = normalizeLang(document.getElementById('language').value);
                // Set cookie
                // Security: add SameSite and conditionally Secure under HTTPS.
                // RU: HttpOnly нельзя выставить из JS — это должен делать сервер.
                // EN: HttpOnly cannot be set from client-side JS; server must set it.
                const cookieAttrs = `; path=/; SameSite=Lax${window.location.protocol === 'https:' ? '; Secure' : ''}`;
                document.cookie = `lang=${lang}${cookieAttrs}`;
                // Update UI
                updateUILanguage(lang);
            }

            function showBmiResult(result) {
                const langCode = normalizeLang(getLanguage());
                const t = translations[langCode];
                const box = document.getElementById('result');
                box.replaceChildren();
                box.style.display = 'block';
                const h2 = document.createElement('h2');
                h2.textContent = `${t.result_bmi}: ${result.bmi}`;
                const pCat = document.createElement('p');
                pCat.textContent = `${t.result_category}: ${result.category ?? ''}`;
                const pNote = document.createElement('p');
                pNote.textContent = `${t.result_note}: ${result.note ?? ''}`;
                box.append(h2, pCat, pNote);
            }

            function showBmiError() {
                const langCode = normalizeLang(getLanguage());
                const t = translations[langCode];
                const box = document.getElementById('result');
                box.replaceChildren();
                const p = document.createElement('p');
                p.textContent = t.result_error;
                box.append(p);
                box.style.display = 'block';
            }

            document.getElementById('bmiForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const lang = getLanguage();
                const data = {
                    weight_kg: parseFloat(document.getElementById('weight').value),
                    height_m: parseFloat(document.getElementById('height').value),
                    age: parseInt(document.getElementById('age').value),
                    gender: document.getElementById('gender').value,
                    pregnant: document.getElementById('pregnant').value,
                    athlete: document.getElementById('athlete').value,
                    waist_cm: document.getElementById('waist').value ?
                              parseFloat(document.getElementById('waist').value) : null,
                    lang: lang
                };

                try {
                    const response = await fetch('/bmi', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    const result = await response.json();
                    showBmiResult(result);
                } catch (error) {
                    showBmiError();
                }
            });
        </script>
    </body>
    </html>
    """
    html_content = html_template.replace("{nonce_attr}", nonce_attr)
    return HTMLResponse(content=html_content)
