document.addEventListener('DOMContentLoaded', function () {
    const readonlySelect = document.querySelector('select[readonly]');

    if (readonlySelect) {
        const selectedOption = readonlySelect.options[readonlySelect.selectedIndex];

        if (selectedOption && selectedOption.value) {
            const selectedName = selectedOption.text;

            const parentNameSpan = document.getElementById('parent-category-name');
            const parentDisplaySmall = document.getElementById('parent-category-display');

            if (parentNameSpan && parentDisplaySmall) {
                parentNameSpan.textContent = selectedName;
                parentDisplaySmall.style.display = 'block';
            }
        }
    }
});
