let project = null, batches = [], batchIndex = 0;
const $ = id => document.getElementById(id);
function status(message, error=false) { $('status').textContent=message; $('status').className=error?'error':''; $('status').hidden=false; }
async function api(path, options={}) {
  const response=await fetch(path, options);
  const data=await response.json();
  if(!response.ok) throw Error(data.error || 'Yêu cầu thất bại.');
  return data;
}
const json = (method, body) => ({method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
function guarded(fn) { return async event => {const button=event?.currentTarget; if(button?.tagName==='BUTTON')button.disabled=true; try{await fn(event);}catch(e){status(e.message,true);}finally{if(button?.tagName==='BUTTON')button.disabled=false;}}; }
function selected() { return batches[batchIndex]?.rows || []; }
function collect() {
  const edits=[...document.querySelectorAll('.row')].map(el=>({id:el.dataset.id,speaker:el.querySelector('[data-field="speaker"]').value,listener:el.querySelector('[data-field="listener"]').value,translation:el.querySelector('textarea').value}));
  return {context:$('context').value,relationships:$('relationships').value,glossary:$('glossary').value,rows:edits};
}
async function persist() { project=await api(`/api/projects/${project.id}`,json('PUT',collect())); updateProgress(); }
function updateProgress() { $('progress').textContent=`${project.rows.filter(r=>r.translation).length} / ${project.rows.length} câu đã dịch`; }
function renderRows() {
  $('rows').replaceChildren();
  for(const row of selected()) {
    const el=document.createElement('div'); el.className='row'; el.dataset.id=row.id;
    const head=document.createElement('div');head.className='row-head';
    const position=document.createElement('span');position.textContent=`${row.file}:${row.line} · ${row.kind}`;head.append(position);
    for(const [field,label] of [['speaker','Người nói'],['listener','Người nghe']]) {
      const wrap=document.createElement('label');wrap.textContent=label;
      const input=document.createElement('input');input.value=row[field];input.dataset.field=field;input.placeholder=field==='listener'?'Chưa xác nhận':'';input.maxLength=200;wrap.append(input);head.append(wrap);
    }
    const source=document.createElement('p');source.className='source';source.textContent=row.text;
    const translation=document.createElement('textarea');translation.rows=2;translation.value=row.translation;translation.placeholder='Bản dịch tiếng Việt…';translation.setAttribute('aria-label',`Bản dịch ${row.id}`);
    el.append(head,source,translation);
    if(row.notes){const note=document.createElement('p');note.className='notes';note.textContent=`Cần soát: ${row.notes}`;el.append(note);}
    $('rows').append(el);
  }
  $('prompt-text').value=''; $('copy').disabled=true; $('result').value='';
  $('prompt').disabled=!selected().length;
}
function openProject(data) {
  project=data; batchIndex=0;batches=[];
  for(const row of project.rows) {
    let last=batches.at(-1);
    if(!last || last.file!==row.file || last.scene!==row.scene || last.rows.length===60) {last={file:row.file,scene:row.scene,rows:[]};batches.push(last);}
    last.rows.push(row);
  }
  $('welcome').hidden=true;$('workspace').hidden=false;$('project-name').textContent=project.name;
  for(const field of ['context','relationships','glossary'])$(field).value=project[field];
  $('characters').replaceChildren();
  for(const [code,name] of Object.entries(project.characters)){const tag=document.createElement('span');tag.textContent=`${code}: ${name}`;$('characters').append(tag);}
  $('warnings').textContent=project.warnings.join('\n');$('warnings').hidden=!project.warnings.length;
  $('batch').replaceChildren();batches.forEach((batch,i)=>{const option=document.createElement('option');option.value=i;option.textContent=`${i+1}. ${batch.file} / ${batch.scene} · ${batch.rows.length} câu`;$('batch').append(option);});
  $('extracted').href=`/api/projects/${project.id}/export?original=1`;
  renderRows();updateProgress();
}
function refreshBatchRows(){ for(const batch of batches)batch.rows=batch.rows.map(old=>project.rows.find(r=>r.id===old.id)); }
$('upload').onsubmit=guarded(async event=>{
  event.preventDefault();const submit=$('upload').querySelector('button');submit.disabled=true;
  status('Đang mở tệp và xử lý kịch bản…');
  try{const body=new FormData();body.append('name',$('name').value);for(const file of $('files').files)body.append('files',file);openProject(await api('/api/projects',{method:'POST',body}));status('Đã mở dự án. Điền bối cảnh và xác nhận người nghe trước khi dịch.');}finally{submit.disabled=false;}
});
$('batch').onchange=guarded(async()=>{const next=Number($('batch').value);try{await persist();refreshBatchRows();batchIndex=next;renderRows();}catch(e){$('batch').value=batchIndex;throw e;}});
$('save').onclick=guarded(async()=>{await persist();refreshBatchRows();status('Đã lưu sổ tay và các chỉnh sửa.');});
$('prompt').onclick=guarded(async()=>{await persist();refreshBatchRows();const data=await api(`/api/projects/${project.id}/prompt`,json('POST',{ids:selected().map(r=>r.id)}));$('prompt-text').value=data.prompt;$('copy').disabled=false;status('Yêu cầu đã sẵn sàng. Sao chép sang Gemini web.');});
$('copy').onclick=guarded(async()=>{try{await navigator.clipboard.writeText($('prompt-text').value);status('Đã sao chép. Dán vào Gemini rồi lấy kết quả JSON.');}catch{ $('prompt-text').focus();$('prompt-text').select();status('Trình duyệt không cho sao chép tự động. Nội dung đã được chọn; nhấn Ctrl+C hoặc Cmd+C.');}});
$('import').onclick=guarded(async()=>{await persist();project=await api(`/api/projects/${project.id}/import`,json('POST',{text:$('result').value,ids:selected().map(r=>r.id)}));refreshBatchRows();renderRows();updateProgress();status('Đã nhập bản dịch và kiểm tra biến, thẻ. Hãy đọc lại các câu trước khi xuất.');});
$('export').onclick=guarded(async()=>{await persist();window.location.href=`/api/projects/${project.id}/export`;status('Đã lưu và xuất các tệp .rpy. Hãy thử trên bản sao game trước khi sử dụng.');});
$('back').onclick=guarded(async()=>{await persist();$('workspace').hidden=true;$('welcome').hidden=false;await listProjects();});
async function listProjects(){const projects=await api('/api/projects');$('existing').replaceChildren();for(const p of projects){const button=document.createElement('button');button.className='secondary';button.textContent=`Tiếp tục: ${p.name}`;button.onclick=guarded(async()=>{openProject(await api(`/api/projects/${p.id}`));status('Đã mở lại dự án đã lưu.');});$('existing').append(button);}}
$('demo').onclick=guarded(async()=>{const body=new FormData();body.append('name','Một chiều mưa — Bản mẫu');body.append('files',new Blob(['define m = Character("Minh")\ndefine l = Character("Linh")\n\nlabel start:\n    scene bg cafe\n    m "You came. I thought you wouldn’t."\n    l "And let you drink alone? Not a chance."\n    "She sets a rain-soaked umbrella by the door."\n    m "I saved your usual seat, [player_name]."\n    l "{i}Our{/i} usual seat, you mean."\n    menu:\n        "Tell her you missed her":\n            m "I missed you."\n        "Change the subject":\n            m "Still taking your coffee black?"\n    return\n'],{type:'text/plain'}),'script.rpy');openProject(await api('/api/projects',{method:'POST',body}));$('context').value='Hai người từng yêu nhau gặp lại tại quán cà phê trong chiều mưa. Giọng văn nhẹ nhàng, ấm áp, có chút ngập ngừng và trêu đùa.';$('relationships').value='Minh: nam, 26 tuổi, kín đáo. Linh: nữ, 24 tuổi, tinh nghịch. Minh gọi Linh là em, xưng anh. Linh gọi Minh là anh, xưng em. [player_name] là biến tên trong game, giữ nguyên.';for(const row of project.rows){if(row.speaker==='m')row.listener='Linh';if(row.speaker==='l')row.listener='Minh';}refreshBatchRows();renderRows();await persist();status('Đã mở mẫu. Tạo yêu cầu dịch để thử với Gemini.');});
listProjects().catch(e=>status(e.message,true));
window.addEventListener('beforeunload',event=>{if(project && !$('workspace').hidden && JSON.stringify(collect())!==JSON.stringify({context:project.context,relationships:project.relationships,glossary:project.glossary,rows:selected().map(r=>({id:r.id,speaker:r.speaker,listener:r.listener,translation:r.translation}))})){event.preventDefault();event.returnValue='';}});
