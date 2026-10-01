/* Diwan SQL — offline-first Arabic->SQL engine + optional FastAPI backend */
const $ = s => document.querySelector(s);
let ROWS = [], LAST_SQL = "", HISTORY = [];
try { HISTORY = JSON.parse(localStorage.getItem('diwan_hist')||'[]'); } catch(e){ HISTORY = []; }

const DEPTS = {"مبيعات":"المبيعات","السيلز":"المبيعات","المبيعات":"المبيعات","تسويق":"التسويق","الماركتنج":"التسويق","التسويق":"التسويق","اي تي":"تقنية المعلومات","التقنية":"تقنية المعلومات","تكنولوجيا المعلومات":"تقنية المعلومات","تقنية المعلومات":"تقنية المعلومات","اتش ار":"الموارد البشرية","الموارد البشرية":"الموارد البشرية","شئون العاملين":"الموارد البشرية","مالية":"المالية","الحسابات":"المالية","المالية":"المالية","المحاسبة":"المالية"};
const CITIES = ["القاهرة","الجيزة","الإسكندرية","المنصورة","طنطا","أسيوط","سوهاج","الفيوم","اسكندرية","القاهره","الجيزه"];
const CITY_FIX = {"القاهره":"القاهرة","الجيزه":"الجيزة","اسكندرية":"الإسكندرية","الاسكندرية":"الإسكندرية","المنصوره":"المنصورة","اسيوط":"أسيوط"};
const REGIONS = ["القاهرة الكبرى","الدلتا","الصعيد"];
const AR_NUM = {"واحد":1,"واحدة":1,"اتنين":2,"اثنين":2,"تلاتة":3,"ثلاثة":3,"اربعة":4,"أربعة":4,"خمسة":5,"ستة":6,"سبعة":7,"تمانية":8,"ثمانية":8,"تسعة":9,"عشرة":10,"عشره":10};

const EXAMPLES = [
  "اعرض كل الموظفين في قسم المبيعات",
  "كام موظف في التسويق؟",
  "متوسط مرتبات تقنية المعلومات",
  "أعلى 5 موظفين في المبيعات حسب المبيعات",
  "ورتبهم حسب المرتب تنازليا",
  "الموظفين اللي مرتبهم أكبر من 13000 في القاهرة",
  "مجموع مبيعات الدلتا",
  "عايز موظفين التقييم بتاعهم أعلى من 4.5",
  "اعرض موظفي المالية و رتبهم حسب المرتب",
];
const CHIPS = ["عايز (مصري)","أبغى (خليجي)","بدي (شامي)","اعرض (فصحى)","كام موظف؟","رتبهم","أعلى 5"];

const FALLBACK_CSV = `id,first_name_ar,last_name_ar,department_ar,city_ar,salary_egp,hire_date,performance_rating,sales_amount_egp,region_ar
1,أحمد,محمد,المبيعات,القاهرة,12500,2021-03-15,4.5,85000,القاهرة الكبرى
2,فاطمة,علي,التسويق,الجيزة,11000,2020-07-22,4.2,42000,القاهرة الكبرى
3,محمود,حسن,تقنية المعلومات,الإسكندرية,15000,2019-11-01,4.8,15000,الدلتا
5,خالد,عبد الله,المبيعات,المنصورة,13200,2020-05-30,4.6,92000,الدلتا
9,كريم,فؤاد,تقنية المعلومات,القاهرة,16500,2017-04-25,4.9,22000,القاهرة الكبرى
10,منى,سعيد,المبيعات,الإسكندرية,12900,2020-12-01,4.3,78000,الدلتا
13,عمر,الشريف,المبيعات,سوهاج,11200,2022-03-11,4.0,54000,الصعيد
19,طارق,سالم,المبيعات,الجيزة,13100,2020-03-21,4.7,88000,القاهرة الكبرى
25,أيمن,فاروق,المبيعات,القاهرة,13400,2019-08-13,4.6,95000,القاهرة الكبرى
39,فارس,كريم,المبيعات,القاهرة,13300,2019-10-24,4.5,90000,القاهرة الكبرى
6,نور,السيد,المالية,القاهرة,14000,2018-09-12,4.7,0,القاهرة الكبرى
14,رانيا,فتحي,التسويق,القاهرة,11500,2020-08-08,4.5,51000,القاهرة الكبرى`;

function parseCSV(t){
  const lines = t.trim().split(/\r?\n/); const h = lines[0].split(',');
  return lines.slice(1).map(l=>{
    // split respecting Arabic (no quoted commas in our file)
    const v = l.split(','); const o = {};
    h.forEach((k,i)=> o[k.trim()] = (v[i]??'').trim());
    ['id','salary_egp','performance_rating','sales_amount_egp'].forEach(k=> o[k]=Number(o[k]));
    try { const ov = JSON.parse(localStorage.getItem('diwan_upd')||'{}'); if(ov[o.id]) Object.assign(o, ov[o.id]); } catch(e){}
    return o;
  });
}
async function loadRows(){
  try{
    const r = await fetch('../data/company.csv');
    if(r.ok){ ROWS = parseCSV(await r.text()); }
    else ROWS = parseCSV(FALLBACK_CSV);
  }catch(e){ ROWS = parseCSV(FALLBACK_CSV); }
  $('#dbStatus').textContent = `🗄️ ${ROWS.length} سجلًا · employees`;
  renderSchema();
}
function renderSchema(){
  const cols = ROWS.length? Object.keys(ROWS[0]) : [];
  $('#schemaList').innerHTML = cols.map(c=>`<li><code dir="ltr">${c}</code></li>`).join('');
}
function norm(s){ return s.replace(/[أإآ]/g,'ا').replace(/ة/g,'ه').replace(/ى/g,'ي').replace(/[\u064B-\u0652]/g,'').replace(/[؟?،؛!.,\-_]+/g,' '); }
function findDept(q){
  const hasCtx = /قسم|إدارة|ادارة|موظف|عاملين|فريق/.test(q);
  const metric = /مجموع|متوسط|إجمالي|اجمالي/.test(q) && q.includes('مبيعات');
  for(const k in DEPTS){
    if(q.includes(k)){
      if(!hasCtx && metric && DEPTS[k]==='المبيعات') continue;
      if(!hasCtx && ['مبيعات','تسويق','مالية','التسويق','المبيعات','المالية'].includes(k)
        && !/موظف|عدد|كام|كم|أعلى|اعلى|أفضل|افضل|متوسط|مجموع/.test(q)) continue;
      return DEPTS[k];
    }
  } return null;
}
function findCity(q){ for(const c of CITIES){ if(q.includes(c)) return CITY_FIX[c]||c; } return null; }
function findRegion(q){ for(const r of REGIONS){ if(q.includes(r)) return r; } return null; }
function findNum(q){ const m = q.match(/\d+(\.\d+)?/); if(m) return Number(m[0]);
  for(const k in AR_NUM){ if(q.includes(k)) return AR_NUM[k]; } return null; }

function buildSQL(q){
  const keep = $('#keepCtx').checked;
  let dept = findDept(q), city = findCity(q), region = findRegion(q);
  // follow-up inheritance
  let baseWhere = "";
  if(keep && LAST_SQL && /رتبهم|ورتبهم|منهم|دول|اللي فات|^\s*طب|طيب|كمان/.test(q)){
    const m = LAST_SQL.match(/WHERE\s+(.+?)(?:\s+ORDER BY|\s+LIMIT|;?\s*$)/i);
    if(m) baseWhere = m[1];
  }
  const n = norm(q);
  const isCmpAgg = /(أكبر|اكبر|أعلى|اعلى|أقل|اقل|أصغر|اصغر|أكثر|اكثر)\s+من\s+\d/.test(q);
  let agg=null;
  if(!isCmpAgg){ if(/عدد|كام|كم/.test(n)) agg='COUNT'; else if(/مجموع|اجمالي|جمله/.test(n)) agg='SUM';
  else if(/متوسط|معدل/.test(n)) agg='AVG'; else if(/اعلي|اقصي|اكبر|افضل/.test(n)) agg='MAX'; else if(/اقل|ادني|اصغر/.test(n)) agg='MIN'; }
  else { if(/عدد|كام|كم/.test(n)) agg='COUNT'; else if(/مجموع|اجمالي|جمله/.test(n)) agg='SUM'; else if(/متوسط|معدل/.test(n)) agg='AVG'; }
  // order
  let dir = /تنازلي|من الكبير/.test(q)?'DESC':(/تصاعدي|من الصغير/.test(q)?'ASC':(/الاعلي|الأعلى|الاكبر|افضل|أفضل/.test(q)?'DESC':null));
  let hasOrder = /رتب|ترتيب|مرتب |الاعلي|الأعلى|الاقل|الأقل|افضل|أفضل/.test(q);
  let ocol=null;
  if(/مرتب|راتب|اجر|قبض|دخل/.test(q)) ocol='salary_egp';
  else if(/مبيعات|بيع|ايراد|إيراد/.test(q)) ocol='sales_amount_egp';
  else if(/تقييم|اداء|أداء/.test(q)) ocol='performance_rating';
  else if(/تعيين|توظيف/.test(q)) ocol='hire_date';
  let lim=null;
  const isCmpLimit = /(أكبر|اكبر|أصغر|اصغر|أعلى|اعلى|أقل|اقل|أكثر|اكثر)\s+من\s+\d/.test(q);
  if(!isCmpLimit){
    const lm=q.match(/(?:أول|اول|اعلي|أعلي|اكبر|أكبر|افضل|أفضل)\s*(\d+)/);
    if(lm) lim=+lm[1]; else if(/أعلى 5|اعلى 5|أفضل 5/.test(q)) lim=5; else if(/أعلى 10|اعلى 10/.test(q)) lim=10;
    else if(hasOrder && /خمسة/.test(q)) lim=5; else if(hasOrder && /عشرة/.test(q)) lim=10; else if(hasOrder && !dir && !ocol && !lim && /الأعلى|الاعلى|الأفضل/.test(q)) lim=5;
  } else { const m0=q.match(/(?:أول|اول)\s*(\d+)/); if(m0) lim=+m0[1]; }
  // comparison
  let cmp=null; const num=findNum(q);
  let ccol = /مرتب|راتب|اجر|أجر|قبض|دخل/.test(q)?'salary_egp':(/مبيعات|باع|ايراد|إيراد/.test(q)?'sales_amount_egp':(/تقييم|اداء|أداء/.test(q)?'performance_rating':null));
  let cop = /اكبر من|أكبر من|اكثر من|أكثر من|اعلي من|أعلى من|فوق|يزيد عن|يتجاوز/.test(q)?'>':(/اقل من|أقل من|اصغر من|أصغر من|تحت/.test(q)?'<':null);
  if(ccol&&cop&&num!=null) cmp={col:ccol,op:cop,val:num};
  // name
  let nm=null; const nmM=q.match(/اسم[هها]?\s+(\S+)/); if(nmM && nmM[1].length>1 && !/الموظف|القسم/.test(nmM[1])) nm=nmM[1];

  const W=[]; if(baseWhere) W.push(baseWhere);
  if(dept) W.push(`department_ar = '${dept}'`);
  if(city) W.push(`city_ar = '${city}'`);
  if(region) W.push(`region_ar = '${region}'`);
  if(nm) W.push(`(first_name_ar LIKE '%${nm}%' OR last_name_ar LIKE '%${nm}%')`);
  if(cmp) W.push(`${cmp.col} ${cmp.op} ${cmp.val}`);
  const where = W.length? 'WHERE '+W.join(' AND ') : '';
  const SEL = 'id, first_name_ar, last_name_ar, department_ar, city_ar, salary_egp, sales_amount_egp, performance_rating';
  if(lim && (agg==='MAX'||agg==='MIN') && /موظف|عامل|اعرض|عايز|أبغى|ابغى|بدي|وريني|فرجيني/.test(q)) agg=null;
  let target = ocol || (/مبيعات|بيع/.test(q)?'sales_amount_egp':(/مرتب|راتب/.test(q)?'salary_egp':(/تقييم/.test(q)?'performance_rating':'salary_egp')));
  let sql, expl, conf=0.85;
  if(agg==='COUNT'){ sql=`SELECT COUNT(*) AS عدد_الموظفين FROM employees ${where};`; expl='حساب عدد الموظفين المطابقين للشروط.'; }
  else if(['SUM','AVG','MAX','MIN'].includes(agg)){ sql=`SELECT ${agg}(${target}) AS النتيجة FROM employees ${where};`; expl=`دالة ${agg} على ${target}.`; }
  else if(hasOrder||lim){ const c2=ocol||target; const d2=dir||'DESC'; const L=lim?` LIMIT ${lim}`:((/الأعلى|الاعلى|الأفضل|افضل/.test(q))?' LIMIT 5':'');
    sql=`SELECT ${SEL} FROM employees ${where} ORDER BY ${c2} ${d2}${L};`; expl=`عرض مرتب حسب ${c2} ${d2}.`; }
  else { const ob=(hasOrder&&ocol)?` ORDER BY ${ocol} ${dir||'DESC'}`:'';
    sql=`SELECT ${SEL} FROM employees ${where}${ob}${lim?` LIMIT ${lim}`:''};`; expl='عرض بيانات الموظفين.'; if(!W.length) conf=0.55; }
  return {sql:sql.replace(/\s+/g,' ').trim(), expl, conf, dept, city, region};
}

function runLocal(sql){
  // minimal executor mirroring backend over ROWS
  let rows=[...ROWS];
  const wm = sql.match(/WHERE\s+(.+?)(?:\s+ORDER BY|\s+LIMIT|;?\s*$)/i);
  if(wm){
    const conds = wm[1].split(/\s+AND\s+/i);
    for(const c of conds){
      let m;
      if(m=c.match(/(\w+)\s*=\s*'([^']+)'/)){ const [,k,v]=m; rows=rows.filter(r=>String(r[k])===v); }
      else if(m=c.match(/(\w+)\s*([<>])\s*([\d.]+)/)){ const [,k,op,v]=m; rows=rows.filter(r=> op==='>'? +r[k]>+v : +r[k]<+v); }
      else if(m=c.match(/LIKE\s*'%([^%]+)%'/i)){ const v=m[1]; rows=rows.filter(r=> (r.first_name_ar+r.last_name_ar).includes(v)); }
    }
  }
  const aggM = sql.match(/SELECT\s+(COUNT\(\*\)|(?:SUM|AVG|MAX|MIN)\((\w+)\))/i);
  if(aggM){
    if(/COUNT/i.test(aggM[1])) return {columns:['عدد_الموظفين'], rows:[[rows.length]]};
    const fn=aggM[1].match(/(SUM|AVG|MAX|MIN)/i)[1].toUpperCase(), col=aggM[2];
    const vals=rows.map(r=>+r[col]||0); let v=0;
    if(fn==='SUM')v=vals.reduce((a,b)=>a+b,0); if(fn==='AVG')v=vals.length?vals.reduce((a,b)=>a+b,0)/vals.length:0;
    if(fn==='MAX')v=Math.max(...vals,0); if(fn==='MIN')v=Math.min(...vals,0);
    return {columns:['النتيجة'], rows:[[Math.round(v*100)/100]]};
  }
  const om = sql.match(/ORDER BY\s+(\w+)\s+(ASC|DESC)/i);
  if(om){ const [,k,d]=om; rows.sort((a,b)=> d.toUpperCase()==='DESC'? (b[k]>a[k]?1:-1):(a[k]>b[k]?1:-1)); }
  const lm = sql.match(/LIMIT\s+(\d+)/i); if(lm) rows=rows.slice(0,+lm[1]);
  const cols = ['id','first_name_ar','last_name_ar','department_ar','city_ar','salary_egp','sales_amount_egp','performance_rating'];
  return {columns:cols, rows:rows.map(r=>cols.map(c=>r[c]))};
}

let LAST_ROWS=null, LAST_COLS=[];
async function ask(){
  const q=$('#q').value.trim(); if(!q){ $('#q').focus(); return; }
  $('#askBtn').disabled=true; $('#askBtn').textContent='⏳ جارٍ الفهم...';
  let sql, expl, conf, engine='محلي (JS أوفلاين)';
  const useSrv=$('#useServer').checked;
  if(useSrv){
    try{
      const r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,use_llm:true})});
      if(r.ok){ const d=await r.json(); sql=d.sql; expl=d.explanation_ar; conf=d.confidence; engine='سيرفر: '+d.engine;
        renderResult(sql,expl,conf,engine,d.data); pushHist(q,sql); $('#askBtn').disabled=false; $('#askBtn').textContent='🔍 استعلم'; LAST_SQL=sql; return; }
    }catch(e){ /* fall through to local */ }
    $('#engineStatus').textContent='⚙️ محرك محلي (تعذّر السيرفر)';
  }
  const b=buildSQL(q); sql=b.sql; expl=b.expl; conf=b.conf;
  const data=runLocal(sql);
  renderResult(sql,expl,conf,engine,data); pushHist(q,sql); LAST_SQL=sql;
  $('#askBtn').disabled=false; $('#askBtn').textContent='🔍 استعلم';
}
function renderResult(sql,expl,conf,engine,data){
  $('#sqlOut').textContent=sql;
  $('#explOut').textContent='💡 '+expl;
  $('#engineOut').textContent='المحرك: '+engine;
  const cb=$('#confBadge'); cb.textContent=`الثقة ${(conf*100)|0}%`; cb.style.background=conf>0.75?'#0e9f6e':(conf>0.6?'#c9a227':'#b33');
  LAST_COLS=data.columns; LAST_ROWS=data.rows;
  $('#rowCount').textContent=`${data.rows.length} صف`;
  renderTable(data); drawChart(data);
}
function renderTable(data, filter=''){
  const th=data.columns.map(c=>`<th>${c}</th>`).join('');
  const rows=data.rows.filter(r=> !filter || r.join(' ').includes(filter));
  $('#resTable thead').innerHTML=`<tr>${th}</tr>`;
  $('#resTable tbody').innerHTML=rows.length? rows.map(r=>`<tr>${r.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('') : `<tr><td class="muted">لا نتائج مطابقة.</td></tr>`;
}
function drawChart(data){
  const cv=$('#chart'), ctx=cv.getContext('2d'); ctx.clearRect(0,0,cv.width,cv.height);
  if(!data.rows.length) return;
  const ni=data.columns.map((c,i)=>({c,i})).filter(o=>data.rows.every(r=>!isNaN(+r[o.i]))).slice(0,1);
  if(!ni.length){ ctx.fillStyle='#b9ad8a'; ctx.font='14px Cairo'; ctx.fillText('لا أعمدة رقمية للرسم.',20,40); return; }
  const idx=ni[0].i, vals=data.rows.slice(0,12).map(r=>+r[idx]); const labels=data.rows.slice(0,12).map(r=>String(r[1]||r[0]));
  const mx=Math.max(...vals,1), bw=cv.width/vals.length;
  vals.forEach((v,i)=>{ const h=(v/mx)*(cv.height-50);
    const g=ctx.createLinearGradient(0,cv.height-h,0,cv.height); g.addColorStop(0,'#e8c766'); g.addColorStop(1,'#0e9f6e');
    ctx.fillStyle=g; ctx.fillRect(i*bw+6, cv.height-30-h, bw-12, h);
    ctx.fillStyle='#f3ecd9'; ctx.font='11px Cairo'; ctx.fillText(labels[i].slice(0,8), i*bw+8, cv.height-12);
    ctx.fillText(String(v), i*bw+8, cv.height-36-h);
  });
}
function pushHist(q,sql){ HISTORY.unshift({q,sql}); HISTORY=HISTORY.slice(0,20);
  try{localStorage.setItem('diwan_hist',JSON.stringify(HISTORY));}catch(e){} renderHist(); }
function renderHist(){ $('#history').innerHTML = HISTORY.length? HISTORY.map((h,i)=>`<li><b>${h.q}</b><br><code dir="ltr" class="small">${h.sql.slice(0,90)}...</code></li>`).join('') : '<li class="muted">لا استعلامات بعد…</li>'; }

// tabs
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{ document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active')); t.classList.add('active');
  document.querySelectorAll('.tabpanel').forEach(p=>p.classList.add('hidden')); $('#tab-'+t.dataset.tab).classList.remove('hidden'); });
$('#askBtn').onclick=ask;
$('#q').addEventListener('keydown',e=>{ if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)) ask(); });
$('#copySql').onclick=()=>{ navigator.clipboard.writeText($('#sqlOut').textContent); };
$('#searchRows').oninput=e=>{ if(LAST_ROWS) renderTable({columns:LAST_COLS,rows:LAST_ROWS}, e.target.value.trim()); };
$('#csvBtn').onclick=()=>{ if(!LAST_ROWS) return;
  const csv=[LAST_COLS.join(','),...LAST_ROWS.map(r=>r.join(','))].join('\n');
  const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'})); a.download='results.csv'; a.click(); };
$('#clearHist').onclick=()=>{ HISTORY=[]; try{localStorage.removeItem('diwan_hist');}catch(e){} renderHist(); };
$('#serverBtn').onclick=async()=>{ try{ const r=await fetch('/api/health'); const d=await r.json();
  $('#engineStatus').textContent=d.llm? '⚙️ سيرفر + LLM متصل' : `⚙️ سيرفر متصل (${d.rows} سجل)`; }catch(e){ $('#engineStatus').textContent='⚙️ تعذّر السيرفر — وضع محلي'; } };
$('#updBtn').onclick=async()=>{
  const id=+$('#updId').value, col=$('#updCol').value; let val=$('#updVal').value.trim();
  if(['salary_egp','sales_amount_egp','performance_rating'].includes(col)) val=Number(val);
  // local
  const row=ROWS.find(r=>r.id===id); if(row){ row[col]=val;
    try{ const ov=JSON.parse(localStorage.getItem('diwan_upd')||'{}'); ov[id]=ov[id]||{}; ov[id][col]=val; localStorage.setItem('diwan_upd',JSON.stringify(ov)); }catch(e){} }
  $('#updMsg').textContent=`✅ حُفظ محليًا: id=${id} / ${col} = ${val}`;
  try{ const r=await fetch('/api/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({updates:[{[ 'id']:id,[col]:val}]})});
    if(r.ok){ const d=await r.json(); $('#updMsg').textContent+=` + سيرفر: ${d.applied_cells} خلية في data/company.csv`; } }catch(e){}
};
$('#micBtn').onclick=()=>{ const SR=window.webkitSpeechRecognition||window.SpeechRecognition; if(!SR){alert('المتصفح لا يدعم الإملاء الصوتي');return;}
  const r=new SR(); r.lang='ar-EG'; r.onresult=e=>{ $('#q').value=e.results[0][0].transcript; }; r.start(); };
// examples + chips
$('#examples').innerHTML=EXAMPLES.map(e=>`<button>${e}</button>`).join('');
document.querySelectorAll('#examples button').forEach(b=>b.onclick=()=>{ $('#q').value=b.textContent; ask(); });
$('#dialectChips').innerHTML=CHIPS.map(c=>`<button>${c}</button>`).join('');
document.querySelectorAll('#dialectChips button').forEach(b=>b.onclick=()=>{ $('#q').value+=($('#q').value?' ':'')+b.textContent; $('#q').focus(); });

loadRows(); renderHist();
