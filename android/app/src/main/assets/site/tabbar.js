// One bar, two jobs: on index.html it switches between the sections (each tab is a
// page of its own), on mumbai.html it is plain links back. Routing goes through the
// hash, so the page's own "#live" buttons and the hardware back key both work.
(function () {
  const ICON = {
    home: '<path d="M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-5v-6h-4v6H5a1 1 0 0 1-1-1z"/>',
    chart: '<path d="M4 19V5"/><path d="M4 19h16"/><path d="M7 15l4-5 3 3 4-6"/>',
    sun: '<circle cx="12" cy="12" r="3.2"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6L7 7M17 17l1.4 1.4M18.4 5.6L17 7M7 17l-1.4 1.4"/>',
    air: '<circle cx="12" cy="12" r="2.3"/><path d="M7.6 7.6a6.2 6.2 0 0 0 0 8.8M16.4 7.6a6.2 6.2 0 0 1 0 8.8M4.9 4.9a10 10 0 0 0 0 14.2M19.1 4.9a10 10 0 0 1 0 14.2"/>',
    train: '<rect x="6" y="3" width="12" height="13" rx="3.5"/><path d="M6 10h12M9.5 19.5L8 21.5M14.5 19.5L16 21.5M9.7 13h.01M14.3 13h.01"/>',
    chat: '<path d="M20.5 12c0 4-3.8 7.2-8.5 7.2a9.9 9.9 0 0 1-2.6-.34L4.5 20.5l1.2-3.3A6.9 6.9 0 0 1 3.5 12c0-4 3.8-7.2 8.5-7.2s8.5 3.2 8.5 7.2Z"/><path d="M8.7 11.9h.01M12 11.9h.01M15.3 11.9h.01"/>',
  };
  // tab id -> label, icon, and the elements that make up that page
  const TABS = [
    { id: 'top', label: 'Home', icon: 'home', parts: ['#top', '#how', '#faq', '#early', 'footer'] },
    { id: 'live', label: 'Predictions', icon: 'chart', parts: ['#live'] },
    { id: 'run', label: 'Try it', icon: 'sun', parts: ['#run'] },
    { id: 'report', label: 'On air', icon: 'air', parts: ['#report'] },
    { id: 'stations', label: 'Stations', icon: 'train', href: 'mumbai.html' },
    // the chat panel is the whole page on this tab, so it shows no section of its own
    { id: 'assistant', label: 'Assistant', icon: 'chat', parts: [] },
  ];
  // sections that live on the Home tab but have their own anchors around the page
  const ON_HOME = ['how', 'faq', 'early', 'main'];

  const onIndex = !!document.getElementById('live');

  const bar = document.createElement('nav');
  bar.className = 'tabbar';
  bar.setAttribute('aria-label', 'Sections');
  bar.innerHTML = TABS.map(t => {
    const href = t.href ? (onIndex ? t.href : '#') : (onIndex ? '#' + t.id : 'index.html#' + t.id);
    return `<a href="${href}" data-tab="${t.id}">` +
      `<svg viewBox="0 0 24 24" aria-hidden="true">${ICON[t.icon]}</svg>${t.label}</a>`;
  }).join('');
  document.body.appendChild(bar);

  if (!onIndex) {                                   // mumbai.html: links only
    bar.querySelector('[data-tab="stations"]').setAttribute('aria-current', 'page');
    return;
  }

  const parts = new Map();                          // tab id -> elements it shows
  for (const t of TABS) {
    if (!t.parts) continue;
    parts.set(t.id, t.parts.flatMap(sel => Array.from(document.querySelectorAll(sel))));
  }
  const all = [...new Set([...parts.values()].flat())];

  function show(tab, scrollTo) {
    const wanted = new Set(parts.get(tab) || parts.get('top'));
    for (const el of all) el.classList.toggle('tab-off', !wanted.has(el));
    for (const a of bar.children) {
      if (a.dataset.tab === tab) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    }
    // canvases sized while their tab was hidden came out 0 wide; the page's own
    // resize handler re-sizes and redraws every one of them.
    window.dispatchEvent(new Event('resize'));
    // the assistant tab is the chat panel, opened through the page's own button
    const assistant = tab === 'assistant';
    document.body.classList.toggle('tab-assistant', assistant);
    if (assistant) document.getElementById('botfab').click();
    else document.getElementById('botclose').click();

    const target = scrollTo && document.getElementById(scrollTo);
    if (target) target.scrollIntoView();
    else window.scrollTo(0, 0);
  }

  function route() {
    const id = location.hash.slice(1);
    if (parts.has(id)) show(id);
    else if (ON_HOME.includes(id)) show('top', id);
    else show('top');
  }

  window.addEventListener('hashchange', route);
  // a tab tapped twice in a row fires no hashchange, so route on click too
  bar.addEventListener('click', () => setTimeout(route, 0));
  route();
})();
