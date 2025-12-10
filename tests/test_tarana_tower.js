const fs = require('fs');
const jsdom = require('jsdom');
const { JSDOM } = jsdom;

const html = fs.readFileSync('NOC-configMaker.html', 'utf8');

const dom = new JSDOM(html, { runScripts: "dangerously", resources: "usable" });
// Wait briefly for scripts to initialize
setTimeout(() => {
    const window = dom.window;
    const document = window.document;

    // Populate minimal required fields
    document.getElementById('siteName').value = 'NX-TEST';
    document.getElementById('routerId').value = '10.5.0.57';
    document.getElementById('targetDevice').value = 'rb5009';

    // Enable Tarana optional feature
    document.getElementById('enableTarana').checked = true;
    document.getElementById('enableTarana').dispatchEvent(new window.Event('change'));

    // Fill tarana mini UI fields
    document.getElementById('tower_tarana_alpha').value = 'sfp-sfpplus6';
    document.getElementById('tower_tarana_beta').value = 'sfp-sfpplus7';
    document.getElementById('tower_tarana_gamma').value = 'sfp-sfpplus8';
    document.getElementById('tower_tarana_delta').value = '';
    document.getElementById('tower_unicornmgmt_subnet').value = '10.246.25.48/29';

  // (preview removed) we only run main generator and inspect final output

    // Call main generateConfig when it becomes available (poll for it)
    let attempts = 0;
    const maxAttempts = 40; // ~8 seconds
    const poll = setInterval(() => {
      attempts++;
      if (typeof window.generateConfig === 'function') {
        try {
          window.generateConfig();
        } catch (e) {
          console.error('generateConfig() threw', e);
        }
        clearInterval(poll);
        const mainOutput = document.getElementById('output')?.textContent || document.getElementById('output')?.value || '';
        console.log('--- MAIN GENERATED CONFIG (first 2000 chars) ---\n', mainOutput.substring(0,2000));
        process.exit(0);
      }
      if (attempts >= maxAttempts) {
        clearInterval(poll);
        console.warn('generateConfig() not available after polling; aborting.');
        process.exit(2);
      }
    }, 200);

    process.exit(0);
  }, 800);
