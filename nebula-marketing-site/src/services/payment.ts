// Helper to get cookie value
function getCookie(name: string): string | null {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
    return null;
}

export const paymentService = {
    async createOrder(amount: number, credits: number) {
        // Use relative path - Vite proxy handles dev, Nginx/Flask handles prod
        const csrfToken = getCookie('csrf_access_token');

        const headers: any = {
            'Content-Type': 'application/json'
        };
        if (csrfToken) {
            headers['X-CSRF-TOKEN'] = csrfToken;
        }

        const response = await fetch(`/payments/create-order`, {
            method: 'POST',
            credentials: 'include',
            headers: headers,
            body: JSON.stringify({ amount, credits })
        });
        if (!response.ok) {
            const err = await response.json();
            // Handle both standard Flask error (msg) and custom error (error)
            throw new Error(err.error || err.msg || 'Payment initialization failed');
        }
        return await response.json();
    },

    async verifyPayment(paymentData: any) {
        const csrfToken = getCookie('csrf_access_token');

        const headers: any = {
            'Content-Type': 'application/json'
        };
        if (csrfToken) {
            headers['X-CSRF-TOKEN'] = csrfToken;
        }

        const response = await fetch(`/payments/verify`, {
            method: 'POST',
            credentials: 'include',
            headers: headers,
            body: JSON.stringify(paymentData)
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.message || err.msg || 'Payment verification failed');
        }
        return await response.json();
    },

    loadRazorpay(): Promise<boolean> {
        return new Promise((resolve) => {
            const script = document.createElement('script');
            script.src = 'https://checkout.razorpay.com/v1/checkout.js';
            script.onload = () => resolve(true);
            script.onerror = () => resolve(false);
            document.body.appendChild(script);
        });
    }
};
