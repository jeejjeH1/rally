// Deterministic frame renderer: headless Chromium draws index.html at exact timestamps,
// frames are piped as JPEG into ffmpeg. Work is split across parallel workers, each
// encoding one segment, then segments are concatenated losslessly and muxed with audio.
//
//   node render.mjs stills 2.5 9.9 ...        -> out/still-<t>.png
//   node render.mjs video [workers]            -> out/genlayer-rally-v2-60fps.mp4
import { createRequire } from 'module';
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
const { chromium } = createRequire('/opt/node22/lib/node_modules/')('playwright');

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FPS = 60, DURATION = 35, N = FPS * DURATION;
const OUT = path.join(HERE, 'out'); fs.mkdirSync(OUT, { recursive: true });
const EXE = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const mode = process.argv[2] || 'video';

async function openPage() {
  const browser = await chromium.launch({ executablePath: EXE, args: ['--allow-file-access-from-files', '--enable-unsafe-swiftshader', '--use-angle=swiftshader', '--disable-gpu-vsync'] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  page.on('console', m => console.log('[page]', m.text()));
  page.on('pageerror', e => console.error('[pageerror]', e.message));
  await page.goto('file://' + path.join(HERE, 'index.html') + '?capture');
  await page.evaluate(() => window.ready);
  return { browser, page };
}
const grab = (page, t, q) => page.evaluate(([t, q]) => window.grab(t, q).split(',')[1], [t, q]);
const run = (cmd, args) => new Promise((res, rej) => { const p = spawn(cmd, args, { stdio: ['ignore', 'ignore', 'inherit'] }); p.on('close', c => c ? rej(new Error(cmd + ' ' + c)) : res()); });

if (mode === 'stills') {
  const { browser, page } = await openPage();
  for (const t of process.argv.slice(3).map(Number)) {
    const t0 = Date.now();
    const b64 = await page.evaluate(t => { window.render(t); return document.getElementById('gl').toDataURL('image/png').split(',')[1]; }, t);
    fs.writeFileSync(path.join(OUT, `still-${t}.png`), Buffer.from(b64, 'base64'));
    console.log('still', t, Date.now() - t0, 'ms');
  }
  await browser.close();
} else {
  const workers = +(process.argv[3] || 4);
  const per = Math.ceil(N / workers);
  const started = Date.now();
  await Promise.all(Array.from({ length: workers }, async (_, w) => {
    const a = w * per, b = Math.min(N, a + per);
    const { browser, page } = await openPage();
    const seg = path.join(OUT, `seg${w}.mp4`);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', String(FPS), '-i', '-',
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-r', String(FPS),
      '-g', '120', '-bf', '2', '-x264-params', 'keyint=120:min-keyint=60', seg], { stdio: ['pipe', 'ignore', 'inherit'] });
    for (let i = a; i < b; i++) {
      const buf = Buffer.from(await grab(page, i / FPS, .97), 'base64');
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if ((i - a) % 120 === 0) console.log(`w${w} frame ${i - a}/${b - a}  (${((Date.now() - started) / 1000).toFixed(0)}s)`);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
    await browser.close();
  }));
  fs.writeFileSync(path.join(OUT, 'list.txt'), Array.from({ length: workers }, (_, w) => `file 'seg${w}.mp4'`).join('\n'));
  const wav = path.join(HERE, 'soundtrack.wav');
  const final = path.join(OUT, 'genlayer-rally-v2-60fps.mp4');
  await run('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(OUT, 'list.txt'),
    ...(fs.existsSync(wav) ? ['-i', wav, '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-shortest'] : []),
    '-c:v', 'copy', '-movflags', '+faststart', final]);
  console.log('done ->', final, ((Date.now() - started) / 1000).toFixed(0) + 's');
}
