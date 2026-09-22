import { spawn } from 'node:child_process'; import { setTimeout as sleep } from 'node:timers/promises'; import { writeFileSync } from 'node:fs';
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new','--disable-gpu','--remote-debugging-port=9335',`--user-data-dir=${process.env.TEMP}/cdp-p2-${Date.now()}`,'--hide-scrollbars','--no-first-run','--window-size=1440,900','about:blank'], { stdio:'ignore' });
let t; for (let i=0;i<50&&!t;i++){ try{ t=(await (await fetch('http://127.0.0.1:9335/json/list')).json()).find(x=>x.type==='page') }catch{} if(!t) await sleep(200) }
const ws = new WebSocket(t.webSocketDebuggerUrl); await new Promise(r=>ws.onopen=r); let id=0; const pend=new Map(); const errs=[];
ws.onmessage = e => { const m=JSON.parse(e.data); if(m.id&&pend.has(m.id)){pend.get(m.id)(m);pend.delete(m.id)} if(m.method==='Runtime.exceptionThrown') errs.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text) };
const send=(m,p={})=>new Promise(r=>{const i=++id;pend.set(i,x=>r(x.result||x.error));ws.send(JSON.stringify({id:i,method:m,params:p}))});
const ev=async x=>{ const r=await send('Runtime.evaluate',{expression:x,returnByValue:true,awaitPromise:true}); if(r.exceptionDetails) return 'EXC: '+(r.exceptionDetails.exception?.description||r.exceptionDetails.text); return r.result?.value };
const shot=async n=>{ const r=await send('Page.captureScreenshot',{format:'png'}); writeFileSync('shots/'+n+'.png', Buffer.from(r.data,'base64')) };
await send('Page.enable'); await send('Runtime.enable'); await send('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});
await send('Page.navigate',{url:'http://127.0.0.1:8090/'}); for(let i=0;i<50;i++){ if(await ev('document.readyState')==='complete') break; await sleep(100)} await sleep(2000);
await ev("document.getElementById('botfab').click()"); await sleep(600);
console.log('children after open:\n' + await ev("[...document.getElementById('bot').children].map(c => c.tagName + '.' + c.className + ' display=' + getComputedStyle(c).display + ' rect=' + JSON.stringify(c.getBoundingClientRect().toJSON ? {y: Math.round(c.getBoundingClientRect().y), h: Math.round(c.getBoundingClientRect().height)} : 0)).join(' | ')"));
console.log('log children:', await ev("document.getElementById('botlog').children.length + ' | ' + [...document.querySelectorAll('#botlog .msg')].map(m => m.className + ' h=' + Math.round(m.getBoundingClientRect().height) + ' \"' + m.textContent.slice(0, 30) + '\"').join(' | ')"));
await shot('probe-bot-open');
await ev("document.querySelector('#botchips .chipbtn').click()");
let txt=''; for (let i=0;i<40;i++){ await sleep(3000); txt = await ev("(m => m.length ? m[m.length-1].textContent : '')([...document.querySelectorAll('.msg.reply')])"); const st = await ev("document.getElementById('botsend').disabled"); if (txt.length > 40 && st === false) break; }
console.log('answer:', txt.slice(0, 120));
console.log('log children after answer:', await ev("document.getElementById('botlog').children.length + ' | scrollTop=' + document.getElementById('botlog').scrollTop + ' scrollH=' + document.getElementById('botlog').scrollHeight + ' clientH=' + document.getElementById('botlog').clientHeight"));
await shot('probe-bot-answered');
console.log('page exceptions:', errs);
ws.close(); chrome.kill();
