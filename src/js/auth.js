// Authentication helpers for Paper Library
// Stores JWT in localStorage and sends Bearer token on API calls.

const TOKEN_KEY = 'paper_lib_token';
const USER_KEY = 'paper_lib_user';

export function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
}

export function getUser() {
    try {
        return JSON.parse(localStorage.getItem(USER_KEY) || 'null');
    } catch {
        return null;
    }
}

export function setUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function isLoggedIn() {
    return !!getToken();
}

export function isAdmin() {
    const user = getUser();
    return !!(user && user.is_admin);
}

export async function login(username, password) {
    const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
    });

    const data = await response.json();
    if (!response.ok || !data.success) {
        throw new Error(data.detail || data.error || 'Login failed');
    }

    setToken(data.token);
    setUser(data.user);
    return data;
}

export async function logout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
    } catch (err) {
        console.error('Logout error:', err);
    }
    clearToken();
}

export async function fetchCurrentUser() {
    const token = getToken();
    if (!token) return null;

    try {
        const response = await fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        const data = await response.json();
        if (data.user) {
            setUser(data.user);
            return data.user;
        }
        clearToken();
        return null;
    } catch (err) {
        console.error('fetchCurrentUser error:', err);
        return null;
    }
}

export async function apiFetch(url, options = {}) {
    const token = getToken();
    const headers = { ...(options.headers || {}) };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    if (!headers['Accept']) {
        headers['Accept'] = 'application/json';
    }

    const response = await fetch(url, { ...options, headers });

    if (response.status === 401) {
        clearToken();
        if (window.location.pathname !== '/login' && window.location.pathname !== '/login/') {
            window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname + window.location.search);
        }
        throw new Error('Unauthorized');
    }

    return response;
}

export function requireAuth() {
    if (!isLoggedIn()) {
        window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname + window.location.search);
        return false;
    }
    return true;
}

export function requireAdmin() {
    if (!isLoggedIn() || !isAdmin()) {
        window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname + window.location.search);
        return false;
    }
    return true;
}
