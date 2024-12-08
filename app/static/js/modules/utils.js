export function getDownloadFilename() {
    const isbn = document.getElementById('epub_isbn').value;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '');
    return `AccessONIX_${isbn}_${timestamp}.xml`;
}

export function formatDate(date) {
    return date.toISOString().replace(/[:.]/g, '');
}

export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
