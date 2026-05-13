(function () {
    if (typeof window === 'undefined' || !window.document) return;
    if (window.__UnimusConfigSearchCompatLoaded) return;
    if (document.querySelector('script[src^="unimus/config-search.js"]')) return;
    window.__UnimusConfigSearchCompatLoaded = true;

    const script = document.createElement('script');
    script.src = 'unimus/config-search.js?v=8';
    script.defer = true;
    (document.currentScript?.parentNode || document.head || document.body).appendChild(script);
})();
