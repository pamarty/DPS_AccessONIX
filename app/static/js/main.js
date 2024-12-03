document.addEventListener('DOMContentLoaded', function() {
    // Form handling
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
    
    if (role === 'publisher') {
        publisherFields.style.display = 'block';
        requiredFields.forEach(field => {
            field.required = true;
        });
    } else {
        publisherFields.style.display = 'none';
        requiredFields.forEach(field => {
            field.required = false;
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
    
    // Publisher role specific validations
    if (role === 'publisher') {
        if (!validatePublisherFields()) {
            return false;
        }
    }
    
    return true;
}

function validatePublisherFields() {
    const namePattern = /^[a-zA-Z0-9\s\-\'\.]+$/;
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    const pricePattern = /^\d+(\.\d{1,2})?$/;
    
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
            showError(`Invalid ${currency.toUpperCase()} Price format`);
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
        // Create download link
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
    // Add real-time validation for ISBN
    const isbnField = document.getElementById('epub_isbn');
    isbnField.addEventListener('input', function() {
        this.value = this.value.replace(/[^\d]/g, '');
        if (this.value.length > 13) {
            this.value = this.value.slice(0, 13);
        }
    });
    
    // Add real-time validation for prices
    const priceFields = document.querySelectorAll('input[id^="price_"]');
    priceFields.forEach(field => {
        field.addEventListener('input', function() {
            this.value = this.value.replace(/[^\d.]/g, '');
            const parts = this.value.split('.');
            if (parts.length > 2) {
                this.value = parts[0] + '.' + parts.slice(1).join('');
            }
            if (parts[1] && parts[1].length > 2) {
                this.value = parts[0] + '.' + parts[1].slice(0, 2);
            }
        });
    });
}