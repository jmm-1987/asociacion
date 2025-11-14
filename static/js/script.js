// JavaScript personalizado para la Asociación de Vecinos

document.addEventListener('DOMContentLoaded', function() {
    // Auto-ocultar alertas flash después de 5 segundos
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Confirmar acciones destructivas
    const deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            const message = button.getAttribute('data-confirm-delete') || '¿Estás seguro de que deseas realizar esta acción?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // Validación de formularios
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (!validateForm(form)) {
                e.preventDefault();
            }
        });
    });
    
    // Mejorar experiencia de usuario con loading states (SOLO para formularios específicos)
    const submitButtons = document.querySelectorAll('button[type="submit"]:not([data-no-loading])');
    submitButtons.forEach(function(button) {
        const originalText = button.innerHTML;
        
        button.addEventListener('click', function() {
            const form = button.closest('form');
            if (form && form.checkValidity()) {
                // Solo aplicar loading a formularios de creación/edición, no a cancelar/marcar asistencia
                const formAction = form.action.toLowerCase();
                if (formAction.includes('crear') || formAction.includes('editar') || formAction.includes('nuevo')) {
                    button.disabled = true;
                    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Procesando...';
                    
                    // Restaurar el botón después de 10 segundos por si hay un error
                    setTimeout(function() {
                        if (button.disabled) {
                            button.disabled = false;
                            button.innerHTML = originalText;
                        }
                    }, 10000);
                }
            }
        });
    });
    
    // Tooltips de Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Popovers de Bootstrap
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Animaciones de entrada
    const animatedElements = document.querySelectorAll('.fade-in');
    animatedElements.forEach(function(element) {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        
        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        });
        
        observer.observe(element);
    });
});

// Función para validar formularios
function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(function(field) {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });
    
    // Validación de email
    const emailFields = form.querySelectorAll('input[type="email"]');
    emailFields.forEach(function(field) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (field.value && !emailRegex.test(field.value)) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });
    
    // Validación de fechas
    const dateFields = form.querySelectorAll('input[type="date"]');
    dateFields.forEach(function(field) {
        if (field.value) {
            const selectedDate = new Date(field.value);
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            
            if (selectedDate < today) {
                field.classList.add('is-invalid');
                isValid = false;
            } else {
                field.classList.remove('is-invalid');
            }
        }
    });
    
    return isValid;
}

// Función para confirmar eliminación
function confirmarEliminar(id, nombre) {
    const modal = document.getElementById('modalEliminar');
    const nombreElement = document.getElementById('nombreActividad');
    const form = document.getElementById('formEliminar');
    
    if (nombreElement) {
        nombreElement.textContent = nombre;
    }
    
    if (form) {
        form.action = form.action.replace('0', id);
    }
    
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

// Función para mostrar notificaciones toast
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remover el toast del DOM después de que se oculte
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

// Función para crear el contenedor de toasts
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '1055';
    document.body.appendChild(container);
    return container;
}

// Función para formatear fechas
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// Función para formatear fechas y horas
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('es-ES', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Función para copiar al portapapeles
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showToast('Copiado al portapapeles', 'success');
    }).catch(function() {
        showToast('Error al copiar', 'danger');
    });
}

// Función para exportar datos a CSV
function exportToCSV(data, filename) {
    const csvContent = data.map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// Utilidades para el manejo de estados
const StateManager = {
    // Guardar estado en localStorage
    save: function(key, data) {
        try {
            localStorage.setItem(key, JSON.stringify(data));
        } catch (e) {
            console.warn('No se pudo guardar el estado:', e);
        }
    },
    
    // Cargar estado desde localStorage
    load: function(key, defaultValue = null) {
        try {
            const data = localStorage.getItem(key);
            return data ? JSON.parse(data) : defaultValue;
        } catch (e) {
            console.warn('No se pudo cargar el estado:', e);
            return defaultValue;
        }
    },
    
    // Eliminar estado
    remove: function(key) {
        localStorage.removeItem(key);
    }
};

// Manejo de errores global
window.addEventListener('error', function(e) {
    console.error('Error:', e.error);
    showToast('Ha ocurrido un error inesperado', 'danger');
});

// Manejo de errores de promesas no capturadas
window.addEventListener('unhandledrejection', function(e) {
    console.error('Promise rejected:', e.reason);
    showToast('Ha ocurrido un error inesperado', 'danger');
});
