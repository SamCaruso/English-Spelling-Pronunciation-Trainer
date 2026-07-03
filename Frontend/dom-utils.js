/**
 * Pure DOM utility functions for the English Pronunciation Trainer.
 * These are stateless rendering helpers with no dependencies on app logic,
 * auth state, or API calls.
 */

const WORD_AUDIO_BASE = 'https://storage.googleapis.com/spell-pron-trainer/word_audio';


export function wordAudioUrl(word) {
    return `${WORD_AUDIO_BASE}/${word.toLowerCase()}.mp3`;
}


export function playAudio(audioUrl) {
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


export function clickableWord(word) {
    const span = document.createElement('span');
    span.textContent = word;
    span.className = 'clickable-word';
    span.title = 'Click to hear pronunciation';
    let lastClick = 0;
    span.addEventListener('click', (e) => {
        e.stopPropagation();
        const now = Date.now();
        if (now - lastClick < 1000) return;
        lastClick = now;
        new Audio(wordAudioUrl(word)).play();
    });
    return span;
}


export function renderPromptWithIPA(text) {
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


export function createInput(attemptsLeft) {
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


export function renderCoveredList(covered) {
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
        li.append(phonemeText, playAudio(wordAudioUrl(p.api_word)));

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
