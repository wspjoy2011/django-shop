document.addEventListener('DOMContentLoaded', function () {
  const atSelect = document.getElementById('id_article_type');
  const subDisplay = document.getElementById('id_sub_category_display');
  const masterDisplay = document.getElementById('id_master_category_display');

  function updateDisplays() {
    if (!atSelect) return;
    try {
      const data = atSelect.dataset.articleMap ? JSON.parse(atSelect.dataset.articleMap) : {};
      const v = data[atSelect.value];
      if (v) {
        if (subDisplay) subDisplay.value = v.sub || '';
        if (masterDisplay) masterDisplay.value = v.master || '';
      } else {
        if (subDisplay) subDisplay.value = '';
        if (masterDisplay) masterDisplay.value = '';
      }
    } catch (_) {
      if (subDisplay) subDisplay.value = '';
      if (masterDisplay) masterDisplay.value = '';
    }
  }
  if (atSelect) {
    atSelect.addEventListener('change', updateDisplays);
    updateDisplays();
  }

  const imageInput = document.getElementById('id_image_url');
  const preview = document.getElementById('imagePreview');
  const placeholder = document.getElementById('imagePreviewPlaceholder');

  function updatePreview() {
    if (!preview || !placeholder) return;
    const url = imageInput ? imageInput.value.trim() : '';
    if (url) {
      preview.src = url;
      preview.onload = () => {
        preview.style.display = 'block';
        placeholder.style.display = 'none';
      };
      preview.onerror = () => {
        preview.style.display = 'none';
        placeholder.style.display = 'block';
      };
    } else {
      preview.style.display = 'none';
      placeholder.style.display = 'block';
    }
  }
  if (imageInput) {
    imageInput.addEventListener('input', updatePreview);
    updatePreview();
  }
});
