document.addEventListener('DOMContentLoaded', function() {
    const onixForm = document.getElementById('onixForm');
    const roleSelect = document.getElementById('role');
    const publisherFields = document.getElementById('publisher-fields');
    
    // Role selection handling
    roleSelect.addEventListener('change', function() {
        togglePublisherFields(this.value);
    });
    
    // Initial state setup
    togglePublisherFields(roleSelect.value);
    
    // Form submission handling
    onixForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (validateForm()) {
            showLoadingIndicator();
            submitForm();
        }
    });
    
    // Field validations
    setupFieldValidations();
});

function togglePublisherFields(role) {
    const publisherFields = document.getElementById('publisher-fields');
    const requiredFields = publisherFields.querySelectorAll('input, select');
    
    if (role === 'enhanced') {
        publisherFields.style.display = 'block';
        requiredFields.forEach(field => {
            if (field.id !== 'price_cad' && field.id !== 'price_gbp' && field.id !== 'price_usd') {
                field.required = true;
            }
        });
    } else {
        publisherFields.style.display = 'none';
        requiredFields.forEach(field => {
            field.required = false;
            field.value = '';
        });
    }
}

// Rest of the existing functions remain the same, but add:

function setupFieldValidations() {
    // Add real-time validation for ISBN
    const isbnField = document.getElementById('epub_isbn');
    isbnField.addEventListener('input', function() {
        this.value = this.value.replace(/[^\d]/g, '');
        if (this.value.length > 13) {
            this.value = this.value.slice(0, 13);
        }
    });
    
    // Add real-time validation for email
    const emailField = document.getElementById('email');
    emailField.addEventListener('input', function() {
        const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (this.value && !emailPattern.test(this.value)) {
            this.classList.add('is-invalid');
            if (!this.nextElementSibling?.classList.contains('invalid-feedback')) {
                const feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                feedback.textContent = 'Please enter a valid email address';
                this.parentNode.insertBefore(feedback, this.nextElementSibling);
            }
        } else {
            this.classList.remove('is-invalid');
            const feedback = this.nextElementSibling;
            if (feedback?.classList.contains('invalid-feedback')) {
                feedback.remove();
            }
        }
    });
    
    // Add real-time validation for prices
    const priceFields = document.querySelectorAll('input[id^="price_"]');
    priceFields.forEach(field => {
        field.addEventListener('input', function(e) {
            let value = this.value;
            
            // Remove any characters that aren't numbers or decimal point
            value = value.replace(/[^\d.]/g, '');
            
            // Ensure only one decimal point
            const parts = value.split('.');
            if (parts.length > 2) {
                value = parts[0] + '.' + parts.slice(1).join('');
            }
            
            // Limit to 2 decimal places
            if (parts[1] && parts[1].length > 2) {
                value = parts[0] + '.' + parts[1].slice(0, 2);
            }
            
            this.value = value;
        });
    });
}