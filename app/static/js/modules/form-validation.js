export function validateISBN(isbn) {
    return /^\d{13}$/.test(isbn);
}

export function validateEmail(email) {
    return /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email);
}

export function validateName(name) {
    return /^[a-zA-Z0-9\s\-\'\.]+$/.test(name);
}

export function validatePrice(price) {
    return /^\d+(\.\d{1,2})?$/.test(price);
}

export function validateFiles(epubFile, onixFile) {
    if (!epubFile || !onixFile) {
        return { valid: false, message: 'Both EPUB and ONIX files are required' };
    }
    
    if (!epubFile.name.endsWith('.epub')) {
        return { valid: false, message: 'Invalid EPUB file format' };
    }
    
    if (!onixFile.name.endsWith('.xml')) {
        return { valid: false, message: 'Invalid ONIX file format' };
    }
    
    return { valid: true };
}

export function validateEnhancedFields(formData) {
    const validations = [
        { field: 'sender_name', validator: validateName, message: 'Invalid Sender Name format' },
        { field: 'contact_name', validator: validateName, message: 'Invalid Contact Name format' },
        { field: 'email', validator: validateEmail, message: 'Invalid Email format' }
    ];

    for (const validation of validations) {
        const value = formData.get(validation.field);
        if (!validation.validator(value)) {
            return { valid: false, message: validation.message };
        }
    }

    const currencies = ['cad', 'gbp', 'usd'];
    for (const currency of currencies) {
        const price = formData.get(`price_${currency}`);
        if (price && !validatePrice(price)) {
            return { valid: false, message: `Invalid ${currency.toUpperCase()} Price format` };
        }
    }

    return { valid: true };
}
