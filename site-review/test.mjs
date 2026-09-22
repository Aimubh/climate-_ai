// Headless Chrome self-test over the DevTools protocol. Zero dependencies (Node 22+).
import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const URL = 'http://127.0.0.1:8090/';
const OUT = 'C:/Users/ADMIN/Desktop/temp/check the Project/ai-climate-prediction/site-review/shots';
const PORT = 9333;
mkdirSync(OUT, { recursive: true });

const chrome = spawn(CHROME, [`--headless=new`, `--disable-gpu`, `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${process.env.TEMP}/cdp-profile-${Date.now()}`, `--hide-scrollbars`, `--no-first-run`, `--window-size=1440,900`, 'about:blank'], { stdio: 'ignore' });

let target;
for (let i = 0; i < 50 && !target; i++) { try { const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); target = list.find(t => t.type === 'page'); } catch {} if (!target) await sleep(200); }
if (!target) { console.error('no chrome target'); chrome.kill(); process.exit(1); }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
let id = 0; const pending = new Map(); const consoleErrors = [];
ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  if (m.method === 'Runtime.exceptionThrown') consoleErrors.push('EXC ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
  if (m.method === 'Runtime.consoleAPICalled' && (m.params.type === 'error' || m.params.type === 'warning')) consoleErrors.push(m.params.type.toUpperCase() + ' ' + m.params.args.map(a => a.value ?? a.description).join(' '));
  if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') consoleErrors.push('LOG ' + m.params.entry.text + ' ' + (m.params.entry.url || '')); };
const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, m => res(m.result || m.error)); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); return r.result ? r.result.value : r; };
const shot = async (name) => { const r = await send('Page.captureScreenshot', { format: 'png' }); writeFileSync(`${OUT}/${name}.png`, Buffer.from(r.data, 'base64')); };
const desktop = () => send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
const phone = () => send('Emulation.setDeviceMetricsOverride', { width: 375, height: 812, deviceScaleFactor: 2, mobile: true });
const nav = async () => { await send('Page.navigate', { url: URL }); for (let i = 0; i < 50; i++) { if (await ev('document.readyState') === 'complete') break; await sleep(100); } await sleep(1800); await ev("document.documentElement.style.scrollBehavior='auto'"); };
const bandsState = () => ev(`[...document.querySelectorAll('.band')].map((b,i)=>i+':'+(+getComputedStyle(b).opacity).toFixed(2)+'/k'+(getComputedStyle(b).getPropertyValue('--k')||'0').trim()).join('  ')`);
const report = {};

await send('Page.enable'); await send('Runtime.enable'); await send('Log.enable');
await desktop(); await nav();
report.title = await ev('document.title');
report.overflowDesktop = await ev('document.documentElement.scrollWidth + " vs " + innerWidth');
await shot('desktop-top');

// scrub positions
const range = await ev(`document.querySelector('.hero').offsetHeight - innerHeight`);
report.heroRange = range;
const probes = {};
for (const p of [0, 0.1, 0.35, 0.6, 0.9, 1]) { await ev(`scrollTo(0, ${Math.round(range * p)})`); await sleep(900); probes[p] = await bandsState(); if (p === 0.35 || p === 0.6 || p === 1) await shot(`desktop-hero-${p}`); }
report.probes = probes;

// contrast audit: worst pixel under each band's text box, with the band scrim applied
await ev(`window.__audit = async (p, alpha) => { scrollTo(0, Math.round((document.querySelector('.hero').offsetHeight - innerHeight) * p)); await new Promise(r => setTimeout(r, 700));
  const cv = document.getElementById('sky'), c = cv.getContext('2d'); const dpr = cv.width / cv.clientWidth;
  const band = [...document.querySelectorAll('.band')].find(b => +getComputedStyle(b).opacity > 0.9); if (!band) return 'no visible band';
  const r = band.getBoundingClientRect(); const d = c.getImageData(Math.round(r.left*dpr), Math.round(r.top*dpr), Math.round(r.width*dpr), Math.round(r.height*dpr)).data;
  const lum = ([R,G,B]) => { const f = v => { v/=255; return v<=0.03928? v/12.92 : ((v+0.055)/1.055)**2.4 }; return 0.2126*f(R)+0.7152*f(G)+0.0722*f(B) };
  let worst = 0; for (let i=0;i<d.length;i+=4){ const px=[0,1,2].map(j=>d[i+j]*(1-alpha)+[5,5,10][j]*alpha); worst=Math.max(worst,lum(px)); }
  const lt = lum([234,243,241]); return ((Math.max(lt,worst)+0.05)/(Math.min(lt,worst)+0.05)).toFixed(2) + ':1 (band ' + [...document.querySelectorAll('.band')].indexOf(band) + ')'; }`);
report.contrast = {};
for (const [p, a] of [[0.05, 0.72], [0.35, 0.66], [0.61, 0.66], [0.95, 0.66]]) report.contrast[p] = await ev(`window.__audit(${p}, ${a})`);

// flick test
const flick = async (step, count) => { await ev('scrollTo(0,0)'); await sleep(600); const log = []; for (let i = 0; i < count; i++) { await ev(`scrollBy(0, ${step})`); await sleep(400); log.push(await ev(`[...document.querySelectorAll('.band')].map(b=>(+getComputedStyle(b).opacity).toFixed(2)).join(' ')`)); } return log; };
report.flick120 = await flick(120, 26); report.flick240 = await flick(240, 14); report.flick360 = await flick(360, 10);

// sections: entrances and screenshots
for (const s of ['live', 'how', 'run', 'report', 'faq', 'early']) { await ev(`document.getElementById('${s}').scrollIntoView({block:'start'})`); await sleep(1500); await shot(`desktop-${s}`); }
await ev("document.getElementById('nextbox').scrollIntoView({block:'center'})"); await sleep(1200); await shot('desktop-nextbox');
report.entrances = await ev(`[...document.querySelectorAll('.rv')].map(r => r.id || r.className.split(' ')[0]).map(n => n + ':' + (document.getElementById(n) || document.querySelector('.'+n)).classList.contains('in')).join(' ')`);
report.liveCards = await ev(`[...document.querySelectorAll('#strip .card')].map(c => c.querySelector('.city').textContent + ' ' + c.querySelector('.temp').textContent.trim()).join(' | ')`);
report.stamp = await ev(`document.getElementById('stamp').textContent`);
report.drawLines = await ev(`[...document.querySelectorAll('.draw')].map(p => getComputedStyle(p).strokeDashoffset).join(' ')`);

// hold interaction with a real mouse press, gap, release
await ev(`document.getElementById('run').scrollIntoView({block:'start'})`); await sleep(1200);
const rect = await ev(`(r => ({x: r.left + r.width/2, y: r.top + r.height/2}))(document.getElementById('hold').getBoundingClientRect())`);
await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: rect.x, y: rect.y });
await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: rect.x, y: rect.y, button: 'left', clickCount: 1 });
await sleep(700); report.holdMid = await ev(`getComputedStyle(document.getElementById('hold')).getPropertyValue('--hold').trim()`);
await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: rect.x, y: rect.y, button: 'left', clickCount: 1 });
await sleep(900); report.holdAfterEarlyRelease = await ev(`getComputedStyle(document.getElementById('hold')).getPropertyValue('--hold').trim() + ' / ' + document.getElementById('hint').textContent`);
await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: rect.x, y: rect.y, button: 'left', clickCount: 1 });
await sleep(1900);
await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: rect.x, y: rect.y, button: 'left', clickCount: 1 });
await sleep(2200);
report.holdDone = await ev(`document.getElementById('hold').classList.contains('done') + ' lit=' + document.getElementById('fc').classList.contains('lit') + ' days=' + document.querySelectorAll('#fc .day').length + ' / ' + document.getElementById('hint').textContent`);
report.ours = await ev("document.getElementById('ours').hidden + ' / ' + document.getElementById('ours').textContent"); report.runnote = await ev("document.getElementById('runnote').textContent");
await shot('desktop-run-done');

// form
await ev(`document.getElementById('early').scrollIntoView({block:'start'})`); await sleep(1200);
await ev(`(f => { f.name.value='Asha'; f.email.value='asha@example.com'; f.city.value='Pune'; f.requestSubmit(); })(document.getElementById('form'))`); await sleep(500);
report.form = await ev(`document.getElementById('form').hidden + ' / ' + getComputedStyle(document.getElementById('ok')).display + ' / ' + document.getElementById('oktext').textContent`);
await shot('desktop-form-ok');

// the bot: open it, click a suggested question, wait for a streamed answer from the local model
report.botFab = await ev("document.getElementById('botfab').hidden");
await ev("document.getElementById('botfab').click()"); await sleep(400);
await ev("document.querySelector('#botchips .chipbtn').click()");
let botText = '';
for (let i = 0; i < 60; i++) { await sleep(3000); botText = await ev("(m => m.length ? m[m.length-1].textContent : '')([...document.querySelectorAll('.msg.reply')])"); const st = await ev("document.getElementById('botstatus').textContent + '|' + document.getElementById('botsend').disabled"); if (botText.length > 40 && st === '|false') break; }
report.bot = botText.slice(0, 400);
await shot('desktop-bot');
await ev("document.getElementById('botclose').click()");

// reduced motion, flipped live in both directions
await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] }); await sleep(500);
report.rmOn = await ev(`getComputedStyle(document.querySelector('.bands')).display + ' / static:' + getComputedStyle(document.querySelector('.static-copy')).display + ' / html.rm:' + document.documentElement.classList.contains('rm')`);
await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'no-preference' }] }); await sleep(500);
await ev(`scrollTo(0, ${Math.round(range * 0.6)})`); await sleep(900);
report.rmOff = await ev(`getComputedStyle(document.querySelector('.bands')).display + ' / static:' + getComputedStyle(document.querySelector('.static-copy')).display + ' / html.rm:' + document.documentElement.classList.contains('rm')`) + ' / ' + await bandsState();

// phone
await phone(); await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 }); await nav();
report.phone = await ev(`getComputedStyle(document.querySelector('.bands')).display + ' / static:' + getComputedStyle(document.querySelector('.static-copy')).display + ' / heroH:' + document.querySelector('.hero').offsetHeight + ' / overflow:' + document.documentElement.scrollWidth + ' vs ' + innerWidth`);
report.phoneCanvas = await ev(`(c => { const d = c.getContext('2d').getImageData(Math.round(c.width*0.3), Math.round(c.height*0.5), 1, 1).data; return [...d].slice(0,3).join(',') })(document.getElementById('sky'))`);
await shot('phone-top');
for (const s of ['live', 'run', 'early']) { await ev(`document.getElementById('${s}').scrollIntoView({block:'start'})`); await sleep(1400); await shot(`phone-${s}`); }
report.phoneTargets = await ev(`[...document.querySelectorAll('.btn, .chipbtn')].map(b => Math.round(b.getBoundingClientRect().height)).filter(h => h > 0).sort((a,b)=>a-b).slice(0,3).join(',') + ' (min heights)'`);

report.consoleErrors = consoleErrors;
console.log(JSON.stringify(report, null, 1));
ws.close(); chrome.kill();
