// Readable source of the reading-hub inline script (TOC scroll-spy, theme toggle,
// copy-code, progress bar, back-to-top). The version shipped in build_blog.py's
// READING_HUB_BODY is this file minified with terser (--compress --mangle).
// Edit HERE, re-minify, then paste the output into READING_HUB_BODY.
(function(){
  var doc = document.documentElement;
  function curTheme(){ return doc.getAttribute('data-theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); }
  var themeBtn = document.getElementById('rh-theme');
  function setIcon(){ if (themeBtn) themeBtn.textContent = curTheme() === 'dark' ? '\\u2600\\uFE0E' : '\\u263D'; }
  setIcon();
  if (themeBtn) themeBtn.addEventListener('click', function(){
    var t = curTheme() === 'dark' ? 'light' : 'dark';
    doc.setAttribute('data-theme', t);
    try { localStorage.setItem('theme', t); } catch(e){}
    setIcon();
  });
  var article = document.querySelector('article');
  var toc = document.getElementById('toc');
  if (article && toc) {
    var heads = article.querySelectorAll('h2, h3');
    if (heads.length >= 3) {
      var title = document.createElement('div');
      title.className = 'toc-title'; title.textContent = 'On this page';
      toc.appendChild(title);
      var links = [];
      heads.forEach(function(h, i){
        if (!h.id) h.id = 'sec-' + i;
        var a = document.createElement('a');
        if (h.tagName === 'H3') a.className = 'h3';
        a.href = '#' + h.id;
        a.textContent = h.textContent;
        toc.appendChild(a);
        links.push(a);
      });
      var byId = {}; links.forEach(function(a){ byId[a.getAttribute('href').slice(1)] = a; });
      var obs = new IntersectionObserver(function(entries){
        entries.forEach(function(e){
          if (e.isIntersecting) {
            links.forEach(function(a){ a.classList.remove('active'); });
            var a = byId[e.target.id]; if (a) a.classList.add('active');
          }
        });
      }, { rootMargin: '-80px 0px -70% 0px' });
      heads.forEach(function(h){ obs.observe(h); });
    } else { toc.style.display = 'none'; }
  }
  document.querySelectorAll('article pre').forEach(function(pre){
    var btn = document.createElement('button');
    btn.className = 'copy-btn'; btn.type = 'button'; btn.textContent = 'Copy';
    btn.addEventListener('click', function(){
      var code = pre.querySelector('code');
      var txt = code ? code.innerText : pre.innerText;
      navigator.clipboard.writeText(txt).then(function(){
        btn.textContent = 'Copied'; btn.classList.add('copied');
        setTimeout(function(){ btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 1500);
      });
    });
    pre.appendChild(btn);
  });
  var bar = document.getElementById('read-progress');
  var top = document.getElementById('rh-top');
  function onScroll(){
    var h = doc.scrollHeight - doc.clientHeight;
    var p = h > 0 ? (doc.scrollTop / h) * 100 : 0;
    if (bar) bar.style.width = p + '%';
    if (top) { if (doc.scrollTop > 600) top.classList.add('show'); else top.classList.remove('show'); }
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
  if (top) top.addEventListener('click', function(){ window.scrollTo({ top: 0, behavior: 'smooth' }); });
})();
