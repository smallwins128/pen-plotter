// Print the build book to an A4-landscape PDF, one page per step: node hardware/book/print_pdf.js (needs playwright + Chromium)
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const src = fs.readFileSync(process.argv[2] || '/home/user/pen-plotter/hardware/book/build_book.html', 'utf8');
  const svgs = src.match(/<svg class="page"[\s\S]*?<\/svg>/g);
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>
@page{size:A4 landscape;margin:0}
html,body{margin:0;padding:0;background:#fff}
svg.page{display:block;width:297mm;height:210mm;page-break-after:always;break-after:page}
</style></head><body>${svgs.join('\n')}</body></html>`;
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const p = await b.newPage();
  await p.setContent(html, { waitUntil: 'load' });
  await p.pdf({ path: process.argv[3] || '/home/user/pen-plotter/hardware/book/build_book.pdf', format: 'A4', landscape: true, printBackground: true, margin: {top:0,right:0,bottom:0,left:0} });
  console.log(svgs.length, 'pages'); await b.close();
})();
