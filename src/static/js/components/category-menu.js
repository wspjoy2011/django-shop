document.addEventListener('DOMContentLoaded', function () {
    const categoriesDropdown = document.querySelector('.categories-dropdown');
    const categoriesMenu = categoriesDropdown?.querySelector('.categories-menu');

    if (!categoriesDropdown || !categoriesMenu) {
        return;
    }

    let activeTimeouts = new Map();

    function setupDesktopHover() {
        if (window.innerWidth > 991) {
            const submenus = categoriesMenu.querySelectorAll('.dropdown-submenu');

            submenus.forEach(submenu => {
                const submenuDropdown = submenu.querySelector('.submenu');
                if (!submenuDropdown) return;

                const hoverArea = {
                    parent: submenu,
                    child: submenuDropdown
                };

                submenu.addEventListener('mouseenter', function () {
                    if (activeTimeouts.has(hoverArea)) {
                        clearTimeout(activeTimeouts.get(hoverArea));
                        activeTimeouts.delete(hoverArea);
                    }

                    const siblings = submenu.parentElement.querySelectorAll('.dropdown-submenu');
                    siblings.forEach(sibling => {
                        if (sibling !== submenu) {
                            const siblingMenu = sibling.querySelector('.submenu');
                            if (siblingMenu) {
                                siblingMenu.style.display = 'none';
                                siblingMenu.style.opacity = '0';
                                siblingMenu.style.visibility = 'hidden';
                            }
                        }
                    });

                    submenuDropdown.style.display = 'block';
                    submenuDropdown.style.opacity = '1';
                    submenuDropdown.style.visibility = 'visible';
                });

                submenu.addEventListener('mouseleave', function (e) {
                    const rect = submenuDropdown.getBoundingClientRect();
                    const mouseX = e.clientX;
                    const mouseY = e.clientY;

                    const movingToSubmenu = mouseX >= rect.left - 10 && mouseX <= rect.right + 10 &&
                        mouseY >= rect.top - 10 && mouseY <= rect.bottom + 10;

                    const delay = movingToSubmenu ? 300 : 100;

                    const timeoutId = setTimeout(() => {
                        submenuDropdown.style.display = 'none';
                        submenuDropdown.style.opacity = '0';
                        submenuDropdown.style.visibility = 'hidden';
                        activeTimeouts.delete(hoverArea);
                    }, delay);

                    activeTimeouts.set(hoverArea, timeoutId);
                });

                submenuDropdown.addEventListener('mouseenter', function () {
                    if (activeTimeouts.has(hoverArea)) {
                        clearTimeout(activeTimeouts.get(hoverArea));
                        activeTimeouts.delete(hoverArea);
                    }
                });

                submenuDropdown.addEventListener('mouseleave', function () {
                    const timeoutId = setTimeout(() => {
                        submenuDropdown.style.display = 'none';
                        submenuDropdown.style.opacity = '0';
                        submenuDropdown.style.visibility = 'hidden';
                        activeTimeouts.delete(hoverArea);
                    }, 150);

                    activeTimeouts.set(hoverArea, timeoutId);
                });
            });
        }
    }

    function setupMobileAccordion() {
        if (window.innerWidth <= 991) {
            const submenuToggles = categoriesMenu.querySelectorAll('.dropdown-submenu > .dropdown-item.dropdown-toggle');

            submenuToggles.forEach(toggle => {
                toggle.addEventListener('click', function (event) {
                    event.preventDefault();
                    event.stopPropagation();

                    const parentSubmenu = this.parentElement;
                    const submenu = parentSubmenu.querySelector('.submenu');

                    if (!submenu) return;

                    const isActive = parentSubmenu.classList.contains('active');

                    const siblings = Array.from(parentSubmenu.parentElement.children);
                    siblings.forEach(sibling => {
                        if (sibling !== parentSubmenu && sibling.classList.contains('dropdown-submenu')) {
                            sibling.classList.remove('active');
                        }
                    });

                    if (isActive) {
                        parentSubmenu.classList.remove('active');
                    } else {
                        parentSubmenu.classList.add('active');
                    }
                });
            });
        }
    }

    function resetSubmenus() {
        const submenus = categoriesMenu.querySelectorAll('.submenu');
        submenus.forEach(submenu => {
            submenu.style.display = 'none';
            submenu.style.opacity = '0';
            submenu.style.visibility = 'hidden';
        });

        const submenuItems = categoriesMenu.querySelectorAll('.dropdown-submenu');
        submenuItems.forEach(item => {
            item.classList.remove('active');
        });

        activeTimeouts.forEach(timeout => clearTimeout(timeout));
        activeTimeouts.clear();
    }

    function setupMenuBehavior() {
        resetSubmenus();
        setupDesktopHover();
        setupMobileAccordion();
    }

    setupMenuBehavior();

    let resizeTimeout;
    window.addEventListener('resize', function () {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            activeTimeouts.forEach(timeout => clearTimeout(timeout));
            activeTimeouts.clear();
            setupMenuBehavior();
        }, 250);
    });

    document.addEventListener('click', function (event) {
        if (!categoriesDropdown.contains(event.target)) {
            resetSubmenus();
        }
    });

    categoriesMenu.addEventListener('click', function (event) {
        if (event.target.classList.contains('dropdown-toggle')) {
            event.stopPropagation();
        }
    });

    categoriesDropdown.addEventListener('hidden.bs.dropdown', function () {
        resetSubmenus();
    });

    categoriesDropdown.addEventListener('shown.bs.dropdown', function () {
        setupMenuBehavior();
    });
});
