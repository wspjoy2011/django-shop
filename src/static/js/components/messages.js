document.addEventListener('DOMContentLoaded', function () {
    const messageAlerts = document.querySelectorAll('.message-alert');

    messageAlerts.forEach(function (alert) {
        const progressBar = alert.querySelector('.progress-bar');

        setTimeout(function () {
            if (progressBar) progressBar.style.width = '0%';
        }, 100);

        let autoCloseTimer = setTimeout(function () {
            closeMessage(alert);
        }, 10000);

        alert.addEventListener('mouseenter', function () {
            clearTimeout(autoCloseTimer);
            if (progressBar) progressBar.style.animationPlayState = 'paused';
        });

        alert.addEventListener('mouseleave', function () {
            if (progressBar) progressBar.style.animationPlayState = 'running';
            autoCloseTimer = setTimeout(function () {
                closeMessage(alert);
            }, 2000);
        });

        const closeButton = alert.querySelector('.btn-close');
        if (closeButton) {
            closeButton.addEventListener('click', function () {
                clearTimeout(autoCloseTimer);
                closeMessage(alert);
            });
        }
    });

    function closeMessage(alert) {
        alert.classList.add('fade-out');
        setTimeout(function () {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 500);
    }
});
