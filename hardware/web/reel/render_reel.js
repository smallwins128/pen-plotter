// Renders harbor_reel.html to a 1080x1920 MP4, frame by frame. Run from the repo root:
//   node hardware/web/reel/render_reel.js [out.mp4] [--three path/to/three.module.js] [--preview t1,t2,...]
// three.js is loaded from jsDelivr; --three serves a local copy instead (for sandboxes without CDN access).
const {chromium}=require('playwright');
const http=require('http'),fs=require('fs'),path=require('path'),{spawn}=require('child_process');
const args=process.argv.slice(2);
const opt=(k)=>{const i=args.indexOf(k);return i<0?null:args.splice(i,2)[1];};
const three=opt('--three'),preview=opt('--preview');
const out=args[0]||'harbor_reel.mp4';
const root=path.resolve(__dirname,'..','..');
const types={'.html':'text/html','.js':'text/javascript','.ttf':'font/ttf'};
const srv=http.createServer((q,r)=>{const f=path.join(root,decodeURIComponent(q.url.split('?')[0]));
  if(!f.startsWith(root)||!fs.existsSync(f)){r.writeHead(404);return r.end();}
  r.writeHead(200,{'content-type':types[path.extname(f)]||'application/octet-stream'});fs.createReadStream(f).pipe(r);});
(async()=>{
  await new Promise(ok=>srv.listen(0,ok));
  const browser=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const page=await browser.newPage({viewport:{width:1080,height:1920},deviceScaleFactor:1});
  if(three)await page.route('**/three@0.160.0/build/three.module.js',r=>r.fulfill({path:three,contentType:'text/javascript'}));
  page.on('pageerror',e=>console.error('page:',e.message));
  await page.goto(`http://localhost:${srv.address().port}/web/reel/harbor_reel.html?render`);
  await page.waitForFunction(()=>window.READY);
  const {DUR,FPS}=await page.evaluate(()=>window.REEL);
  if(preview){for(const t of preview.split(',')){await page.evaluate(t=>window.seek(t),+t);await page.screenshot({path:`${out}-${t}.jpg`,quality:85,type:'jpeg'});}}
  else{
    const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',String(FPS),'-c:v','mjpeg','-i','-',
      '-c:v','libx264','-pix_fmt','yuv420p','-crf','18','-preset','slow','-movflags','+faststart',out],{stdio:['pipe','inherit','inherit']});
    const n=DUR*FPS;
    for(let f=0;f<n;f++){await page.evaluate(t=>window.seek(t),f/FPS);
      ff.stdin.write(await page.screenshot({type:'jpeg',quality:95}));if(f%30===0)process.stdout.write(`${f}/${n}\r`);}
    ff.stdin.end();await new Promise(ok=>ff.on('close',ok));console.log('\nwrote',out);
  }
  await browser.close();srv.close();
})();
