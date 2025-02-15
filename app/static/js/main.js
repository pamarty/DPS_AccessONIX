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
    const requiredFields = publisherFields.querySelectorAll('input[required], select[required]');
    
    if (role === 'enhanced') {
        publisherFields.style.display = 'block';
        requiredFields.forEach(field => {
            field.required = true;
        });
    } else {
        publisherFields.style.display = 'none';
        requiredFields.forEach(field => {
            field.required = false;
            field.value = '';
        });
    }
}

function validateForm() {
    const form = document.getElementById('onixForm');
    const role = document.getElementById('role').value;
    
    // Basic validations
    const isbnField = document.getElementById('epub_isbn');
    if (!/^\d{13}$/.test(isbnField.value)) {
        showError('ISBN must be 13 digits');
        return false;
    }
    
    // File validations
    const epubFile = document.getElementById('epub_file').files[0];
    const onixFile = document.getElementById('onix_file').files[0];
    
    if (!epubFile || !onixFile) {
        showError('Both EPUB and ONIX files are required');
        return false;
    }
    
    if (!epubFile.name.endsWith('.epub')) {
        showError('Invalid EPUB file format');
        return false;
    }
    
    if (!onixFile.name.endsWith('.xml')) {
        showError('Invalid ONIX file format');
        return false;
    }
    
    // Enhanced role specific validations
    if (role === 'enhanced') {
        if (!validateEnhancedFields()) {
            return false;
        }
    }
    
    return true;
}

function validateEnhancedFields() {
    const namePattern = /^[a-zA-Z0-9\s\-\'\.]+$/;
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    const pricePattern = /^\d*\.?\d{0,2}$/;
    
    // Validate sender information
    const senderName = document.getElementById('sender_name').value;
    const contactName = document.getElementById('contact_name').value;
    const email = document.getElementById('email').value;
    
    if (!namePattern.test(senderName)) {
        showError('Invalid Sender Name format');
        return false;
    }
    
    if (!namePattern.test(contactName)) {
        showError('Invalid Contact Name format');
        return false;
    }
    
    if (!emailPattern.test(email)) {
        showError('Invalid Email format');
        return false;
    }
    
    // Validate prices
    const currencies = ['cad', 'gbp', 'usd'];
    for (const currency of currencies) {
        const price = document.getElementById(`price_${currency}`).value;
        if (price && !pricePattern.test(price)) {
            showError(`Invalid ${currency.toUpperCase()} Price format. Use format: 99.99`);
            return false;
        }
    }
    
    return true;
}

function showLoadingIndicator() {
    const submitButton = document.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="spinner"></span> Processing...';
}

function hideLoadingIndicator() {
    const submitButton = document.querySelector('button[type="submit"]');
    submitButton.disabled = false;
    submitButton.innerHTML = 'Generate ONIX';
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-error';
    errorDiv.textContent = message;
    
    const form = document.getElementById('onixForm');
    form.insertBefore(errorDiv, form.firstChild);
    
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

function submitForm() {
    const form = document.getElementById('onixForm');
    const formData = new FormData(form);
    
    fetch('/process', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || data.errors.join('\n'));
            });
        }
        return response.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = getDownloadFilename();
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        hideLoadingIndicator();
    })
    .catch(error => {
        showError(error.message);
        hideLoadingIndicator();
    });
}

function getDownloadFilename() {
    const isbn = document.getElementById('epub_isbn').value;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '');
    return `AccessONIX_${isbn}_${timestamp}.xml`;
}

function setupFieldValidations() {
    // ISBN validation
    const isbnField = document.getElementById('epub_isbn');
    isbnField.addEventListener('input', function() {
        this.value = this.value.replace(/[^\d]/g, '');
        if (this.value.length > 13) {
            this.value = this.value.slice(0, 13);
        }
    });
    
    // Email validation
    const emailField = document.getElementById('email');
    if (emailField) {
        emailField.addEventListener('input', function() {
            const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
            const isValid = !this.value || emailPattern.test(this.value);
            this.classList.toggle('is-invalid', !isValid);
            
            let feedback = this.nextElementSibling;
            if (!isValid) {
                if (!feedback || !feedback.classList.contains('invalid-feedback')) {
                    feedback = document.createElement('div');
                    feedback.className = 'invalid-feedback';
                    this.parentNode.insertBefore(feedback, this.nextElementSibling);
                }
                feedback.textContent = 'Please enter a valid email address';
            } else if (feedback && feedback.classList.contains('invalid-feedback')) {
                feedback.remove();
            }
        });
    }
    
    // Price validation
    const priceFields = document.querySelectorAll('input[id^="price_"]');
    priceFields.forEach(field => {
        field.addEventListener('input', function() {
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