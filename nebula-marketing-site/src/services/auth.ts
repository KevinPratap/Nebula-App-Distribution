import { apiService } from './api';

export const authService = {
    async signup(email: string, password: string) {
        const result = await apiService.register(email, password);
        if (!result.error) {
            return await this.login(email, password);
        }
        return result;
    },

    async loginWithToken(token: string) {
        // No longer using localStorage for tokens. 
        // Tokens are now set as HttpOnly cookies by the server.
        return { success: true };
    },

    async login(email: string, password: string, rememberMe: boolean = false) {
        const result = await apiService.login(email, password);
        if (result.login) {
            if (rememberMe) {
                localStorage.setItem('nebula_remember_email', email);
                localStorage.setItem('nebula_should_remember', 'true');
            } else {
                localStorage.removeItem('nebula_remember_email');
                localStorage.removeItem('nebula_should_remember');
            }
            return { success: true };
        }
        return { success: false, error: result.message || result.msg || result.error || 'Login failed' };
    },

    async logout() {
        try {
            await fetch('/auth/logout', { method: 'POST', credentials: 'include' });
        } catch (e) { }
        localStorage.removeItem('nebula_user');
        window.location.href = '/login';
    },

    isLoggedIn() {
        // Since we use cookies, sync check is limited to the user object presence
        return !!localStorage.getItem('nebula_user');
    },

    async refreshUser() {
        const data = await apiService.getUserInfo();
        // Strict check: User object MUST have an email to be valid.
        // This prevents error objects like { message: "User not found" } from being treated as success.
        if (data && !data.error && !data.message && !data.msg && data.email) {
            localStorage.setItem('nebula_user', JSON.stringify(data));
            return data;
        }

        // If we got an error message but no explicit 'error' key, normalize it
        const errorMsg = data?.message || data?.msg || data?.error || 'Failed to refresh user';
        return { error: errorMsg };
    },

    getCurrentUser() {
        const user = localStorage.getItem('nebula_user');
        return user ? JSON.parse(user) : null;
    },

    async updateProfile(displayName: string) {
        const result = await apiService.updateProfile(displayName);
        // Only treat as error if apiRequest actually returned an error key
        if (result && !result.error) {
            await this.refreshUser(); // Sync local storage
            return { success: true };
        }
        return { success: false, error: result.error || result.message || result.msg || 'Update failed' };
    }
};
