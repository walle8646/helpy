console.log('Helpy frontend loaded');

document.addEventListener('DOMContentLoaded', () => {
    // Registration form handler
    const registerForm = document.getElementById('registerForm');
    const confirmForm = document.getElementById('confirmForm');
    
    if (registerForm && confirmForm) {
        const registerStep = document.getElementById('registerStep');
        const confirmStep = document.getElementById('confirmStep');
        const successStep = document.getElementById('successStep');
        const errorDiv = document.getElementById('errorMessage');
        const confirmErrorDiv = document.getElementById('confirmErrorMessage');
        const userEmailSpan = document.getElementById('userEmail');

        let registeredEmail = '';

        // Step 1: Registration
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            errorDiv.style.display = 'none';

            const formData = new FormData(registerForm);
            registeredEmail = formData.get('email');
            
            try {
                const response = await fetch('/api/register', {
                    method: 'POST',
                    body: new URLSearchParams(formData)
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    // Success: show confirmation step
                    registerStep.style.display = 'none';
                    confirmStep.style.display = 'block';
                    userEmailSpan.textContent = registeredEmail;
                } else {
                    errorDiv.textContent = data.error || 'Registration failed. Please try again.';
                    errorDiv.style.display = 'block';
                }
            } catch (error) {
                errorDiv.textContent = 'An error occurred. Please try again later.';
                errorDiv.style.display = 'block';
                console.error('Error:', error);
            }
        });

        // Step 2: Confirmation
        confirmForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            confirmErrorDiv.style.display = 'none';

            const formData = new FormData(confirmForm);
            formData.append('email', registeredEmail);
            
            try {
                const response = await fetch('/api/confirm', {
                    method: 'POST',
                    body: new URLSearchParams(formData)
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    // Success: show welcome message
                    confirmStep.style.display = 'none';
                    successStep.style.display = 'block';
                } else {
                    confirmErrorDiv.textContent = data.error || 'Invalid code. Please try again.';
                    confirmErrorDiv.style.display = 'block';
                }
            } catch (error) {
                confirmErrorDiv.textContent = 'An error occurred. Please try again later.';
                confirmErrorDiv.style.display = 'block';
                console.error('Error:', error);
            }
        });
    }

    // Login form handler
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        console.log('Login form found'); // DEBUG
        const errorDiv = document.getElementById('errorMessage');
        const emailNotFoundDiv = document.getElementById('emailNotFound');
        const wrongPasswordDiv = document.getElementById('wrongPassword');
        const resetPasswordLink = document.getElementById('resetPasswordLink');
        let userEmail = '';

        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log('Login form submitted');
            errorDiv.style.display = 'none';
            emailNotFoundDiv.style.display = 'none';
            wrongPasswordDiv.style.display = 'none';

            const formData = new FormData(loginForm);
            userEmail = formData.get('email');
            
            console.log('Sending login request for:', userEmail);

            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    body: new URLSearchParams(formData)
                });

                console.log('Response status:', response.status);
                const data = await response.json();
                console.log('Response data:', data);

                if (response.ok) {
                    // Salva il token in localStorage
                    localStorage.setItem('session_token', data.token);
                    console.log('Token saved to localStorage');
                    console.log('Redirecting to:', data.redirect);
                    window.location.href = data.redirect;
                } else {
                    if (data.error === 'email_not_found') {
                        emailNotFoundDiv.style.display = 'block';
                    } else if (data.error === 'wrong_password') {
                        wrongPasswordDiv.style.display = 'block';
                        resetPasswordLink.href = `/reset-password?email=${userEmail}`;
                    } else {
                        errorDiv.textContent = data.error || 'Login failed';
                        errorDiv.style.display = 'block';
                    }
                }
            } catch (error) {
                errorDiv.textContent = 'An error occurred. Please try again.';
                errorDiv.style.display = 'block';
                console.error('Error:', error);
            }
        });
    }

    // Password reset request
    const requestResetForm = document.getElementById('requestResetForm');
    if (requestResetForm) {
        const requestStep = document.getElementById('requestStep');
        const resetStep = document.getElementById('resetStep');
        const errorDiv = document.getElementById('errorMessage');
        let resetEmail = '';

        requestResetForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            errorDiv.style.display = 'none';

            const formData = new FormData(requestResetForm);
            resetEmail = formData.get('email');

            try {
                const response = await fetch('/api/request-password-reset', {
                    method: 'POST',
                    body: new URLSearchParams(formData)
                });

                const data = await response.json();

                if (response.ok) {
                    requestStep.style.display = 'none';
                    resetStep.style.display = 'block';
                } else {
                    errorDiv.textContent = data.error || 'Failed to send reset code';
                    errorDiv.style.display = 'block';
                }
            } catch (error) {
                errorDiv.textContent = 'An error occurred. Please try again.';
                errorDiv.style.display = 'block';
                console.error('Error:', error);
            }
        });

        // Reset password with code
        const resetPasswordForm = document.getElementById('resetPasswordForm');
        if (resetPasswordForm) {
            const resetErrorDiv = document.getElementById('resetErrorMessage');
            const successDiv = document.getElementById('successMessage');

            resetPasswordForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                resetErrorDiv.style.display = 'none';
                successDiv.style.display = 'none';

                const formData = new FormData(resetPasswordForm);
                formData.append('email', resetEmail);

                try {
                    const response = await fetch('/api/reset-password', {
                        method: 'POST',
                        body: new URLSearchParams(formData)
                    });

                    const data = await response.json();

                    if (response.ok) {
                        successDiv.textContent = 'Password updated! Redirecting to login...';
                        successDiv.style.display = 'block';
                        setTimeout(() => {
                            window.location.href = '/login';
                        }, 2000);
                    } else {
                        resetErrorDiv.textContent = data.error || 'Failed to reset password';
                        resetErrorDiv.style.display = 'block';
                    }
                } catch (error) {
                    resetErrorDiv.textContent = 'An error occurred. Please try again.';
                    resetErrorDiv.style.display = 'block';
                    console.error('Error:', error);
                }
            });
        }
    }

    // Intercetta tutte le richieste fetch e aggiungi il token
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        const token = localStorage.getItem('session_token');
        if (token && args[1]) {
            args[1].headers = {
                ...args[1].headers,
                'Authorization': `Bearer ${token}`
            };
        }
        return originalFetch.apply(this, args);
    };
});
