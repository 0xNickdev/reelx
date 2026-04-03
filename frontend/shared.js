// REELX SHARED JS — no custom cursor
document.addEventListener('DOMContentLoaded', function() {
  // Scroll reveal
  var obs = new IntersectionObserver(function(entries) {
    entries.forEach(function(e) { if (e.isIntersecting) e.target.classList.add('in'); });
  }, { threshold: 0.07 });
  document.querySelectorAll('.reveal').forEach(function(el) { obs.observe(el); });

  // FAQ accordion
  document.querySelectorAll('.faq-q').forEach(function(q) {
    q.addEventListener('click', function() {
      var item = q.parentElement;
      var isOpen = item.classList.contains('open');
      document.querySelectorAll('.faq-item').forEach(function(i) { i.classList.remove('open'); });
      if (!isOpen) item.classList.add('open');
    });
  });

  // Filter buttons (single select within group)
  document.querySelectorAll('.filter-group').forEach(function(group) {
    group.querySelectorAll('.f-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        group.querySelectorAll('.f-btn').forEach(function(b) { b.classList.remove('on'); });
        btn.classList.add('on');
      });
    });
  });

  // Toggle buttons (multi select)
  document.querySelectorAll('.toggle-btn').forEach(function(btn) {
    btn.addEventListener('click', function() { btn.classList.toggle('on'); });
  });
});

// Copy to clipboard
function copyText(elId) {
  var el = document.getElementById(elId);
  if (!el) return;
  var text = el.innerText || el.textContent;
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(function() { showToast('Скопировано ✓'); });
  } else {
    var ta = document.createElement('textarea');
    ta.value = text; document.body.appendChild(ta); ta.select();
    document.execCommand('copy'); document.body.removeChild(ta);
    showToast('Скопировано ✓');
  }
}

function showToast(msg) {
  var t = document.createElement('div');
  t.textContent = msg;
  t.style.cssText = 'position:fixed;bottom:28px;left:50%;transform:translateX(-50%);background:#e8ddd2;color:#0c0c0e;padding:10px 22px;border-radius:8px;font-size:0.82rem;font-weight:600;z-index:9999;font-family:inherit;pointer-events:none;animation:fadeUp 0.3s ease;';
  document.body.appendChild(t);
  setTimeout(function() { t.style.opacity = '0'; t.style.transition = 'opacity 0.3s'; setTimeout(function() { t.remove(); }, 300); }, 2000);
}

function goPage(url) { window.location.href = url; }
