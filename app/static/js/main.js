import { setupFormHandlers } from './modules/form-handlers.js';
import { setupFieldValidations, togglePublisherFields } from './modules/ui-controls.js';

document.addEventListener('DOMContentLoaded', function() {
    // Setup role selection handling
    const roleSelect = document.getElementById('role');
    roleSelect.addEventListener('change', () => togglePublisherFields(roleSelect.value));
    
    // Initial setup
    togglePublisherFields(roleSelect.value);
    setupFormHandlers();
    setupFieldValidations();
});
