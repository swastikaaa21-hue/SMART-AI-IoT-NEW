// ══════════════════════════════════════════════════════════
// Configuration & Constants
// ══════════════════════════════════════════════════════════

// API Configuration
const DEFAULT_PROD_BACKEND_URL = 'https://smart-ai-iot-backend.onrender.com';
const RENDER_BACKEND_URL = localStorage.getItem('custom_backend_url') || DEFAULT_PROD_BACKEND_URL;
const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname.startsWith('10.') || window.location.hostname.startsWith('192.168.');
const LOCAL_BACKEND = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? 'http://localhost:8000' : `http://${window.location.hostname}:8000`;
const API_BASE = isLocal
    ? LOCAL_BACKEND + '/api/v1'
    : RENDER_BACKEND_URL.replace(/\/+$/, '') + '/api/v1';

function initBackendUrlSetting() {
    const el = document.getElementById('custom-backend-input');
    if (el) el.value = localStorage.getItem('custom_backend_url') || DEFAULT_PROD_BACKEND_URL;
}

function saveBackendUrl() {
    const el = document.getElementById('custom-backend-input');
    if (el && el.value.trim()) {
        const val = el.value.trim().replace(/\/+$/, '');
        localStorage.setItem('custom_backend_url', val);
        showToast('Backend URL updated! Reloading...', 'success');
        setTimeout(() => window.location.reload(), 600);
    }
}

// Auth Tokens
let authToken = localStorage.getItem('auth_token') || '';
let refreshToken = localStorage.getItem('refresh_token') || '';
let chatSessionId = localStorage.getItem('chat_session_id') || '';
let currentUser = null;
let ws = null;

// Internationalization (i18n)
const translations = {
    en: {
        home_title: 'HOME',
        schedule_title: 'SCHEDULE',
        settings_title: 'SETTINGS',
        welcome: 'Welcome',
        login: 'Login',
        register: 'Register',
        logout: 'Logout',
        // Add more translations as needed
    },
    id: {
        home_title: 'BERANDA',
        schedule_title: 'JADWAL',
        settings_title: 'PENGATURAN',
        welcome: 'Selamat Datang',
        login: 'Masuk',
        register: 'Daftar',
        logout: 'Keluar',
        // Add more translations as needed
    }
};

let currentLang = localStorage.getItem('language') || 'id';

function setLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('language', lang);
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (translations[lang] && translations[lang][key]) {
            el.textContent = translations[lang][key];
        }
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (translations[lang] && translations[lang][key]) {
            el.placeholder = translations[lang][key];
        }
    });
}
