/**
 * API client for the English Pronunciation Trainer.
 * Handles all HTTP communication with the backend, including
 * authentication headers, timeouts, retries, and error classification.
 * Exports named functions for each API endpoint.
 */

const API_BASE = '';

const ENDPOINTS = {
    reviewStatus:      '/api/reviewstatus',
    phonemesCovered:   '/api/phonemescovered',
    learn:             '/api/learn',
    exercises:         '/api/exercises/',
    checkAnswer:       '/api/checkanswer',
    homophones:        '/api/homophones/',
    reviewHomophones:  '/api/reviewhomophones',
    checkHomophAnswer: '/api/checkhomophanswer',
    saveProgress:      '/api/saveprogress',
};


// Custom error to drive app logic and to give structured info the browser console
class APIError extends Error {
    constructor(message, {status = null, kind = 'unknown', retry = false, detail = null} = {}) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.kind = kind;
        this.retry = retry;
        this.detail = detail;
    }
}


let _getToken = null;

export function setTokenProvider(fn) {
    _getToken = fn;
}


async function getAuthHeaders() {
    if (!_getToken) return {};
    const token = await _getToken();
    if (!token) return {};
    return { 'Authorization': `Bearer ${token}` };
}


async function fetchJSON(url, options = {}, timeout = 5000) {
    // Fail fast if browser knows there's no network
    if (!navigator.onLine) {
        throw new APIError('No internet connection', { kind: 'network', retry: true });
    }

    // Get auth headers BEFORE starting the timeout timer,
    // since token refresh after being offline can take time
    let authHeaders;
    try {
        authHeaders = await getAuthHeaders();
    } catch (err) {
        throw new APIError('Authentication failed — check your connection', { kind: 'network', retry: true });
    }
    options.headers = { ...authHeaders, ...(options.headers || {}) };

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);

    try {
        const resp = await fetch(url, { signal: controller.signal, ...options });
        let data = null;
        const content = resp.headers.get('content-type') || '';

        // 'content-type' can lie since it's only a claim but it's not validated
        if (content.includes('application/json')) {
            data = await resp.json();
        }

        if (!resp.ok) {
            const detail = data?.detail ?? null;
            const message = detail ? `${resp.status} - ${detail}` : `${resp.status} - ${resp.statusText}`;
            const retry = resp.status >= 500 || resp.status === 429 || resp.status === 408;
            throw new APIError(message, { status: resp.status, kind: 'http', retry, detail });
        }

        if (data === null) {
            throw new APIError('Expected JSON from server', { kind: 'parse', retry: true });
        }
        return data;
    } catch (err) {
        if (err.name === 'AbortError') throw new APIError('Request timed out', { kind: 'timeout', retry: true });
        if (err instanceof TypeError) throw new APIError('Network or CORS error', { kind: 'network', retry: true });
        if (err instanceof SyntaxError) throw new APIError('Invalid JSON from server', { kind: 'parse', retry: true });
        if (err instanceof APIError) throw err;
        throw err;
    } finally {
        clearTimeout(timer);
    }
}


async function fetchValidate({ url, type = 'object', init, timeout }) {
    const data = await fetchJSON(url, init ? { ...init } : {}, timeout);
    if (type === 'array' && !Array.isArray(data)) {
        throw new APIError('Expected array from server', { kind: 'schema', retry: false });
    }
    if (type === 'object' && (Array.isArray(data) || data === null || typeof data !== 'object')) {
        throw new APIError('Expected object from server', { kind: 'schema', retry: false });
    }
    return data;
}


function postJSON(body, extraHeaders = {}) {
    return {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...extraHeaders },
        body: JSON.stringify(body),
    };
}


// No more userId in URLs — the backend gets it from the auth token

export const fetchReviewStatus = () =>
    fetchValidate({ url: `${API_BASE}${ENDPOINTS.reviewStatus}` });

export const fetchPhonemesCovered = () =>
    fetchValidate({ url: `${API_BASE}${ENDPOINTS.phonemesCovered}`, type: 'array' });

export const fetchLearn = () =>
    fetchValidate({ url: `${API_BASE}${ENDPOINTS.learn}` });

export const fetchExercises = (phoneme) =>
    fetchValidate({ url: `${API_BASE}${ENDPOINTS.exercises}${encodeURIComponent(phoneme)}`, timeout: 60000 });

export const fetchHomophones = (phoneme) =>
    fetchValidate({ url: `${API_BASE}${ENDPOINTS.homophones}${encodeURIComponent(phoneme)}`, type: 'array' });

export const fetchReviewHomophones = () =>
    fetchValidate({ url: `${API_BASE}${ENDPOINTS.reviewHomophones}`, type: 'array' });

export const fetchReviewExercises = () =>
    fetchValidate({ url: `${API_BASE}/api/reviewexercises`, timeout: 120000 });

export const submitAnswer = (test_id, answer, idempotencyKey) =>
    fetchValidate({ url: `${API_BASE}${ENDPOINTS.checkAnswer}`, init: postJSON({ test_id, answer }, { 'Idempotency-Key': idempotencyKey }) });

export const submitHomophAnswer = (test_id, answer, idempotencyKey) =>
    fetchValidate({ url: `${API_BASE}${ENDPOINTS.checkHomophAnswer}`, init: postJSON({ test_id, answer }, { 'Idempotency-Key': idempotencyKey }) });

export const saveProgress = (phoneme) =>
    fetchValidate({ url: `${API_BASE}${ENDPOINTS.saveProgress}`, init: postJSON({ phoneme }) });

export const fetchUserName = () =>
    fetchValidate({ url: `${API_BASE}/api/username` });

export const saveUserName = (name) =>
    fetchValidate({ url: `${API_BASE}/api/username`, init: postJSON({ name }) });
