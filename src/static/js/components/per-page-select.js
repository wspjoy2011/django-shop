document.addEventListener('DOMContentLoaded', function () {
  const perPageSelect = document.getElementById('perPageSelect');
  if (!perPageSelect) return;

  perPageSelect.addEventListener('change', function () {
    const url = new URL(window.location);
    const value = this.value;

    const allowed = ['8','12','16','20','24'];
    if (allowed.includes(value)) {
      url.searchParams.set('per_page', value);
    } else {
      url.searchParams.delete('per_page');
    }

    url.searchParams.delete('page');

    window.location.href = url.toString();
  });
});
