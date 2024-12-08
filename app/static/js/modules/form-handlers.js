import { validateFiles, validateEnhancedFields, validateISBN } from './form-validation.js';
import { showError, showLoadingIndicator, hideLoadingIndicator } from './ui-controls.js';
import { getDownloadFilename } from './utils.js';

export function setupFormHandlers() {
    const form = document.getElementById('onixForm');
    form.addEventListener('submit', handleFormSubmit);
}

async function handleFormSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const role = formData.get('role');
    
    // Validate ISBN
    if (!validateISBN(formData.get('epub_isbn'))) {
        showError('ISBN must be 13 digits');
        return;
    }
    
    // Validate files
    const fileValidation = validateFiles(
        formData.get('epub_file'),
        formData.get('onix_file')
    );
    if (!fileValidation.valid) {
        showError(fileValidation.message);
        return;
    }
    
    // Validate enhanced fields if necessary
    if (role === 'enhanced') {
        const enhancedValidation = validateEnhancedFields(formData);
        if (!enhancedValidation.valid) {
            showError(enhancedValidation.message);
            return;
        }
    }
    
    // Submit form if all validations pass
    showLoadingIndicator();
    try {
        await submitForm(formData);
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoadingIndicator();
    }
}

async function submitForm(formData) {
    const response = await fetch('/process', {
        method: 'POST',
        body: formData
    });

    if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || data.errors.join('\n'));
    }

    const blob = await response.blob();
    downloadFile(blob);
}

function downloadFile(blob) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = getDownloadFilename();
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}
