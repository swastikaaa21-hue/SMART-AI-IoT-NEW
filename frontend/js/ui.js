// ══════════════════════════════════════════════════════════
// UI Helper Functions (Toast, Modals, etc.)
// ══════════════════════════════════════════════════════════

// Toast Notification
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        info: 'bg-blue-500',
        warning: 'bg-yellow-500',
    };
    toast.className = `fixed top-4 right-4 ${colors[type]} text-white px-6 py-3 rounded-lg shadow-lg z-[200] transition-all transform translate-x-0`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.transform = 'translateX(400px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Modal Functions
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        setTimeout(() => {
            const content = modal.querySelector('[id$="-content"]');
            if (content) {
                content.classList.remove('scale-95', 'opacity-0');
                content.classList.add('scale-100', 'opacity-100');
            }
        }, 10);
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        const content = modal.querySelector('[id$="-content"]');
        if (content) {
            content.classList.remove('scale-100', 'opacity-100');
            content.classList.add('scale-95', 'opacity-0');
        }
        setTimeout(() => {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }, 300);
    }
}

// Device Type Metadata
function getDeviceMeta(type) {
    const meta = {
        tv: { icon: 'fa-tv', color: 'bg-purple-500 text-white' },
        ac: { icon: 'fa-snowflake', color: 'bg-blue-500 text-white' },
        light: { icon: 'fa-lightbulb', color: 'bg-yellow-500 text-white' },
        fan: { icon: 'fa-fan', color: 'bg-cyan-500 text-white' },
        plug: { icon: 'fa-plug', color: 'bg-green-500 text-white' },
        camera: { icon: 'fa-video', color: 'bg-red-500 text-white' },
        door: { icon: 'fa-door-open', color: 'bg-indigo-500 text-white' },
        cooker: { icon: 'fa-fire-burner', color: 'bg-orange-500 text-white' },
        projector: { icon: 'fa-tv', color: 'bg-gray-500 text-white' }
    };
    return meta[type?.toLowerCase()] || { icon: 'fa-microchip', color: 'bg-gray-500 text-white' };
}
