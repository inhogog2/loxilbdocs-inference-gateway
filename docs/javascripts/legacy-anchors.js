// Forward an old deep link (#removed-section) to the section's current location.
(function () {
  function follow() {
    var id = decodeURIComponent(window.location.hash.slice(1));
    if (!id) return;
    var target = document.getElementById(id);
    if (!target || !target.closest('.legacy-anchors')) return;
    var link = target.parentElement.querySelector('a[href]');
    if (link) window.location.replace(link.href);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', follow);
  } else {
    follow();
  }
  window.addEventListener('hashchange', follow);
})();
