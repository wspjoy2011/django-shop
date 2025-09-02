document.addEventListener('DOMContentLoaded', function () {
  const sortSelect = document.getElementById('sortSelect');
  if (!sortSelect) return;

  sortSelect.addEventListener('change', function () {
    const url = new URL(window.location);
    const selectedOrder = this.value;

    if (selectedOrder && selectedOrder !== 'default') {
      url.searchParams.set('ordering', selectedOrder);
    } else {
      url.searchParams.delete('ordering');
    }

    url.searchParams.delete('page');

    window.location.href = url.toString();
  });
});
