from flask import Flask, render_template_string, jsonify
import json
import random
import re

app = Flask(__name__)

# --------------------------------------------------
# LOAD YOUR SAT VOCABULARY
# --------------------------------------------------

with open("sat_words_clean.json", "r", encoding="utf-8") as f:
    words = json.load(f)

# Only keep word + meaning.
# Example sentences are completely ignored.
vocab = []

for item in words:
    word = str(item.get("word", "")).strip()
    meaning = str(item.get("meaning", "")).strip()

    if word and meaning:
        vocab.append({
            "word": word,
            "meaning": meaning
        })

print(f"Loaded {len(vocab)} words")


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def normalize(text):
    """Make meanings easier to compare."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def meaning_tokens(text):
    """Return useful words from a meaning."""
    stopwords = {
        "to", "a", "an", "the", "of", "and", "or",
        "for", "in", "on", "with", "by", "someone",
        "something", "one", "that", "as", "from"
    }

    return {
        word for word in normalize(text).split()
        if len(word) > 2 and word not in stopwords
    }


def meanings_too_similar(meaning1, meaning2):
    """
    Prevent obviously similar meanings from appearing
    together as answer choices.
    """

    a = meaning_tokens(meaning1)
    b = meaning_tokens(meaning2)

    if not a or not b:
        return False

    overlap = len(a & b)
    smaller = min(len(a), len(b))

    # If most of the important words overlap,
    # consider the meanings too similar.
    if smaller > 0 and overlap / smaller >= 0.6:
        return True

    # Catch a few particularly obvious synonym relationships.
    synonym_groups = [
        {"reduce", "lessen", "decrease", "diminish"},
        {"hate", "detest", "abhor", "dislike"},
        {"praise", "approval", "approbation"},
        {"attack", "assail"},
        {"calm", "appease", "pacify"},
        {"understand", "perceive", "grasp"},
        {"wealthy", "rich", "affluent"},
        {"friendly", "amiable", "amicable"},
        {"dry", "arid"},
        {"old", "outdated", "archaic", "antiquated"},
        {"secret", "obscure", "arcane"},
        {"hardworking", "diligent", "assiduous"},
    ]

    for group in synonym_groups:
        if (a & group) and (b & group):
            return True

    return False


def make_question():
    """
    Create one question:
        question = definition
        answer = word
        choices = 4 words
    """

    answer = random.choice(vocab)

    # Start with the correct answer.
    choices = [answer]

    # Shuffle candidates so distractors are random.
    candidates = vocab.copy()
    random.shuffle(candidates)

    for candidate in candidates:

        # Don't use the answer again.
        if candidate["word"].lower() == answer["word"].lower():
            continue

        # Don't use duplicate words.
        if any(
            candidate["word"].lower() == c["word"].lower()
            for c in choices
        ):
            continue

        # Avoid another choice with essentially the same meaning.
        if meanings_too_similar(
            candidate["meaning"],
            answer["meaning"]
        ):
            continue

        # Also compare against existing distractors.
        too_similar = False

        for existing in choices[1:]:
            if meanings_too_similar(
                candidate["meaning"],
                existing["meaning"]
            ):
                too_similar = True
                break

        if too_similar:
            continue

        choices.append(candidate)

        if len(choices) == 4:
            break

    # Extremely unlikely fallback.
    # If similarity filtering couldn't find enough,
    # fill the remaining choices with random words.
    if len(choices) < 4:
        for candidate in candidates:
            if candidate not in choices:
                choices.append(candidate)

            if len(choices) == 4:
                break

    random.shuffle(choices)

    return {
        "meaning": answer["meaning"],
        "answer": answer["word"],
        "choices": [x["word"] for x in choices]
    }


# --------------------------------------------------
# MAIN PAGE
# --------------------------------------------------

HTML = """
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>SAT Vocabulary Quiz</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    min-height: 100vh;

    font-family: "Segoe UI", Arial, sans-serif;

    background: #b0d5cd;

    display: flex;
    justify-content: center;
    align-items: center;

    color: #183c40;
}

.container {
    width: min(720px, 92%);

    background: #fffaf0;

    border-radius: 20px;

    padding: 42px;

    box-shadow:
        0 10px 35px rgba(24, 60, 64, 0.15);
}

h1 {
    margin: 0 0 35px 0;

    font-family: Georgia, serif;

    font-size: 30px;

    text-align: center;

    color: #183c40;
}

.question {
    font-family: Georgia, serif;

    font-size: 25px;

    line-height: 1.45;

    text-align: center;

    margin-bottom: 30px;

    color: #183c40;
}

.options {
    display: flex;
    flex-direction: column;

    gap: 13px;
}

.option {
    width: 100%;

    padding: 17px 20px;

    background: #fffaf0;

    border: 2px solid #d5d5d5;

    border-radius: 12px;

    font-size: 19px;

    text-align: left;

    color: #183c40;

    cursor: pointer;

    transition: 0.15s ease;
}

.option:hover {
    border-color: #183c40;
}

.option.correct {
    border-color: #4caf50;
}

.option.incorrect {
    border-color: #e05252;
}

.feedback {
    min-height: 32px;

    margin-top: 22px;

    font-size: 18px;

    font-weight: 600;

    text-align: center;
}

.feedback.correct {
    color: #4caf50;
}

.feedback.incorrect {
    color: #e05252;
}

.next {
    display: none;

    margin: 25px auto 0 auto;

    padding: 13px 28px;

    border: none;

    border-radius: 10px;

    background: #183c40;

    color: white;

    font-size: 17px;

    cursor: pointer;
}

.next:hover {
    opacity: 0.9;
}

.progress {
    text-align: center;

    margin-top: 28px;

    font-size: 14px;

    opacity: 0.65;
}

</style>

</head>


<body>

<div class="container">

    <h1>SAT Vocabulary</h1>

    <div id="question" class="question">
        Loading...
    </div>

    <div id="options" class="options"></div>

    <div id="feedback" class="feedback"></div>

    <button id="next" class="next" onclick="loadQuestion()">
        Next Question
    </button>

    <div id="progress" class="progress"></div>

</div>


<script>

let currentQuestion = null;
let answered = false;
let questionNumber = 0;


async function loadQuestion() {

    answered = false;

    document.getElementById("feedback").textContent = "";
    document.getElementById("feedback").className = "feedback";

    document.getElementById("next").style.display = "none";

    const response = await fetch("/question");

    currentQuestion = await response.json();

    questionNumber++;

    document.getElementById("question").textContent =
        currentQuestion.meaning;

    const optionsContainer =
        document.getElementById("options");

    optionsContainer.innerHTML = "";

    currentQuestion.choices.forEach(function(word) {

        const button = document.createElement("button");

        button.className = "option";

        button.textContent = word;

        button.onclick = function() {
            selectAnswer(button, word);
        };

        optionsContainer.appendChild(button);

    });

    document.getElementById("progress").textContent =
        "Question " + questionNumber;
}


function selectAnswer(button, selectedWord) {

    if (answered) {
        return;
    }

    answered = true;

    const feedback =
        document.getElementById("feedback");

    if (
        selectedWord.toLowerCase() ===
        currentQuestion.answer.toLowerCase()
    ) {

        button.classList.add("correct");

        feedback.textContent = "Correct";
        feedback.className = "feedback correct";

    } else {

        button.classList.add("incorrect");

        feedback.textContent = "Incorrect";
        feedback.className = "feedback incorrect";

    }

    // Disable all choices after one click.
    document.querySelectorAll(".option").forEach(function(option) {
        option.style.cursor = "default";
    });

    document.getElementById("next").style.display = "block";
}


// Load first question.
loadQuestion();

</script>

</body>
</html>
"""


# --------------------------------------------------
# FLASK ROUTES
# --------------------------------------------------

@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/question")
def question():
    return jsonify(make_question())


# --------------------------------------------------
# START SERVER
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
