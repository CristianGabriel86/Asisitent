// No inline code or third-party scripts; the core workflow also works without JS.
for (const form of document.querySelectorAll('form')) {
  form.addEventListener('submit', (event) => {
    if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
      event.preventDefault();
      return;
    }
    const button = form.querySelector('button[type="submit"]');
    if (button) {
      button.disabled = true;
      button.textContent = 'Se procesează…';
    }
  });
}
window.addEventListener('pageshow', () => {
  for (const button of document.querySelectorAll('button')) {
    if (button.textContent === 'Se procesează…') window.location.reload();
  }
});
