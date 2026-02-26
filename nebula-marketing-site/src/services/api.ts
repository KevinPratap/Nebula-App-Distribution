const API_BASE = ''; // Use relative paths for production reliability

// Helper to get cookie value
function getCookie(name: string): string | null {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
    return null;
}

// Helper for standardized API calls
async function apiRequest(url: string, data?: any, method: 'GET' | 'POST' = 'POST') {
    try {
        const csrfToken = getCookie('csrf_access_token');
        const headers: any = { 'Content-Type': 'application/json' };
        if (csrfToken && method === 'POST') headers['X-CSRF-TOKEN'] = csrfToken;

        const options: any = {
            method,
            headers,
            credentials: 'include'
        };
        if (data && method === 'POST') options.body = JSON.stringify(data);

        const response = await fetch(`${API_BASE}${url}`, options);
        const result = await response.json();

        if (!response.ok) {
            return { error: result.message || result.error || 'Request failed' };
        }
        return result;
    } catch (error) {
        return { error: 'Connection failed' };
    }
}

export const apiService = {
    async register(email: string, password: string) {
        return await apiRequest('/register', { email, password });
    },

    async login(email: string, password: string) {
        return await apiRequest('/login', { email, password });
    },

    async getUserInfo() {
        return await apiRequest('/me', undefined, 'GET');
    },

    async updateProfile(displayName: string) {
        return await apiRequest('/update_profile', { display_name: displayName });
    },

    async getTransactions() {
        return await apiRequest('/api/me/transactions', undefined, 'GET');
    },

    async changePassword(newPassword: string) {
        return await apiRequest('/auth/change-password', { new_password: newPassword });
    },

    async toggle2FA(enabled: boolean) {
        return await apiRequest('/auth/toggle-2fa', { enabled });
    },

    async requestPasswordReset(email: string) {
        return await apiRequest('/auth/forgot-password', { email });
    },

    async resetPassword(data: any) {
        return await apiRequest('/auth/reset-password', data);
    },

    async deleteAccount() {
        return await apiRequest('/auth/delete-account', {});
    }
};
