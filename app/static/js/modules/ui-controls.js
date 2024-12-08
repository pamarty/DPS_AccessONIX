export function togglePublisherFields(role) {
    const publisherFields = document.getElementById('publisher-fields');
    const requiredFields = publisherFields.querySelectorAll('input, select');
    
    if (role === 'enhanced') {
        publisherFields.style.display = 'block';
        requiredFields.forEach(field => field.required = true);
    } else {
        publisherFields.style.display = 'none';
        requiredFields.forEach(field => {
            field.required = false;
            field.value = '';
        });
    }
}

export function showLoadingIndicator() {
    const submitButton = document.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="spinner"></span> Processing...';
}

export function hideLoadingIndicator() {
    const submitButton = document.querySelector('button[type="submit"]');
    submitButton.disabled = false;
    submitButton.innerHTML = 'Generate ONIX';
}

export function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-error';
    errorDiv.textContent = message;
    
    const form = document.getElementById('onixForm');
    form.insertBefore(errorDiv, form.firstChild);
    
    setTimeout(() => errorDiv.remove(), 5000);
}

export function setupFieldValidations() {
    setupISBNValidation();
    setupPriceValidation();
    setupEmailValidation();
}

function setupISBNValidation() {
    const isbnField = document.getElementById('epub_isbn');
    isbnField.addEventListener('input', function() {
        this.value = this.value.replace(/[^\d]/g, '').slice(0, 13);
    });
}

function setupPriceValidation() {
    const priceFields = document.querySelectorAll('input[id^="price_"]');
    priceFields.forEach(field => {
        field.addEventListener('input', function() {
            this.value = formatPrice(this.value);
        });
    });
}

function setupEmailValidation() {
    const emailField = document.getElementById('email');
    emailField.addEventListener('input', function() {
        const isValid = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(this.value);
        this.classList.toggle('is-invalid', !isValid);
    });
}

function formatPrice(value) {
    value = value.replace(/[^\d.]/g, '');
    const parts = value.split('.');
    if (parts.length > 2) {
        return parts[0] + '.' + parts.slice(1).join('');
    }
    if (parts[1] && parts[1].length > 2) {
        return parts[0] + '.' + parts[1].slice(0, 2);
    }
    return value;
}
