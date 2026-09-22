import { spawn } from 'node:child_process'; import { setTimeout as sleep } from 'node:timers/promises';
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new','--disable-gpu','--remote-debugging-port=9334',`--user-data-dir=${process.env.TEMP}/cdp-p-${Date.now()}`,'--hide-scrollbars','--no-first-run','--window-size=1440,900','about:blank'], { stdio:'ignore' });
let t; for (let i=0;i<50&&!t;i++){ try{ t=(await (await fetch('http://127.0.0.1:9334/json/list')).json()).find(x=>x.type==='page') }catch{} if(!t) await sleep(200) }
const ws = new WebSocket(t.webSocketDebuggerUrl); await new Promise(r=>ws.onopen=r); let id=0; const pend=new Map();
ws.onmessage = e => { const m=JSON.parse(e.data); if(m.id&&pend.has(m.id)){pend.get(m.id)(m);pend.delete(m.id)} };
const send=(m,p={})=>new Promise(r=>{const i=++id;pend.set(i,x=>r(x.result||x.error));ws.send(JSON.stringify({id:i,method:m,params:p}))});
const ev=async x=>(await send('Runtime.evaluate',{expression:x,returnByValue:true,awaitPromise:true})).result?.value;
await send('Page.enable'); await send('Runtime.enable'); await send('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});
await send('Page.navigate',{url:'http://127.0.0.1:8090/'}); for(let i=0;i<50;i++){ if(await ev('document.readyState')==='complete') break; await sleep(100)} await sleep(1800);
await ev(`document.documentElement.style.scrollBehavior='auto'`);
const range = await ev(`document.querySelector('.hero').offsetHeight - innerHeight`); console.log('range', range);
for (const y of [0,120,240,360,480,600,720,840]) { await ev(`scrollTo(0,${y})`); await sleep(800);
  console.log('y='+y, 'p='+(y/range).toFixed(3), await ev(`[...document.querySelectorAll('.band')].map((b,i)=>i+':op'+b.style.opacity+'/c'+(+getComputedStyle(b).opacity).toFixed(2)+'/k'+getComputedStyle(b).getPropertyValue('--k').trim()).join('  ')`),
   'heroTop='+await ev(`Math.round(document.querySelector('.hero').getBoundingClientRect().top)`)); }
ws.close(); chrome.kill();
