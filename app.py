from flask import Flask, render_template_string, jsonify, request
import json
import random
import re

app = Flask(__name__)

# ============================================================
# LOAD VOCABULARY
# ============================================================

with open("sat_words_clean.json", "r", encoding="utf-8") as f:
    raw_words = json.load(f)

vocab = []


# ============================================================
# CLEAN MEANINGS
# ============================================================

def clean_meaning(text):
    """
    Clean the meaning before showing it to the user.

    Removes:
    - Embedded example sentences in parentheses
    - (n.), (v.), (adj.), etc.
    - Extra whitespace

    Keeps:
    - Multiple numbered meanings
    - The actual definitions
    """

    text = str(text).strip()

    # --------------------------------------------------------
    # Remove parenthetical content.
    #
    # Your JSON sometimes contains:
    #
    # a place of refuge... (For Thoreau, the forest served...)
    #
    # or:
    #
    # (This game is so facile...)
    #
    # Removing parenthetical content prevents examples
    # from accidentally giving away the answer.
    # --------------------------------------------------------

    previous = None

    while previous != text:
        previous = text
        text = re.sub(r"\([^()]*\)", " ", text)

    # --------------------------------------------------------
    # Remove standalone parts of speech that may remain.
    # --------------------------------------------------------

    text = re.sub(
        r"\b(?:n|v|adj|adv|prep|conj|pron)\.\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    # --------------------------------------------------------
    # Clean up whitespace.
    # --------------------------------------------------------

    text = re.sub(r"[ \t]+", " ", text)

    text = re.sub(r"\n\s*\n+", "\n\n", text)

    text = text.strip()

    return text


# ============================================================
# BUILD CLEAN VOCABULARY
# ============================================================

for item in raw_words:

    word = str(item.get("word", "")).strip()
    meaning = str(item.get("meaning", "")).strip()

    if not word or not meaning:
        continue

    cleaned = clean_meaning(meaning)

    if not cleaned:
        continue

    vocab.append({
        "word": word,
        "meaning": cleaned
    })


print(f"Loaded {len(vocab)} words")


# ============================================================
# MEANING SIMILARITY
# ============================================================

def normalize(text):
    text = text.lower()

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def meaning_tokens(text):

    stopwords = {
        "to",
        "a",
        "an",
        "the",
        "of",
        "and",
        "or",
        "for",
        "in",
        "on",
        "with",
        "by",
        "someone",
        "something",
        "one",
        "that",
        "as",
        "from",
        "be",
        "is",
        "are",
        "being"
    }

    return {
        word
        for word in normalize(text).split()
        if len(word) > 2 and word not in stopwords
    }


def meanings_too_similar(meaning1, meaning2):

    a = meaning_tokens(meaning1)
    b = meaning_tokens(meaning2)

    if not a or not b:
        return False

    overlap = len(a & b)

    smaller = min(
        len(a),
        len(b)
    )

    if smaller > 0:

        similarity = overlap / smaller

        if similarity >= 0.6:
            return True

    return False


# ============================================================
# CREATE QUESTION
# ============================================================

def make_question(excluded_words):

    excluded = {
        word.lower()
        for word in excluded_words
    }

    available = [
        item
        for item in vocab
        if item["word"].lower() not in excluded
    ]

    # --------------------------------------------------------
    # If there are no unused questions left.
    # --------------------------------------------------------

    if not available:
        return None

    # Pick a random unused question.
    answer = random.choice(available)

    choices = [answer]

    candidates = [
        item
        for item in vocab
        if item["word"].lower() != answer["word"].lower()
    ]

    random.shuffle(candidates)

    # --------------------------------------------------------
    # Find three distractors.
    # --------------------------------------------------------

    for candidate in candidates:

        if candidate["word"].lower() in excluded:
            # This only prevents previously asked words
            # from becoming distractors.
            continue

        # Don't use a word already selected.
        if any(
            candidate["word"].lower() ==
            existing["word"].lower()
            for existing in choices
        ):
            continue

        # Don't use a meaning that is too similar
        # to the correct answer.
        if meanings_too_similar(
            candidate["meaning"],
            answer["meaning"]
        ):
            continue

        # Don't use distractors that are too similar
        # to each other.
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

    # --------------------------------------------------------
    # Safety fallback.
    #
    # If similarity filtering couldn't find enough options,
    # fill the remaining choices from the vocabulary.
    # --------------------------------------------------------

    if len(choices) < 4:

        fallback = vocab.copy()

        random.shuffle(fallback)

        for candidate in fallback:

            if any(
                candidate["word"].lower() ==
                existing["word"].lower()
                for existing in choices
            ):
                continue

            choices.append(candidate)

            if len(choices) == 4:
                break

    random.shuffle(choices)

    return {
        "id": answer["word"],
        "meaning": answer["meaning"],
        "answer": answer["word"],
        "choices": [
            item["word"]
            for item in choices
        ]
    }


# ============================================================
# HTML
# ============================================================

HTML = """
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title> SAT Vocabulary Quiz</title>


<style>

* {
    box-sizing: border-box;
}


body {

    margin: 0;

    min-height: 100vh;

    font-family:
        "Segoe UI",
        Arial,
        sans-serif;

    background: #b0d5cd;

    color: #183c40;

    display: flex;

    justify-content: center;

    align-items: center;

    padding: 20px;
}


.container {

    width: min(
        720px,
        100%
    );

    background: #fffaf0;

    border-radius: 20px;

    padding: 40px;

    box-shadow:
        0 10px 35px
        rgba(
            24,
            60,
            64,
            0.15
        );
}

.header {
    position: relative;
    display: flex;
    justify-content: center;
    align-items: center;
    margin-bottom: 30px;
    min-height: 35px;
}

.header-left {
    position: absolute;
    left: 0;
    display: flex;
    /*align-items: center;*/
}

.question-number {
    font-size: 17px;
    font-weight: 200;
    opacity: 0.7;
}

.title {
    font-family:
        Georgia,
        "Times New Roman",
        serif;
        
   
    font-size: 28px;
    font-weight: bold;
   
}

.progress {
    position: absolute;
    right: 0;
    font-size: 15px;
    opacity: 0.7;
}



.question {

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 24px;

    line-height: 1.5;

    text-align: center;

    margin-bottom: 30px;

    white-space: pre-line;
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

    transition:
        border-color 0.15s ease,
        background 0.15s ease;
}


.option:hover {

    border-color: #183c40;
}


.option.correct {

    border-color: #4caf50;

    background: #fffaf0;
}


.option.incorrect {

    border-color: #e05252;

    background: #fffaf0;
}


.feedback {

    min-height: 30px;

    margin-top: 20px;

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


.navigation {

    display: flex;

    justify-content: space-between;

    align-items: center;

    margin-top: 25px;

    gap: 15px;
}


.nav-button {

    padding: 12px 22px;

    border: none;

    border-radius: 10px;

    background: #183c40;

    color: white;

    font-size: 16px;

    cursor: pointer;
}


.nav-button:hover {

    opacity: 0.9;
}


.nav-button:disabled {

    opacity: 0.35;

    cursor: default;
}


.next-button {

    margin-left: auto;

}

.study-controls {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 25px;
    flex-wrap: wrap;
}

.mode-button {
    padding: 9px 14px;
    border: 2px solid #183c40;
    border-radius: 9px;
    background: transparent;
    color: #183c40;
    font-size: 14px;
    cursor: pointer;
}

.mode-button.active {
    background: #183c40;
    color: white;
}

.incorrect-count {
    font-size: 14px;
    opacity: 0.75;
    margin-left: auto;
}

.clear-button {
    padding: 8px 12px;
    border: 1px solid #d5d5d5;
    border-radius: 8px;
    background: transparent;
    color: #183c40;
    cursor: pointer;
    font-size: 13px;
}

.complete {

    text-align: center;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 25px;

    line-height: 1.5;
}


.restart {

    display: block;

    margin: 25px auto 0 auto;

    padding: 13px 25px;

    border: none;

    border-radius: 10px;

    background: #183c40;

    color: white;

    font-size: 17px;

    cursor: pointer;
}


@media (max-width: 600px) {

    .container {

        padding: 25px;
    }

    .header {

        flex-direction: column;

        gap: 8px;

        align-items: flex-start;
    }

    .question {

        font-size: 21px;
    }

    .option {

        font-size: 17px;

        padding: 15px;
    }

}

</style>

</head>


<body>


<div class="container">

    <div class="header">

        <div class="header-left">

            <div
                id="questionNumber"
                class="question-number"
            >
                Qusetion 1
            </div>

            <div class="title">
                |   SAT Vocabulary
            </div>

        </div>

        <div
            id="progress"
            class="progress"
        >
            0 / {{ total }}
        </div>

    </div>

<div class="study-controls">

    <button
        class="mode-button active"
        id="allWordsButton"
        onclick="switchMode('all')"
    >
        All Words
    </button>

    <button
        class="mode-button"
        id="incorrectButton"
        onclick="switchMode('incorrect')"
    >
        Practice Incorrect
    </button>

    <span
        id="incorrectCount"
        class="incorrect-count"
    >
        Incorrect: 0
    </span>

    <button
        class="clear-button"
        onclick="clearIncorrect()"
    >
        Clear
    </button>

</div>


    <div
        id="quiz"
    >

        <div
            id="question"
            class="question"
        >
            Loading...
        </div>


        <div
            id="options"
            class="options"
        >
        </div>


        <div
            id="feedback"
            class="feedback"
        >
        </div>


        <div
            class="navigation"
        >

            <button
                id="backButton"
                class="nav-button"
                onclick="goBack()"
                disabled
            >
                ← Back
            </button>


            <button
                id="nextButton"
                class="nav-button next-button"
                onclick="goNext()"
                style="display:none;"
            >
                Next →
            </button>

        </div>

    </div>


    <div
        id="complete"
        class="complete"
        style="display:none;"
    >

        <div>
            🎉 You've completed all {{ total }} questions!
        </div>

        <button
            class="restart"
            onclick="restartQuiz()"
        >
            Start Again
        </button>

    </div>


</div>


<script>


// ============================================================
// QUIZ STATE
// ============================================================

let history = [];

let currentIndex = -1;

let uniqueCount = 0;

let finished = false;

// "all" = all vocabulary
// "incorrect" = only locally saved incorrect words
let quizMode = "all";

// Words stored locally in this browser
let incorrectWords =
    JSON.parse(
        localStorage.getItem("satIncorrectWords") || "[]"
    );


// ============================================================
// LOAD A NEW QUESTION
// ============================================================

async function getNewQuestion() {

    const seenWords = history.map(
        item => item.question.id
    );

    let excluded = [...seenWords];

    let endpoint = "/question";

    // ------------------------------------------------
    // Practice Incorrect mode
    // ------------------------------------------------

    if (quizMode === "incorrect") {

        if (incorrectWords.length === 0) {

            showNoIncorrect();

            return;
        }

        endpoint = "/incorrect-question";

        excluded = [...seenWords];
    }

    const response = await fetch(
        endpoint,
        {
            method: "POST",

            headers: {
                "Content-Type":
                    "application/json"
            },

            body: JSON.stringify({
                excluded: excluded,
                incorrect: incorrectWords
            })
        }
    );

    const question =
        await response.json();

    if (question === null) {

        showComplete();

        return;
    }

    const state = {

        question: question,

        selected: null,

        correct: null

    };

    history =
        history.slice(
            0,
            currentIndex + 1
        );

    history.push(state);

    currentIndex++;

    uniqueCount = history.length;

    renderQuestion();
}


// ============================================================
// RENDER CURRENT QUESTION
// ============================================================

function renderQuestion() {

    const state =
        history[currentIndex];


    if (!state) {
        return;
    }


    document.getElementById(
        "question"
    ).textContent =
        state.question.meaning;


    const options =
        document.getElementById(
            "options"
        );


    options.innerHTML = "";


    state.question.choices.forEach(
        function(word) {

            const button =
                document.createElement(
                    "button"
                );


            button.className =
                "option";


            button.textContent =
                word;


            // Restore previous answer state.
            if (
                state.selected !== null &&
                word === state.selected
            ) {

                if (state.correct) {

                    button.classList.add(
                        "correct"
                    );

                } else {

                    button.classList.add(
                        "incorrect"
                    );

                }

            }


            button.onclick =
                function() {

                    selectAnswer(
                        button,
                        word
                    );

                };


            if (
                state.selected !== null
            ) {

                button.style.cursor =
                    "default";

            }


            options.appendChild(
                button
            );

        }
    );


    const feedback =
        document.getElementById(
            "feedback"
        );


    feedback.textContent = "";


    if (
        state.selected !== null
    ) {

        if (state.correct) {

            feedback.textContent =
                "Correct";

            feedback.className =
                "feedback correct";

        } else {

            feedback.textContent =
                "Incorrect";

            feedback.className =
                "feedback incorrect";

        }

    } else {

        feedback.className =
            "feedback";

    }


    document.getElementById(
        "progress"
    ).textContent =
        uniqueCount +
        " / " +
        {{ total }};

    document.getElementById(
        "questionNumber"
    ).textContent =
        "Question " + (currentIndex + 1);


    document.getElementById(
        "backButton"
    ).disabled =
        currentIndex <= 0;


    const nextButton =
        document.getElementById(
            "nextButton"
        );


    if (
        state.selected !== null
    ) {

        nextButton.style.display =
            "block";

    } else {

        nextButton.style.display =
            "none";

    }

}


// ============================================================
// ANSWER QUESTION
// ============================================================

function selectAnswer(
    button,
    selectedWord
) {

    const state =
        history[currentIndex];


    // Prevent clicking twice.
    if (
        state.selected !== null
    ) {

        return;
    }


    state.selected =
        selectedWord;


    state.correct =
        selectedWord.toLowerCase() ===
        state.question.answer.toLowerCase();
        // Save incorrect answer locally
if (!state.correct) {

    saveIncorrect(
        state.question.answer
    );

}


    if (state.correct) {

        button.classList.add(
            "correct"
        );

    } else {

        button.classList.add(
            "incorrect"
        );

    }


    const feedback =
        document.getElementById(
            "feedback"
        );


    if (state.correct) {

        feedback.textContent =
            "Correct";

        feedback.className =
            "feedback correct";

    } else {

        feedback.textContent =
            "Incorrect";

        feedback.className =
            "feedback incorrect";

    }


    document.querySelectorAll(
        ".option"
    ).forEach(
        function(option) {

            option.style.cursor =
                "default";

        }
    );


    document.getElementById(
        "nextButton"
    ).style.display =
        "block";

}


// ============================================================
// NEXT QUESTION
// ============================================================

function goNext() {

    // If there is already a question ahead in history,
    // restore it.
    if (
        currentIndex <
        history.length - 1
    ) {

        currentIndex++;

        renderQuestion();

        return;
    }

    // ------------------------------------------------
    // Practice Incorrect mode
    // ------------------------------------------------

    if (quizMode === "incorrect") {

        // Start another round of the incorrect words.
        history = [];

        currentIndex = -1;

        uniqueCount = 0;

        getNewQuestion();

        return;
    }

    // ------------------------------------------------
    // All Words mode
    // ------------------------------------------------

    getNewQuestion();
}

// ============================================================
// BACK BUTTON
// ============================================================

function goBack() {

    if (
        currentIndex <= 0
    ) {

        return;
    }


    currentIndex--;

    renderQuestion();

}


// ============================================================
// COMPLETION
// ============================================================

function showComplete() {

    finished = true;

    document.getElementById(
        "quiz"
    ).style.display =
        "none";

    document.getElementById(
        "complete"
    ).style.display =
        "block";

    const completeMessage =
        document.querySelector(
            "#complete div"
        );

    if (quizMode === "incorrect") {

        completeMessage.textContent =
            "🎯 You've gone through all your incorrect questions. " +
            "They will keep looping until you switch back to All Words.";

    } else {

        completeMessage.textContent =
            "🎉 You've completed all " +
            {{ total }} +
            " questions!";
    }
}


// ============================================================
// RESTART
// ============================================================

function restartQuiz() {

    history = [];

    currentIndex = -1;

    uniqueCount = 0;

    finished = false;


    document.getElementById(
        "quiz"
    ).style.display =
        "block";


    document.getElementById(
        "complete"
    ).style.display =
        "none";


    getNewQuestion();

}

// ============================================================
// INCORRECT WORD STORAGE
// ============================================================

function saveIncorrect(word) {

    if (
        !incorrectWords.some(
            w =>
                w.toLowerCase() ===
                word.toLowerCase()
        )
    ) {

        incorrectWords.push(word);

        localStorage.setItem(
            "satIncorrectWords",
            JSON.stringify(incorrectWords)
        );
    }

    updateIncorrectCount();
}


// ============================================================
// UPDATE INCORRECT COUNT
// ============================================================

function updateIncorrectCount() {

    document.getElementById(
        "incorrectCount"
    ).textContent =
        "Incorrect: " +
        incorrectWords.length;
}


// ============================================================
// SWITCH QUIZ MODE
// ============================================================

function switchMode(mode) {

    if (
        mode === "incorrect" &&
        incorrectWords.length === 0
    ) {

        alert(
            "You don't have any incorrect words yet."
        );

        return;
    }

    quizMode = mode;

    history = [];

    currentIndex = -1;

    uniqueCount = 0;

    finished = false;

    document.getElementById(
        "allWordsButton"
    ).classList.toggle(
        "active",
        mode === "all"
    );

    document.getElementById(
        "incorrectButton"
    ).classList.toggle(
        "active",
        mode === "incorrect"
    );

    document.getElementById(
        "complete"
    ).style.display =
        "none";

    document.getElementById(
        "quiz"
    ).style.display =
        "block";

    getNewQuestion();
}


// ============================================================
// CLEAR INCORRECT WORDS
// ============================================================

function clearIncorrect() {

    if (
        incorrectWords.length === 0
    ) {

        return;
    }

    const confirmed =
        confirm(
            "Clear all incorrect words?"
        );

    if (!confirmed) {

        return;
    }

    incorrectWords = [];

    localStorage.removeItem(
        "satIncorrectWords"
    );

    updateIncorrectCount();

    if (
        quizMode === "incorrect"
    ) {

        quizMode = "all";

        history = [];

        currentIndex = -1;

        uniqueCount = 0;

        document.getElementById(
            "allWordsButton"
        ).classList.add(
            "active"
        );

        document.getElementById(
            "incorrectButton"
        ).classList.remove(
            "active"
        );

        getNewQuestion();
    }
}


// ============================================================
// NO INCORRECT QUESTIONS
// ============================================================

function showNoIncorrect() {

    document.getElementById(
        "question"
    ).textContent =
        "You don't have any incorrect questions yet.";

    document.getElementById(
        "options"
    ).innerHTML = "";

    document.getElementById(
        "feedback"
    ).textContent = "";

    document.getElementById(
        "nextButton"
    ).style.display =
        "none";

    document.getElementById(
        "backButton"
    ).disabled =
        true;
}


// ============================================================
// START
// ============================================================

updateIncorrectCount();

getNewQuestion();


</script>

</body>

</html>
"""


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def home():

    return render_template_string(
        HTML,
        total=len(vocab)
    )


@app.route("/question", methods=["POST"])
def question():

    data = request.get_json(
        silent=True
    ) or {}

    excluded = data.get("excluded", [])

    result = make_question(excluded)


    return jsonify(result)

@app.route("/incorrect-question", methods=["POST"])
def incorrect_question():

    data = request.get_json(
        silent=True
    ) or {}

    excluded = data.get(
        "excluded",
        []
    )

    incorrect = data.get(
        "incorrect",
        []
    )

    excluded_lower = {
        word.lower()
        for word in excluded
    }

    incorrect_lower = {
        word.lower()
        for word in incorrect
    }

    available = [
        item
        for item in vocab
        if (
            item["word"].lower()
            in incorrect_lower
            and
            item["word"].lower()
            not in excluded_lower
        )
    ]

    if not available:

        return jsonify(None)

    answer = random.choice(
        available
    )

    choices = [answer]

    candidates = [
        item
        for item in vocab
        if (
            item["word"].lower()
            != answer["word"].lower()
        )
    ]

    random.shuffle(candidates)

    for candidate in candidates:

        if any(
            candidate["word"].lower()
            ==
            existing["word"].lower()
            for existing in choices
        ):
            continue

        if meanings_too_similar(
            candidate["meaning"],
            answer["meaning"]
        ):
            continue

        choices.append(candidate)

        if len(choices) == 4:
            break

    # Safety fallback
    if len(choices) < 4:

        fallback = vocab.copy()

        random.shuffle(fallback)

        for candidate in fallback:

            if any(
                candidate["word"].lower()
                ==
                existing["word"].lower()
                for existing in choices
            ):
                continue

            choices.append(candidate)

            if len(choices) == 4:
                break

    random.shuffle(choices)

    return jsonify({
        "id": answer["word"],
        "meaning": answer["meaning"],
        "answer": answer["word"],
        "choices": [
            item["word"]
            for item in choices
        ]
    })


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
