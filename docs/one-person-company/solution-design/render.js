const {chromium}=require('playwright');const fs=require('fs');const path=require('path');
(async()=>{
 const b=await chromium.launch();const p=await b.newPage({viewport:{width:1600,height:1200},deviceScaleFactor:2});
 const lib=fs.readFileSync(process.env.MERMAID_JS||path.join(__dirname,'node_modules/mermaid/dist/mermaid.min.js'),'utf8');
 await p.setContent('<html><body style="margin:0;background:#fff"><div id="o" style="display:inline-block;padding:16px"></div></body></html>');
 await p.addScriptTag({content:lib});
 await p.evaluate(()=>mermaid.initialize({startOnLoad:false,theme:'base',themeVariables:{fontFamily:'Liberation Sans, Arial',fontSize:'15px',primaryColor:'#DCE6F2',primaryBorderColor:'#2E5597',primaryTextColor:'#1a1a1a',lineColor:'#5B6770',clusterBkg:'#F7F9FC',clusterBorder:'#9FB3D1'},flowchart:{htmlLabels:true,curve:'basis',useMaxWidth:false},state:{useMaxWidth:false},sequence:{useMaxWidth:false},er:{useMaxWidth:false}}));
 const dir=path.join(__dirname,'diagrams');fs.mkdirSync(path.join(__dirname,'img'),{recursive:true});
 for(const f of fs.readdirSync(dir).filter(f=>f.endsWith('.mmd'))){
  const src=fs.readFileSync(path.join(dir,f),'utf8');
  const res=await p.evaluate(async(s)=>{try{const {svg}=await mermaid.render('g'+Math.random().toString(36).slice(2),s);document.getElementById('o').innerHTML=svg;const el=document.querySelector('#o svg');el.style.maxWidth='none';return 'ok'}catch(e){return 'ERR '+e.message}},src);
  if(res!=='ok'){console.log(f,res);continue}
  const el=await p.$('#o');const out=path.join(__dirname,'img',f.replace('.mmd','.png'));await el.screenshot({path:out});
  const bb=await el.boundingBox();console.log(f,Math.round(bb.width),Math.round(bb.height));
 }
 await b.close();})();
