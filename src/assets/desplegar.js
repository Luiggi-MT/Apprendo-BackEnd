const menuBtn = document.getElementById('menuBtn');
const closeBtn = document.getElementById('closeBtn');
const sidebar = document.getElementById('sidebar');
const brandBlock = document.getElementById('brandBlock');

if (menuBtn && sidebar) {
    menuBtn.addEventListener('click', () => {
        sidebar.classList.remove('-translate-x-full');
        if (brandBlock) {
            brandBlock.classList.add('translate-x-20');
        }
    });
}

if (closeBtn && sidebar) {
    closeBtn.addEventListener('click', () => {
        sidebar.classList.add('-translate-x-full');
        if (brandBlock) {
            brandBlock.classList.remove('translate-x-20');
        }
    });
}