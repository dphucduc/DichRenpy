// Optional: install Playwright separately; uses an existing Chromium binary.
const { chromium } = require(process.env.DICHRENPY_PLAYWRIGHT || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch({executablePath:process.env.CHROMIUM_PATH || '/usr/bin/chromium',headless:true,args:['--no-sandbox']});
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  let pid;
  try {
    await page.goto(process.env.DICHRENPY_URL || 'http://127.0.0.1:5000');
    await page.locator('#demo').click();
    await page.locator('#workspace').waitFor({state:'visible'});
    await page.waitForFunction(()=>document.getElementById('status').textContent.includes('Đã mở mẫu'));
    assert.equal(await page.locator('.row').count(),9);
    assert.equal(await page.locator('[data-field="listener"]').first().inputValue(),'Linh');
    await page.locator('#prompt').click();
    await page.waitForFunction(()=>document.getElementById('prompt-text').value.length>100);
    const prompt=await page.locator('#prompt-text').inputValue();
    const data=JSON.parse(prompt.slice(prompt.indexOf('\n{\n')+1));
    assert.match(data.relationships,/xưng anh/);
    assert.equal(data.batch[0].listener,'Linh');
    // Take the actual created project ID from the batch-scoped export link.
    pid=(await page.locator('#extracted').getAttribute('href')).split('/')[3];
    await page.evaluate(()=>window.scrollTo(0,0));
    await page.screenshot({path:'/tmp/dichrenpy-desktop.png',fullPage:true});
    const entries=data.batch.map(row=>({id:row.id,translation:'VI: '+row.text,notes:''}));
    entries[0].translation='Mất biến';
    // Use the row with a variable to prove rejected imports preserve state.
    const variable=entries.findIndex(row=>row.translation.includes('[player_name]'));
    entries[variable].translation='Thiếu placeholder';
    await page.locator('#result').fill(JSON.stringify({translations:entries}));
    await page.locator('#import').click();
    await page.waitForFunction(()=>document.getElementById('status').classList.contains('error'));
    assert.match(await page.locator('#status').textContent(),/biến|thẻ/);
    const valid=data.batch.map(row=>({id:row.id,translation:'VI: '+row.text,notes:''}));
    await page.locator('#result').fill(JSON.stringify({translations:valid}));
    await page.locator('#import').click();
    await page.waitForFunction(()=>document.getElementById('status').textContent.includes('Đã nhập bản dịch'));
    assert.match(await page.locator('#progress').textContent(),/9 \/ 9/);
    assert.match(await page.locator('.row textarea').first().inputValue(),/^VI:/);
    const download=page.waitForEvent('download');
    await page.locator('#export').click();
    const file=await download;await file.saveAs('/tmp/dichrenpy-browser-export.zip');
    assert.equal(file.suggestedFilename(),'renpy-vietnamese.zip');
    await page.reload();
    await page.getByRole('button',{name:/Tiếp tục: Một chiều mưa/}).last().click();
    assert.match(await page.locator('.row textarea').first().inputValue(),/^VI:/);
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth),true);
    await page.screenshot({path:'/tmp/dichrenpy-mobile.png',fullPage:true});
    assert.deepEqual(errors,[]);
    console.log('Browser smoke passed: sample, prompt, rejected/valid import, export, persistence, mobile.');
  } finally {
    await browser.close();
    // Remove only the synthetic project created by this test.
    if(pid && /^[0-9a-f-]{36}$/.test(pid))fs.rmSync(path.join(__dirname,'../data',pid),{recursive:true,force:true});
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
