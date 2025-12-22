const fs = require('fs');
const path = require('path');
let JSDOM;
try {
  ({ JSDOM } = require('jsdom'));
} catch (e) {
  console.error('Missing dependency: jsdom');
  console.error('Install (from repo root): npm init -y && npm i jsdom');
  process.exit(2);
}

const htmlPath = path.join(__dirname, '..', 'vm_deployment', 'NOC-configMaker.html');
const html = fs.readFileSync(htmlPath, 'utf8');
const dom = new JSDOM(html, { runScripts: 'dangerously', resources: 'usable' });
const { window } = dom;
// Wait for scripts to load
function waitFor(selector, timeout = 5000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    (function poll() {
      const el = window.document.querySelector(selector);
      if (el) return resolve(el);
      if (Date.now() - start > timeout) return reject(new Error('Timeout waiting for ' + selector));
      setTimeout(poll, 100);
    })();
  });
}

setTimeout(async () => {
  try {
    await waitFor('#ent_mpls_deviceType', 5000);
    window.alert = function(msg) { console.log('ALERT:', msg); };

    const deviceTypes = ['CCR2004','CCR1036','RB5009','CCR2216','CCR1072'];
    for (const dt of deviceTypes) {
      console.log('\n========================');
      console.log('Generating for device:', dt);
      console.log('========================\n');

      // set basic form
      window.document.getElementById('ent_mpls_deviceType').value = dt;
      window.document.getElementById('ent_mpls_customerCode').value = 'IL-CARMI';
      window.document.getElementById('ent_mpls_deviceName').value = 'NX-537853';
      window.document.getElementById('ent_mpls_loopbackIP').value = '10.5.0.57/32';
      window.document.getElementById('ent_mpls_natInterface').value = '';
      const pubIf = window.document.getElementById('ent_mpls_publicInterface');
      if (pubIf) { let opt = Array.from(pubIf.options).find(o => o.value === 'sfp-sfpplus1'); if (!opt) { opt = window.document.createElement('option'); opt.value='sfp-sfpplus1'; opt.text='sfp-sfpplus1'; pubIf.add(opt);} pubIf.value='sfp-sfpplus1'; }
      if (window.document.getElementById('ent_mpls_snmpCommunity')) window.document.getElementById('ent_mpls_snmpCommunity').value = 'FBZ1yYdphf';
      if (window.document.getElementById('ent_mpls_bgpAs')) window.document.getElementById('ent_mpls_bgpAs').value = '';
      if (window.document.getElementById('ent_mpls_bgpPeers')) window.document.getElementById('ent_mpls_bgpPeers').value = '';

      // ensure uplink exists
      const container = window.document.getElementById('ent_mpls_uplinksContainer');
      container.innerHTML = '';
      const div = window.document.createElement('div');
      div.className = 'interface-item';
      const sel = window.document.createElement('select'); sel.className = 'ent_mpls_uplinkInterface';
      sel.innerHTML = '<option value="sfp-sfpplus1">sfp-sfpplus1</option>';
      const ipIn = window.document.createElement('input'); ipIn.className = 'ent_mpls_uplinkIP'; ipIn.value = '10.1.253.84/29';
      const cIn = window.document.createElement('input'); cIn.className = 'ent_mpls_uplinkComment'; cIn.value = 'IL-CARMI-CN-1';
      div.appendChild(sel); div.appendChild(ipIn); div.appendChild(cIn); container.appendChild(div);

      // call generator
      const genFn = window.generateMPLSEnterpriseConfig;
      try { genFn(); } catch(e){ console.error('Generator error:', e && e.stack ? e.stack : e); }
      // wait
      await new Promise(r=>setTimeout(r,300));
      const real = window.mplsEnterpriseConfigOriginal || '';
      console.log(real);
    }
  } catch (e) {
    console.error('Test harness error:', e && e.stack ? e.stack : e);
  }
}, 1200);
