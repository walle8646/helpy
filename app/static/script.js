console.log('Helpy frontend loaded');

document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.getElementById('registerForm');
    const confirmForm = document.getElementById('confirmForm');
    
    if (!registerForm) return;

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
});
