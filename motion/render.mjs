// Renders index.html frame-by-frame with headless Chromium and pipes PNGs into ffmpeg.
import { createRequire } from 'module';
const { chromium } = createRequire('/opt/node22/lib/node_modules/')('playwright');
import { spawn } from 'child_process';
import path from 'path';

const FPS = 30, DURATION = 25;
const mode = process.argv[2] || 'video';           // 'video' | 'stills'
const out = process.argv[3] || 'out/genlayer-rally.mp4';
const browser = await chromium.launch({ args: ['--allow-file-access-from-files'], executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto('file://' + path.resolve('index.html') + '?capture');
await page.evaluate(() => window.ready);

const grab = t => page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/png').split(',')[1]; }, t);

if (mode === 'stills') {
  const fs = await import('fs');
  for (const t of process.argv.slice(4).map(Number)) fs.writeFileSync(`out/still-${t}.png`, Buffer.from(await grab(t), 'base64'));
} else {
  const ff = spawn('ffmpeg', ['-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-', '-c:v', 'libx264',
    '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'ignore', 'inherit'] });
  const N = FPS * DURATION;
  for (let i = 0; i < N; i++) {
    const buf = Buffer.from(await grab(i / FPS), 'base64');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 60 === 0) console.log(`frame ${i}/${N}`);
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
}
await browser.close();
