import {
    fetchReviewStatus,
    fetchPhonemesCovered,
    fetchLearn,
    fetchExercises,
    fetchHomophones,
    fetchReviewHomophones,
    fetchReviewExercises,
    submitAnswer,
    submitHomophAnswer,
    saveProgress,
    fetchUserName,
    saveUserName,
    setTokenProvider,
} from './fetch.js';

const RESOLVE_TIME = 1500;
const div = document.getElementById('app');

let lastAction = null;
let currentPhoneme = null;
let currentUser = null;

const retryAttempts = { amount: 5 };
const restartAttempts = { amount: 2 };

// Set up token provider for fetch.js
setTokenProvider(async () => {
    const user = firebase.auth().currentUser;
    if (!user) return null;
    return user.getIdToken();
});


// --- Helpers ---

function showError(err) {
    if (err?.name === 'APIError') {
        console.groupCollapsed('APIError');
        console.error('meta:', { message: err.message, kind: err.kind, retry: err.retry, status: err.status, detail: err.detail });
        console.error(err);
        console.groupEnd();
    } else {
        console.error(err);
    }
}

function showAppStopped() {
    div.replaceChildren();
    const stopMsg = document.createElement('h2');
    stopMsg.textContent = 'Connection lost';
    const stopSub = document.createElement('p');
    stopSub.className = 'general';
    stopSub.textContent = 'The app is not responding. Please check your connection and try again later.';
    div.append(stopMsg, stopSub);
}

async function allowRetry(action) {
    lastAction = action;
    await action();
}

function postError(err, input, feedback, retryBtn, postRetryAttempts) {
    showError(err);

    if (postRetryAttempts.amount <= 0 || restartAttempts.amount <= 0) {
        showAppStopped();
        return;
    }

    if (err?.name === 'APIError' && err.retry === false) {
        // Non-retryable (e.g. 404) — app stop
        showAppStopped();
        return;
    }

    // Retryable error — let user try again
    input.focus();
    postRetryAttempts.amount -= 1;
    feedback.textContent = "Couldn't check your answer. Click CHECK again in a moment.";
    setTimeout(() => { retryBtn.disabled = false; }, 1000);
}

function getError(err, container, attempts, action) {
    container.replaceChildren();
    const errMsg = document.createElement('h2');
    errMsg.textContent = 'Something went wrong';
    container.append(errMsg);
    showError(err);

    if (attempts.amount <= 0 || restartAttempts.amount <= 0) {
        showAppStopped();
        return;
    }

    const canRetry = err?.name === 'APIError' && err.retry === true && typeof action === 'function';

    if (canRetry) {
        const retryMsg = document.createElement('p');
        retryMsg.className = 'feedback';
        retryMsg.textContent = `${attempts.amount} retries left`;
        container.append(retryMsg);

        const btn = document.createElement('button');
        btn.textContent = 'Retry';
        btn.addEventListener('click', async () => {
            attempts.amount -= 1;
            container.replaceChildren();
            const loading = document.createElement('p');
            loading.className = 'general';
            loading.textContent = 'Retrying...';
            container.append(loading);
            try {
                await action();
                attempts.amount = 5;
            } catch (e) {
                getError(e, container, attempts, action);
            }
        });
        container.append(btn);
    } else {
        const btn = document.createElement('button');
        btn.textContent = 'Restart';
        btn.addEventListener('click', () => {
            restartAttempts.amount -= 1;
            div.replaceChildren();
            showAuthScreen(div);
        });
        container.append(btn);
    }
}

function playAudio(audioUrl) {
    const btn = document.createElement('button');
    if (!audioUrl) {
        btn.textContent = 'Audio unavailable';
        btn.disabled = true;
        return btn;
    }
    const audio = new Audio(audioUrl);
    btn.textContent = '▶️';
    audio.onended = () => { btn.disabled = false; btn.textContent = '▶️'; };
    audio.onerror = () => { btn.textContent = "Audio can't be played right now"; btn.disabled = false; };
    btn.addEventListener('click', async () => {
        btn.disabled = true;
        const slowTimer = setTimeout(() => {
            btn.textContent = '⏳ Loading...';
            btn.disabled = false;
        }, 5000);
        try {
            await audio.play();
            clearTimeout(slowTimer);
        } catch {
            clearTimeout(slowTimer);
            btn.textContent = "Audio can't be played right now";
            btn.disabled = false;
        }
    });
    return btn;
}

const WORD_AUDIO_BASE = 'https://storage.googleapis.com/spell-pron-trainer/word_audio';

function wordAudioUrl(word) {
    return `${WORD_AUDIO_BASE}/${word.toLowerCase()}.mp3`;
}

function clickableWord(word) {
    const span = document.createElement('span');
    span.textContent = word;
    span.className = 'clickable-word';
    span.title = 'Click to hear pronunciation';
    span.addEventListener('click', () => {
        new Audio(wordAudioUrl(word)).play();
    });
    return span;
}

function renderPromptWithIPA(text) {
    // Render IPA transcriptions (/.../) with no-wrap styling (no audio)
    const container = document.createElement('span');
    const parts = text.split(/(\/[^/]+\/)/g);
    for (const part of parts) {
        if (/^\/[^/]+\/$/.test(part)) {
            const span = document.createElement('span');
            span.textContent = part;
            span.style.whiteSpace = 'nowrap';
            container.append(span);
        } else {
            container.append(document.createTextNode(part));
        }
    }
    return container;
}

function renderPatternsList(patterns) {
    const patternsList = document.createElement('ul');
    patternsList.className = 'patterns';
    for (const [pattern, examples] of Object.entries(patterns)) {
        const patLi = document.createElement('li');
        const patSpan = document.createElement('span');
        patSpan.textContent = pattern.toUpperCase();
        patSpan.style.fontWeight = 'bold';
        const arrow = document.createTextNode(' → ');
        patLi.append(patSpan, arrow);
        examples.forEach((word, i) => {
            if (i > 0) patLi.append(document.createTextNode(', '));
            patLi.append(clickableWord(word));
        });
        patternsList.append(patLi);
    }
    return patternsList;
}

function createInput(attemptsLeft) {
    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'Type your answer';
    const btn = document.createElement('button');
    btn.textContent = 'Check';
    const feedback = document.createElement('div');
    feedback.textContent = `${attemptsLeft} attempts left`;
    feedback.className = 'feedback';
    feedback.setAttribute('role', 'status');

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') btn.click();
    });

    return { input, btn, feedback };
}


// --- Auth Screen ---

function showAuthScreen(div) {
    div.replaceChildren();

    const h1 = document.createElement('h1');
    h1.textContent = 'English Pronunciation Trainer';

    const subtitle = document.createElement('p');
    subtitle.textContent = 'Master British English sounds, one phoneme at a time';
    subtitle.style.textAlign = 'center';
    subtitle.style.color = 'rgba(255,255,255,0.8)';
    subtitle.style.marginBottom = '1rem';

    const authBox = document.createElement('div');
    authBox.className = 'auth-box';

    const emailInput = document.createElement('input');
    emailInput.type = 'email';
    emailInput.placeholder = 'Email address';
    emailInput.id = 'auth-email';

    const passInput = document.createElement('input');
    passInput.type = 'password';
    passInput.placeholder = 'Password';
    passInput.id = 'auth-password';

    const feedback = document.createElement('div');
    feedback.className = 'feedback';

    const loginBtn = document.createElement('button');
    loginBtn.textContent = 'Log in';

    const signupBtn = document.createElement('button');
    signupBtn.textContent = 'Sign up';

    passInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') loginBtn.click();
    });

    loginBtn.addEventListener('click', async () => {
        const email = emailInput.value.trim();
        const pass = passInput.value;
        if (!email || !pass) { feedback.textContent = 'Please enter email and password'; return; }

        loginBtn.disabled = true;
        signupBtn.disabled = true;
        feedback.textContent = 'Logging in...';

        try {
            await firebase.auth().signInWithEmailAndPassword(email, pass);
            // onAuthStateChanged will handle the rest
        } catch (err) {
            loginBtn.disabled = false;
            signupBtn.disabled = false;
            if (err.code === 'auth/user-not-found' || err.code === 'auth/wrong-password' || err.code === 'auth/invalid-credential') {
                feedback.textContent = 'Invalid email or password';
            } else if (err.code === 'auth/invalid-email') {
                feedback.textContent = 'Invalid email format';
            } else {
                feedback.textContent = 'Login failed. Please try again.';
                console.error(err);
            }
        }
    });

    signupBtn.addEventListener('click', async () => {
        const email = emailInput.value.trim();
        const pass = passInput.value;
        if (!email || !pass) { feedback.textContent = 'Please enter email and password'; return; }
        if (pass.length < 6) { feedback.textContent = 'Password must be at least 6 characters'; return; }

        loginBtn.disabled = true;
        signupBtn.disabled = true;
        feedback.textContent = 'Creating account...';

        try {
            await firebase.auth().createUserWithEmailAndPassword(email, pass);
            // onAuthStateChanged will handle the rest
        } catch (err) {
            loginBtn.disabled = false;
            signupBtn.disabled = false;
            if (err.code === 'auth/email-already-in-use') {
                feedback.textContent = 'An account with this email already exists';
            } else if (err.code === 'auth/weak-password') {
                feedback.textContent = 'Password is too weak (min 6 characters)';
            } else if (err.code === 'auth/invalid-email') {
                feedback.textContent = 'Invalid email format';
            } else {
                feedback.textContent = 'Sign up failed. Please try again.';
                console.error(err);
            }
        }
    });

    authBox.append(emailInput, passInput, loginBtn, signupBtn, feedback);
    div.append(h1, subtitle, authBox);
}


// --- Logged-in screen ---

async function showLoggedIn(div, user) {
    currentUser = user;

    // Show loading state while fetching
    div.replaceChildren();
    const loadingMsg = document.createElement('p');
    loadingMsg.className = 'general';
    loadingMsg.textContent = 'Loading...';
    loadingMsg.style.textAlign = 'center';
    loadingMsg.style.color = 'white';
    div.append(loadingMsg);

    // Ensure token is fresh before making API calls
    await user.getIdToken(true);

    // Fetch user's name
    const userData = await fetchUserName();
    let displayName = userData.name;

    // If no name set (new user), ask for it
    if (!displayName) {
        await askForName(div);
        const updated = await fetchUserName();
        displayName = updated.name;
    }

    startApp(div, displayName);
}


async function askForName(div) {
    div.replaceChildren();

    const h2 = document.createElement('h2');
    h2.textContent = 'One more thing!';

    const label = document.createElement('p');
    label.className = 'general';
    label.textContent = 'What should we call you?';

    const nameInput = document.createElement('input');
    nameInput.type = 'text';
    nameInput.placeholder = 'Your first name';
    nameInput.id = 'name-input';

    const btn = document.createElement('button');
    btn.textContent = 'Continue';

    const feedback = document.createElement('div');
    feedback.className = 'feedback';

    nameInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') btn.click();
    });

    div.append(h2, label, nameInput, btn, feedback);

    return new Promise((resolve) => {
        btn.addEventListener('click', async () => {
            const name = nameInput.value.trim();
            if (!name) { feedback.textContent = 'Please enter your name'; nameInput.focus(); return; }

            btn.disabled = true;
            feedback.textContent = '';

            try {
                await saveUserName(name);
                resolve();
            } catch (err) {
                btn.disabled = false;
                feedback.textContent = 'Could not save your name. Please try again.';
                showError(err);
            }
        });
    });
}


async function startApp(div, displayName) {
    try {
        await allowRetry(async () => {
            // Fetch data first, then render everything at once
            const reviewStatus = await fetchReviewStatus();

            div.replaceChildren();

            // Logout button
            const logoutBtn = document.createElement('button');
            logoutBtn.textContent = 'Log out';
            logoutBtn.style.float = 'right';
            logoutBtn.addEventListener('click', () => firebase.auth().signOut());
            div.append(logoutBtn);

            await reviewCheck(reviewStatus, div, displayName);
        });
    } catch (err) {
        getError(err, div, retryAttempts, lastAction);
    }
}


// --- Review check ---

async function reviewCheck(reviewStatus, div, displayName) {
    const msg = document.createElement('h2');
    div.append(msg);

    if (reviewStatus.status === 'review_only') {
        msg.textContent = `Welcome back, ${displayName}!`;
        const sub = document.createElement('p');
        sub.className = 'general';
        sub.textContent = "No new phonemes to learn. Let's review previously studied ones";
        div.append(sub);

        // Fetch covered FIRST (fast), then start LLM generation
        const coveredPromise = fetchPhonemesCovered();
        coveredPromise.catch(() => {});

        // Start LLM only after covered request is sent
        const reviewExPromise = coveredPromise.then(() => fetchReviewExercises()).catch(() => {});

        await review(div, coveredPromise, reviewExPromise);
        const bye = document.createElement('p');
        bye.className = 'general';
        bye.textContent = 'You can keep reviewing now or come back for another review session whenever you want!';
        div.append(bye);

        // Allow the user to keep reviewing
        await showReviewOptions(div, { includeCurrentBtn: false });
        return;
    }

    if (reviewStatus.status === 'no_progress') {
        msg.textContent = `Welcome to your first lesson, ${displayName}!`;
        const startBtn = document.createElement('button');
        startBtn.textContent = 'Start lesson';
        div.append(startBtn);
        startBtn.addEventListener('click', async () => {
            try { await allowRetry(() => learn(div)); }
            catch (err) { getError(err, div, retryAttempts, lastAction); }
        });
        return;
    }

    msg.textContent = `Welcome back, ${displayName}!`;
    const sub = document.createElement('p');
    sub.className = 'general';
    sub.textContent = 'Ready to start the review?';
    div.append(sub);

    // Fetch covered FIRST (fast), then start LLM generation
    const coveredPromise = fetchPhonemesCovered();
    coveredPromise.catch(() => {});

    // Start LLM only after covered request is sent (avoids blocking on single-worker)
    const reviewExPromise = coveredPromise.then(() => fetchReviewExercises()).catch(() => {});

    await review(div, coveredPromise, reviewExPromise);
    const learnBtn = document.createElement('button');
    learnBtn.textContent = 'Learn new phoneme';
    learnBtn.addEventListener('click', () => {
        allowRetry(() => learn(div)).catch(err => getError(err, div, retryAttempts, lastAction));
    });
    div.append(learnBtn);
}


// --- Review ---

async function review(div, coveredPromise = null, reviewExPromise = null) {
    return new Promise((resolve) => {
        const btn = document.createElement('button');
        btn.textContent = 'Start review';
        div.append(btn);

        btn.addEventListener('click', async () => {
            try {
                await allowRetry(async () => {
                    div.replaceChildren();

                    // Keep logout button
                    const logoutBtn = document.createElement('button');
                    logoutBtn.textContent = 'Log out';
                    logoutBtn.style.float = 'right';
                    logoutBtn.addEventListener('click', () => firebase.auth().signOut());
                    div.append(logoutBtn);

                    const covered = coveredPromise ? await coveredPromise : await fetchPhonemesCovered();
                    div.append(renderCoveredList(covered));

                    const host = document.createElement('div');
                    div.append(host);

                    const exerciseBtn = document.createElement('button');
                    exerciseBtn.textContent = 'Start review exercises';
                    host.append(exerciseBtn);

                    await new Promise((startResolve) => {
                        exerciseBtn.addEventListener('click', async () => {
                            exerciseBtn.remove();

                            try {
                                const warning = document.createElement('p');
                                warning.textContent = 'Some of the following words may not be spelt with the common patterns above';
                                warning.className = 'warning';
                                host.append(warning);

                                const loading = document.createElement('p');
                                loading.textContent = 'Loading review exercises...';
                                loading.className = 'general';
                                host.append(loading);

                                const data = reviewExPromise ? await reviewExPromise : await fetchReviewExercises();
                                loading.remove();
                                await runAllExercises(data.exercises, host);

                                const homophs = await fetchReviewHomophones();
                                if (homophs.length > 0) {
                                    await runHomophones(homophs, host, { reviewRound: true });
                                }

                                const done = document.createElement('p');
                                done.className = 'general';
                                done.textContent = 'Review completed!';
                                host.append(done);
                                startResolve();
                            } catch (err) {
                                const exerciseRetryAttempts = { amount: 5 };
                                getError(err, host, exerciseRetryAttempts, async () => {
                                    // Quick connectivity check before the long LLM request
                                    await fetchPhonemesCovered();
                                    const data = await fetchReviewExercises();
                                    await runAllExercises(data.exercises, host);

                                    const homophs = await fetchReviewHomophones();
                                    if (homophs.length > 0) {
                                        await runHomophones(homophs, host, { reviewRound: true });
                                    }

                                    const done = document.createElement('p');
                                    done.className = 'general';
                                    done.textContent = 'Review completed!';
                                    host.append(done);
                                    startResolve();
                                });
                            }
                        });
                    });

                    resolve();
                });
            } catch (err) {
                getError(err, div, retryAttempts, lastAction);
            }
        });
    });
}


// --- Learn new phoneme ---

async function learn(div) {
    div.replaceChildren();

    // Keep logout button
    const logoutBtn = document.createElement('button');
    logoutBtn.textContent = 'Log out';
    logoutBtn.style.float = 'right';
    logoutBtn.addEventListener('click', () => firebase.auth().signOut());
    div.append(logoutBtn);

    const phoneme = await fetchLearn();
    currentPhoneme = phoneme.phoneme;

    // Start generating exercises immediately in the background
    const exercisePromise = fetchExercises(currentPhoneme);
    exercisePromise.catch(() => {}); // Suppress unhandled rejection — caught when awaited

    const card = document.createElement('div');
    card.className = 'phoneme-card';

    const intro = document.createElement('h2');
    intro.textContent = `New phoneme: ${phoneme.ipa}  `;
    intro.append(playAudio(phoneme.audio_url));

    const patternsHeading = document.createElement('h3');
    patternsHeading.textContent = 'Most common spelling patterns:';

    const ul = document.createElement('ul');
    ul.className = 'patterns';
    for (const [pattern, examples] of Object.entries(phoneme.patterns)) {
        const li = document.createElement('li');
        const patSpan = document.createElement('span');
        patSpan.textContent = pattern.toUpperCase();
        patSpan.style.fontWeight = 'bold';
        const arrow = document.createTextNode(' → ');
        li.append(patSpan, arrow);
        examples.forEach((word, i) => {
            if (i > 0) li.append(document.createTextNode(', '));
            li.append(clickableWord(word));
        });
        ul.append(li);
    }

    card.append(intro, patternsHeading, ul);

    const exerciseHost = document.createElement('div');
    const exerciseBtn = document.createElement('button');
    exerciseBtn.textContent = 'Start exercises';
    exerciseHost.append(exerciseBtn);

    div.append(card, exerciseHost);

    exerciseBtn.addEventListener('click', async () => {
        try {
            exerciseHost.replaceChildren();
            const loading = document.createElement('p');
            loading.textContent = 'Loading exercises...';
            loading.className = 'general';
            exerciseHost.append(loading);

            const data = await exercisePromise;
            exerciseHost.replaceChildren();

            const warning = document.createElement('p');
            warning.textContent = 'Some of the following words may not be spelt with the common patterns above';
            warning.className = 'warning';
            exerciseHost.append(warning);

            await runAllExercises(data.exercises, exerciseHost);

            const homophBtn = document.createElement('button');
            homophBtn.textContent = 'Continue to homophones';
            exerciseHost.append(homophBtn);

            homophBtn.addEventListener('click', async () => {
                homophBtn.remove();
                try {
                    const homophs = await fetchHomophones(currentPhoneme);
                    await runHomophones(homophs, exerciseHost);
                } catch (err) {
                    getError(err, exerciseHost, retryAttempts, async () => {
                        exerciseHost.replaceChildren();
                        const homophs = await fetchHomophones(currentPhoneme);
                        await runHomophones(homophs, exerciseHost);
                    });
                }
            });
        } catch (err) {
            getError(err, exerciseHost, retryAttempts, async () => {
                exerciseHost.replaceChildren();
                const data = await fetchExercises(currentPhoneme);
                exerciseHost.replaceChildren();
                await runAllExercises(data.exercises, exerciseHost);
            });
        }
    });
}


// --- Exercise engine: NO_HELP then HELP ---

async function runAllExercises(exercises, host) {
    for (const exercise of exercises) {
        const section = document.createElement('div');
        section.className = 'exercise-section';

        const levelHeading = document.createElement('h3');
        levelHeading.textContent = `Level ${exercise.level}: ${exercise.type}`;

        const instructions = document.createElement('p');
        instructions.className = 'instructions';
        instructions.textContent = exercise.instructions;

        section.append(levelHeading, instructions);
        host.append(section);

        const failedItems = [];
        let index = 0;
        for (const item of exercise.items) {
            index++;
            const passed = await runNoHelp(item, index, section, exercise.level);
            if (!passed) {
                failedItems.push(item);
            }
        }

        if (failedItems.length > 0) {
            const helpHeading = document.createElement('h3');
            helpHeading.textContent = `Level ${exercise.level} — Assisted round`;
            section.append(helpHeading);

            let helpIndex = 0;
            for (const item of failedItems) {
                helpIndex++;
                await runHelp(item, helpIndex, section, exercise.level);
            }
        }
    }
}


// --- NO_HELP round ---

async function runNoHelp(item, index, host, level) {
    const itemDiv = document.createElement('div');
    itemDiv.className = 'exercise-item';

    const prompt = document.createElement('p');
    const num = document.createTextNode(`${index}. `);
    const promptText = renderPromptWithIPA(item.no_help_prompt);
    promptText.className = 'test';
    prompt.append(num, promptText);

    const { input, btn, feedback } = createInput(4);
    itemDiv.append(prompt, input, btn, feedback);
    host.append(itemDiv);

    return new Promise((resolve) => {
        let pending = false;
        const postRetryAttempts = { amount: 4 };

        btn.addEventListener('click', async () => {
            if (pending) return;
            const answer = input.value.trim().toLowerCase();
            if (!answer) { input.focus(); return; }

            if (!/^[a-z]+$/.test(answer)) {
                feedback.textContent = 'Only letters are allowed';
                input.value = '';
                input.focus();
                return;
            }

            pending = true;
            btn.disabled = true;

            try {
                const idempotencyKey = crypto.randomUUID();
                const check = await submitAnswer(item.test_id, answer, idempotencyKey);

                if (check.answered === 'correct') {
                    input.disabled = true;
                    feedback.textContent = 'Correct! ✅ ';
                    feedback.append(clickableWord(answer));
                    resolve(true);
                    return;
                }

                if (check.answered === 'failed_no_help') {
                    input.disabled = true;
                    btn.disabled = true;
                    feedback.textContent = 'We will come back to this word later';
                    resolve(false);
                    return;
                }

                // incorrect — keep trying
                pending = false;
                btn.disabled = false;
                input.value = '';
                input.focus();
                feedback.textContent = `Try again. ${check.attempts_left} attempts left`;
            } catch (err) {
                pending = false;
                postError(err, input, feedback, btn, postRetryAttempts);
            }
        });
    });
}


// --- HELP round ---

async function runHelp(item, index, host, level) {
    const itemDiv = document.createElement('div');
    itemDiv.className = 'exercise-item';

    const prompt = document.createElement('p');
    const num = document.createTextNode(`${index}. `);
    const promptText = renderPromptWithIPA(item.help_prompt);
    promptText.className = 'test';
    prompt.append(num, promptText);

    itemDiv.append(prompt);

    if (item.options && item.options.length > 0 && (level === 1 || level === 3)) {
        const optionsP = document.createElement('p');
        optionsP.className = 'instructions';
        optionsP.textContent = 'Options: ' + item.options.join('  |  ');
        itemDiv.append(optionsP);
    }

    const { input, btn, feedback } = createInput(2);
    itemDiv.append(input, btn, feedback);
    host.append(itemDiv);

    return new Promise((resolve) => {
        let pending = false;
        const postRetryAttempts = { amount: 4 };

        btn.addEventListener('click', async () => {
            if (pending) return;
            const answer = input.value.trim().toLowerCase();
            if (!answer) { input.focus(); return; }

            if (item.options && item.options.length > 0 && (level === 1 || level === 3)) {
                const lowerOptions = item.options.map(o => o.toLowerCase());
                if (!lowerOptions.includes(answer)) {
                    feedback.textContent = 'Choose only from the options';
                    input.value = '';
                    input.focus();
                    return;
                }
            }

            pending = true;
            btn.disabled = true;

            try {
                const idempotencyKey = crypto.randomUUID();
                const check = await submitAnswer(item.test_id, answer, idempotencyKey);

                if (check.answered === 'correct') {
                    input.disabled = true;
                    feedback.textContent = 'Correct! ✅ ';
                    feedback.append(clickableWord(answer));
                    resolve();
                    return;
                }

                if (check.answered === 'failed') {
                    input.disabled = true;
                    btn.disabled = true;
                    feedback.textContent = 'The answer is: ';
                    feedback.append(clickableWord(check.solution));
                    resolve();
                    return;
                }

                // incorrect — keep trying
                pending = false;
                btn.disabled = false;
                input.value = '';
                input.focus();
                feedback.textContent = `Try again. ${check.attempts_left} attempts left`;
            } catch (err) {
                pending = false;
                postError(err, input, feedback, btn, postRetryAttempts);
            }
        });
    });
}


// --- Homophones ---

async function runHomophones(homophs, host, { reviewRound = false } = {}) {
    const section = document.createElement('div');
    section.className = 'exercise-section';

    const warning = document.createElement('h3');
    warning.textContent = 'Find the homophones (example: /raɪt/ → write, right, rite, wright)';
    section.append(warning);
    host.append(section);

    let index = 0;
    for (const homoph of homophs) {
        index++;
        await testHomophone(homoph, index, section);
    }

    if (!reviewRound) {
        try {
            await saveProgress(currentPhoneme);
            const bye = document.createElement('p');
            bye.className = 'general';
            bye.textContent = 'Well done! Your progress has been saved. Review sounds or I will see you in another session!';
            host.append(bye);

            // Check how many sounds are now completed
            const covered = await fetchPhonemesCovered();
            const justLearnt = currentPhoneme;

            if (covered.length === 1) {
                // First session — only one sound to review
                const reviewBtn = document.createElement('button');
                reviewBtn.textContent = 'Review current phoneme';
                host.append(reviewBtn);

                reviewBtn.addEventListener('click', async () => {
                    reviewBtn.remove();
                    // Clear the entire page (removes the new phoneme card)
                    div.replaceChildren();

                    const logoutBtn2 = document.createElement('button');
                    logoutBtn2.textContent = 'Log out';
                    logoutBtn2.style.float = 'right';
                    logoutBtn2.addEventListener('click', () => firebase.auth().signOut());
                    div.append(logoutBtn2);

                    const newHost = document.createElement('div');
                    div.append(newHost);
                    await runSingleReview(justLearnt, newHost);
                });
            } else {
                // Multiple sounds — offer current or all
                const reviewCurrentBtn = document.createElement('button');
                reviewCurrentBtn.textContent = 'Review current phoneme';
                host.append(reviewCurrentBtn);

                const reviewAllBtn = document.createElement('button');
                reviewAllBtn.textContent = 'Review all phonemes';
                host.append(reviewAllBtn);

                reviewCurrentBtn.addEventListener('click', async () => {
                    reviewCurrentBtn.remove();
                    reviewAllBtn.remove();
                    // Clear the entire page (removes the new phoneme card)
                    div.replaceChildren();

                    const logoutBtn2 = document.createElement('button');
                    logoutBtn2.textContent = 'Log out';
                    logoutBtn2.style.float = 'right';
                    logoutBtn2.addEventListener('click', () => firebase.auth().signOut());
                    div.append(logoutBtn2);

                    const newHost = document.createElement('div');
                    div.append(newHost);
                    await runSingleReview(justLearnt, newHost);
                });

                reviewAllBtn.addEventListener('click', async () => {
                    reviewCurrentBtn.remove();
                    reviewAllBtn.remove();
                    await startFullReview();
                });
            }
        } catch (err) {
            getError(err, host, retryAttempts, async () => {
                await saveProgress(currentPhoneme);
                const bye = document.createElement('p');
                bye.className = 'general';
                bye.textContent = 'Progress saved!';
                host.append(bye);
            });
        }
    }
}


async function runSingleReview(phoneme, host) {
    const loading = document.createElement('p');
    loading.textContent = 'Loading...';
    loading.className = 'general';
    host.append(loading);

    try {
        // Fetch covered phonemes to get the card info for this phoneme
        const covered = await fetchPhonemesCovered();
        const phonemeData = covered.find(p => p.phoneme === phoneme);

        // Start generating exercises immediately in the background
        const exercisePromise = fetchExercises(phoneme);
        exercisePromise.catch(() => {}); // Suppress unhandled rejection — caught when awaited

        loading.remove();

        // Show the phoneme card (like when it was first learnt)
        if (phonemeData) {
            const card = document.createElement('div');
            card.className = 'phoneme-card';

            const intro = document.createElement('h2');
            intro.textContent = `Reviewing: /${phonemeData.phoneme}/  `;
            intro.append(playAudio(phonemeData.audio_url));

            const patternsHeading = document.createElement('h3');
            patternsHeading.textContent = 'Most common spelling patterns:';

            const ul = document.createElement('ul');
            ul.className = 'patterns';
            for (const [pattern, examples] of Object.entries(phonemeData.patterns)) {
                const li = document.createElement('li');
                const patSpan = document.createElement('span');
                patSpan.textContent = pattern.toUpperCase();
                patSpan.style.fontWeight = 'bold';
                const arrow = document.createTextNode(' → ');
                li.append(patSpan, arrow);
                examples.forEach((word, i) => {
                    if (i > 0) li.append(document.createTextNode(', '));
                    li.append(clickableWord(word));
                });
                ul.append(li);
            }

            card.append(intro, patternsHeading, ul);
            host.append(card);
        }

        // Add "Start exercises" button
        const exerciseHost = document.createElement('div');
        host.append(exerciseHost);

        const startBtn = document.createElement('button');
        startBtn.textContent = 'Start exercises';
        exerciseHost.append(startBtn);

        await new Promise((resolve) => {
            startBtn.addEventListener('click', async () => {
                startBtn.remove();

                const exLoading = document.createElement('p');
                exLoading.textContent = 'Loading exercises...';
                exLoading.className = 'general';
                exerciseHost.append(exLoading);

                try {
                    const data = await exercisePromise;
                    exLoading.remove();

                    const warning = document.createElement('p');
                    warning.textContent = 'Some of the following words may not be spelt with the common patterns above';
                    warning.className = 'warning';
                    exerciseHost.append(warning);

                    await runAllExercises(data.exercises, exerciseHost);

                    const homophs = await fetchHomophones(phoneme);
                    await runHomophones(homophs, exerciseHost, { reviewRound: true });

                    const done = document.createElement('p');
                    done.className = 'general';
                    done.textContent = 'Review completed!';
                    exerciseHost.append(done);

                    resolve();
                } catch (err) {
                    getError(err, exerciseHost, retryAttempts, async () => {
                        exerciseHost.replaceChildren();
                        const data = await fetchExercises(phoneme);
                        await runAllExercises(data.exercises, exerciseHost);

                        const homophs = await fetchHomophones(phoneme);
                        await runHomophones(homophs, exerciseHost, { reviewRound: true });

                        const done = document.createElement('p');
                        done.className = 'general';
                        done.textContent = 'Review completed!';
                        exerciseHost.append(done);
                        resolve();
                    });
                }
            });
        });

        // Show review options again
        await showReviewOptions(host);
    } catch (err) {
        getError(err, host, retryAttempts, () => runSingleReview(phoneme, host));
    }
}


async function runMixedReview(host, reviewExPromise = null) {
    // Start generating exercises immediately in the background
    if (!reviewExPromise) {
        reviewExPromise = fetchReviewExercises();
        reviewExPromise.catch(() => {}); // Suppress unhandled rejection — caught when awaited
    }

    const startBtn = document.createElement('button');
    startBtn.textContent = 'Start exercises';
    host.append(startBtn);

    await new Promise((startResolve) => {
        startBtn.addEventListener('click', async () => {
            startBtn.remove();

            const loading = document.createElement('p');
            loading.textContent = 'Loading review exercises...';
            loading.className = 'general';
            host.append(loading);

            try {
                const warning = document.createElement('p');
                warning.textContent = 'Some of the following words may not be spelt with the common patterns above';
                warning.className = 'warning';
                host.append(warning);

                const data = await reviewExPromise;
                loading.remove();
                await runAllExercises(data.exercises, host);

                const homophs = await fetchReviewHomophones();
                if (homophs.length > 0) {
                    await runHomophones(homophs, host, { reviewRound: true });
                }

                const done = document.createElement('p');
                done.className = 'general';
                done.textContent = 'Review completed!';
                host.append(done);

                // Show review options again
                await showReviewOptions(host);
                startResolve();
            } catch (err) {
                getError(err, host, retryAttempts, async () => {
                    host.replaceChildren();
                    const data = await fetchReviewExercises();
                    await runAllExercises(data.exercises, host);

                    const homophs = await fetchReviewHomophones();
                    if (homophs.length > 0) {
                        await runHomophones(homophs, host, { reviewRound: true });
                    }

                    const done = document.createElement('p');
                    done.className = 'general';
                    done.textContent = 'Review completed!';
                    host.append(done);

                    await showReviewOptions(host);
                    startResolve();
                });
            }
        });
    });
}


function renderCoveredList(covered) {
    const fragment = document.createDocumentFragment();

    const heading = document.createElement('h2');
    heading.textContent = 'Phonemes covered so far';
    heading.style.color = 'rgba(255, 255, 255, 1)';

    const list = document.createElement('ul');
    list.className = 'patterns';
    for (const p of covered) {
        const li = document.createElement('li');
        const phonemeText = document.createElement('span');
        phonemeText.style.fontWeight = 'bold';
        phonemeText.style.fontSize = '1.3rem';
        phonemeText.textContent = `/${p.phoneme}/  `;
        li.append(phonemeText, playAudio(p.audio_url));

        const patternsLabel = document.createElement('p');
        patternsLabel.textContent = 'Most common spelling patterns:';
        patternsLabel.style.fontWeight = 'bold';
        patternsLabel.style.marginTop = '0.5rem';
        patternsLabel.style.marginBottom = '0.2rem';
        li.append(patternsLabel);

        const patternsList = document.createElement('ul');
        patternsList.className = 'patterns';
        for (const [pattern, examples] of Object.entries(p.patterns)) {
            const patLi = document.createElement('li');
            const patSpan = document.createElement('span');
            patSpan.textContent = pattern.toUpperCase();
            patSpan.style.fontWeight = 'bold';
            const arrow = document.createTextNode(' → ');
            patLi.append(patSpan, arrow);
            examples.forEach((word, i) => {
                if (i > 0) patLi.append(document.createTextNode(', '));
                patLi.append(clickableWord(word));
            });
            patternsList.append(patLi);
        }
        li.append(patternsList);
        list.append(li);
    }

    fragment.append(heading, list);
    return fragment;
}


async function startFullReview() {
    div.replaceChildren();

    const logoutBtn = document.createElement('button');
    logoutBtn.textContent = 'Log out';
    logoutBtn.style.float = 'right';
    logoutBtn.addEventListener('click', () => firebase.auth().signOut());
    div.append(logoutBtn);

    // Fetch covered phonemes FIRST (fast), then start LLM generation
    const covered = await fetchPhonemesCovered();

    // Start generating exercises in the background AFTER covered data is loaded
    const reviewExPromise = fetchReviewExercises();
    reviewExPromise.catch(() => {});

    div.append(renderCoveredList(covered));

    const newHost = document.createElement('div');
    div.append(newHost);
    await runMixedReview(newHost, reviewExPromise);
}


async function showReviewOptions(host, { includeCurrentBtn = true } = {}) {
    // Check how many phonemes the user has to decide which buttons to show
    const covered = await fetchPhonemesCovered();
    const hasMultiple = covered.length > 1;

    const buttons = [];

    if (includeCurrentBtn) {
        const reviewCurrentBtn = document.createElement('button');
        reviewCurrentBtn.textContent = 'Review current phoneme';
        host.append(reviewCurrentBtn);
        buttons.push(reviewCurrentBtn);
    }

    if (hasMultiple || !includeCurrentBtn) {
        const reviewAllBtn = document.createElement('button');
        reviewAllBtn.textContent = 'Review all phonemes';
        host.append(reviewAllBtn);
        buttons.push(reviewAllBtn);
    }

    await new Promise((resolve) => {
        if (includeCurrentBtn && buttons[0]) {
            buttons[0].addEventListener('click', async () => {
                buttons.forEach(b => b.remove());
                div.replaceChildren();

                const logoutBtn = document.createElement('button');
                logoutBtn.textContent = 'Log out';
                logoutBtn.style.float = 'right';
                logoutBtn.addEventListener('click', () => firebase.auth().signOut());
                div.append(logoutBtn);

                const newHost = document.createElement('div');
                div.append(newHost);

                const lastPhoneme = covered[covered.length - 1].phoneme;
                await runSingleReview(lastPhoneme, newHost);
                resolve();
            });
        }

        const reviewAllBtn = buttons.find(b => b.textContent === 'Review all phonemes');
        if (reviewAllBtn) {
            reviewAllBtn.addEventListener('click', async () => {
                buttons.forEach(b => b.remove());
                await startFullReview();
                resolve();
            });
        }
    });
}


async function testHomophone(homoph, index, host) {
    const exercise = document.createElement('div');
    exercise.className = 'exercise-item';
    const task = document.createElement('h3');
    const ind = document.createTextNode(`${index}. `);
    const target = document.createElement('span');
    target.textContent = homoph.homoph;
    target.className = 'test clickable-word';
    if (homoph.audio_url) {
        target.style.cursor = 'pointer';
        target.title = 'Click to hear pronunciation';
        target.addEventListener('click', () => {
            new Audio(homoph.audio_url).play();
        });
    }
    const rest = document.createTextNode(` has ${homoph.amount} homophones`);
    task.append(ind, target, rest);

    const test = document.createElement('div');
    const { input, btn, feedback } = createInput(4);
    const guessed = document.createElement('ol');
    guessed.className = 'answer';
    test.append(guessed, input, btn, feedback);
    exercise.append(task, test);
    host.append(exercise);

    const correctAnswers = new Set();

    await new Promise((resolve) => {
        let pending = false;
        const postRetryAttempts = { amount: 4 };

        btn.addEventListener('click', async () => {
            if (pending) return;
            const answer = input.value.trim().toLowerCase();
            if (!answer || correctAnswers.has(answer)) { input.focus(); return; }

            if (!/^[a-z]+$/.test(answer)) {
                feedback.textContent = 'Only letters are allowed';
                input.value = '';
                input.focus();
                return;
            }

            pending = true;
            btn.disabled = true;

            try {
                const idempotencyKey = crypto.randomUUID();
                const check = await submitHomophAnswer(homoph.test_id, answer, idempotencyKey);

                if (check.answered === 'correct') {
                    pending = false;
                    btn.disabled = false;
                    correctAnswers.add(answer);
                    const li = document.createElement('li');
                    li.textContent = `${answer} ✅`;
                    guessed.append(li);
                    feedback.textContent = `${check.attempts_left} attempts left`;
                    input.value = '';
                    input.focus();
                    return;
                }

                if (check.answered === 'done') {
                    const li = document.createElement('li');
                    li.textContent = `${answer} ✅`;
                    guessed.append(li);
                    btn.remove(); input.remove(); feedback.remove();
                    resolve();
                    return;
                }

                if (check.answered === 'failed') {
                    btn.remove(); input.remove();
                    const label = correctAnswers.size === 0 ? 'All the homophones of ' : 'The remaining homophones of ';
                    feedback.textContent = '';
                    const start = document.createElement('span');
                    start.className = 'feedback-failed';
                    start.textContent = label;
                    const t = document.createElement('span');
                    t.textContent = homoph.homoph;
                    t.className = 'test';
                    const are = document.createElement('span');
                    are.className = 'feedback-failed';
                    are.textContent = ' are ';
                    const sols = document.createElement('span');
                    sols.textContent = check.solution.join(', ');
                    sols.className = 'solution';
                    feedback.append(start, t, are, sols);
                    resolve();
                    return;
                }

                // incorrect — keep trying
                pending = false;
                btn.disabled = false;
                input.value = '';
                input.focus();
                feedback.textContent = `Try again. ${check.attempts_left} attempts left`;
            } catch (err) {
                pending = false;
                postError(err, input, feedback, btn, postRetryAttempts);
            }
        });
    });
}


// --- Firebase Auth State Listener ---

firebase.auth().onAuthStateChanged((user) => {
    if (user) {
        showLoggedIn(div, user).catch(err => {
            console.error('Login flow error:', err);
            getError(err, div, retryAttempts, () => showLoggedIn(div, user));
        });
    } else {
        currentUser = null;
        showAuthScreen(div);
    }
});
