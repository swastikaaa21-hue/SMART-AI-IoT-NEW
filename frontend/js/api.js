// ══════════════════════════════════════════════════════════
// API Helper Functions
// ══════════════════════════════════════════════════════════

async function api(method, endpoint, body = null) {
    const url = `${API_BASE}${endpoint}`;
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        },
    };

    if (authToken) {
        options.headers['Authorization'] = `Bearer ${authToken}`;
    }

    if (body) {
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(url, options);
        
        // Handle 401 Unauthorized
        if (response.status === 401) {
            // Token expired, clear and redirect to login
            localStorage.removeItem('auth_token');
            localStorage.removeItem('refresh_token');
            authToken = '';
            refreshToken = '';
            if (state.activePage !== 'login' && state.activePage !== 'register') {
                showToast('Session expired. Please login again.', 'error');
                navigate('login');
            }
        }
        
        return response;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}
