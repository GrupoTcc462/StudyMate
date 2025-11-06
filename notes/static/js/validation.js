/**
 * VALIDAÇÕES CENTRALIZADAS PARA O MÓDULO NOTES
 * StudyMate - ETEC João Maria Stevanatto
 */

// ========================================
// REGEX PATTERNS
// ========================================
const VALIDATION_PATTERNS = {
    // Apenas letras (com acentos), espaços
    textOnly: /^[A-Za-zÀ-ÿÇç\s]*$/,
    
    // Letras, espaços e pontuação básica
    textWithPunctuation: /^[A-Za-zÀ-ÿÇç\s.,!?;:\-()'"]*$/,
    
    // URL válida
    url: /^(https?:\/\/)[\w\-]+(\.[\w\-]+)+[/#?]?.*$/
};

// ========================================
// FUNÇÕES DE VALIDAÇÃO
// ========================================

/**
 * Valida se o título contém apenas letras e espaços
 * @param {string} title - Título a validar
 * @returns {boolean}
 */
function validateTitle(title) {
    if (!title || title.length > 50) {
        return false;
    }
    return VALIDATION_PATTERNS.textOnly.test(title);
}

/**
 * Valida se a descrição está dentro dos limites
 * @param {string} description - Descrição a validar
 * @returns {boolean}
 */
function validateDescription(description) {
    if (description && description.length > 400) {
        return false;
    }
    return !description || VALIDATION_PATTERNS.textWithPunctuation.test(description);
}

/**
 * Valida formato de URL
 * @param {string} url - URL a validar
 * @returns {boolean}
 */
function validateURL(url) {
    return VALIDATION_PATTERNS.url.test(url);
}

/**
 * Valida comentário
 * @param {string} text - Texto do comentário
 * @returns {boolean}
 */
function validateComment(text) {
    if (!text || text.length > 400) {
        return false;
    }
    return VALIDATION_PATTERNS.textWithPunctuation.test(text);
}

// ========================================
// CONTADORES DE CARACTERES
// ========================================

/**
 * Configura contador de caracteres para um campo
 * @param {HTMLElement} input - Campo de input
 * @param {HTMLElement} counter - Elemento do contador
 * @param {number} maxLength - Tamanho máximo
 * @param {function} validator - Função de validação
 */
function setupCharCounter(input, counter, maxLength, validator) {
    if (!input || !counter) return;
    
    input.addEventListener('input', function() {
        const len = this.value.length;
        counter.textContent = `${len}/${maxLength}`;
        
        // Validar caracteres
        if (validator && !validator(this.value)) {
            this.style.borderColor = '#dc3545';
        } else {
            this.style.borderColor = '#e9ecef';
        }
        
        // Destacar quando atingir limite
        if (len >= maxLength) {
            counter.style.color = '#dc3545';
            counter.style.fontWeight = '600';
        } else {
            counter.style.color = '#6c757d';
            counter.style.fontWeight = '400';
        }
        
        // Bloquear entrada acima do limite
        if (len > maxLength) {
            this.value = this.value.substring(0, maxLength);
        }
    });
}

// ========================================
// FEEDBACK VISUAL
// ========================================

/**
 * Destaca campo com erro
 * @param {HTMLElement} field - Campo a destacar
 * @param {string} message - Mensagem de erro (opcional)
 */
function highlightFieldError(field, message) {
    field.style.borderColor = '#8ecae6';
    field.focus();
    
    if (message) {
        showToast(message, 'error');
    }
    
    setTimeout(() => {
        field.style.borderColor = '#e9ecef';
    }, 2000);
}

/**
 * Exibe toast de notificação
 * @param {string} message - Mensagem a exibir
 * @param {string} type - Tipo: 'success' ou 'error'
 */
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: white;
        border-left: 4px solid ${type === 'error' ? '#dc3545' : '#28a745'};
        border-radius: 8px;
        padding: 15px 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        z-index: 9999;
        animation: slideIn 0.3s ease;
        max-width: 350px;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ========================================
// VALIDAÇÃO DE CAMPOS OBRIGATÓRIOS
// ========================================

/**
 * Valida campos obrigatórios de um formulário
 * @param {HTMLFormElement} form - Formulário a validar
 * @returns {boolean}
 */
function validateRequiredFields(form) {
    const requiredFields = form.querySelectorAll('[required]');
    const emptyFields = [];
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            emptyFields.push(field);
            highlightFieldError(field);
        }
    });
    
    if (emptyFields.length > 0) {
        showToast('Você esqueceu de preencher todos os campos obrigatórios.', 'error');
        return false;
    }
    
    return true;
}

// ========================================
// EXPORTAR PARA USO GLOBAL
// ========================================
window.NotesValidation = {
    validateTitle,
    validateDescription,
    validateURL,
    validateComment,
    setupCharCounter,
    highlightFieldError,
    showToast,
    validateRequiredFields,
    patterns: VALIDATION_PATTERNS
};