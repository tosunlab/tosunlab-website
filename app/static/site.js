(function () {
  var KEY = 'tosunlab-site-dark';
  var root = document.documentElement;
  var button = document.getElementById('theme-toggle');
  if (!button) return;

  function isDark() {
    if (root.dataset.theme) return root.dataset.theme === 'dark';
    return !!(window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches);
  }
  function label() {
    button.textContent = isDark() ? '[ light mode ]' : '[ dark mode ]';
  }
  button.addEventListener('click', function () {
    var dark = !isDark();
    root.dataset.theme = dark ? 'dark' : 'light';
    try { localStorage.setItem(KEY, dark ? '1' : '0'); } catch (e) {}
    label();
  });
  label();
  button.hidden = false;
})();
