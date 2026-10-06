# Synthesizes the 35s soundtrack for index.html (120 BPM, F minor), hit-synced to the
# FX timeline (HITS / GLITCH / ZOOM in index.html). Pure numpy, writes soundtrack.wav.
import numpy as np, wave, os

SR, DUR = 48000, 35.0
N = int(SR * DUR)
L = np.zeros(N); R = np.zeros(N)
SEND_L = np.zeros(N); SEND_R = np.zeros(N)      # reverb bus
DUCK = np.zeros(N)                              # sidechain bus (non-kick musical parts)
DUCK_L = np.zeros(N); DUCK_R = np.zeros(N)
rng = np.random.default_rng(7)
BPM = 120; BEAT = 60 / BPM; BAR = BEAT * 4

def add(sig, at, gain=1.0, pan=0.0, rev=0.0, duck=False):
    if sig.ndim == 1: sl, sr = sig, sig
    else: sl, sr = sig[0], sig[1]
    i = int(round(at * SR)); n = min(len(sl), N - i)
    if n <= 0 or i < 0: return
    gl, gr = gain * np.sqrt(1 - max(pan, 0)) , gain * np.sqrt(1 + min(pan, 0))
    tl, tr = (DUCK_L, DUCK_R) if duck else (L, R)
    tl[i:i+n] += sl[:n] * gl; tr[i:i+n] += sr[:n] * gr
    if rev: SEND_L[i:i+n] += sl[:n] * gl * rev; SEND_R[i:i+n] += sr[:n] * gr * rev

def ts(dur): return np.arange(int(dur * SR)) / SR
def adsr(n, a=.005, d=.1, s=.7, r=.1):
    x = np.arange(n) / SR; tot = n / SR
    e = np.where(x < a, x / a, np.where(x < a + d, 1 - (1 - s) * (x - a) / d, s))
    return e * np.clip((tot - x) / r, 0, 1)
def fftfilt(x, lo=0, hi=None, q=1.0):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); g = np.ones_like(f)
    if hi: g *= 1 / np.sqrt(1 + (f / hi) ** (4 * q))
    if lo: g *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1)) ** (4 * q))
    return np.fft.irfft(X * g, len(x))
def saw(freq, t, detune=0.0, maxh=9000):
    out = np.zeros_like(t)
    for d in ([0] if not detune else [-detune, 0, detune]):
        f = freq * (1 + d); ph = rng.random() * 6.283
        for k in range(1, int(maxh / f) + 1):
            out += np.sin(2 * np.pi * k * f * t + ph * k) / k
    return out / (3 if detune else 1)
def note_hz(n): return 440 * 2 ** ((n - 69) / 12)

# ------------------------------------------------------------------ instruments
def kick():
    t = ts(.5); f = 42 + 140 * np.exp(-t * 32) + 40 * np.exp(-t * 200)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6.5)
    click = rng.standard_normal(len(t)) * np.exp(-t * 400) * .4
    return np.tanh((body + click) * 1.8)
def clap():
    t = ts(.45); n = fftfilt(rng.standard_normal(len(t)), 900, 7000)
    e = sum((t >= k * .011) * np.exp(-np.maximum(t - k * .011, 0) * (60 if k < 3 else 13)) for k in range(4))
    return n * e * .55
def hat(open_=False):
    t = ts(.35 if open_ else .07); n = fftfilt(rng.standard_normal(len(t)), 7000)
    return n * np.exp(-t * (11 if open_ else 70))
def snare():
    t = ts(.25); tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    return (fftfilt(rng.standard_normal(len(t)), 1200, 9000) * np.exp(-t * 22) * .8 + tone * .5)
def sub(freq, dur):
    t = ts(dur); s = np.sin(2 * np.pi * freq * t) + .25 * np.tanh(3 * np.sin(2 * np.pi * freq * t))
    return s * adsr(len(t), .004, .1, .9, .05)
def reese(freq, dur):
    t = ts(dur); s = saw(freq, t, .006, 2500)
    return fftfilt(s, 0, 700) * adsr(len(t), .01, .2, .8, .08)
def pad(notes, dur, bright=1800):
    t = ts(dur); s = sum(saw(note_hz(n), t, .008, 6000) for n in notes)
    s = fftfilt(s, 120, bright) * adsr(len(t), .25, .4, .85, .5)
    st = np.stack([s, np.roll(s, 331)]) / len(notes)
    return st
def pluck(n, dur=.25, bright=4000):
    t = ts(dur); s = saw(note_hz(n), t, .004, 9000)
    s = fftfilt(s, 200, bright) * np.exp(-t * 14)
    return s
def sweep_noise(dur, f0, f1, bw=1.2, rise=True):
    n = int(dur * SR); hop = 512; win = np.hanning(hop * 2); out = np.zeros(n + hop * 2)
    for k, i in enumerate(range(0, n, hop)):
        u = i / n; fc = f0 * (f1 / f0) ** u
        seg = rng.standard_normal(hop * 2) * win
        X = np.fft.rfft(seg); f = np.fft.rfftfreq(hop * 2, 1 / SR)
        g = np.exp(-(np.log2(np.maximum(f, 1) / fc) / bw) ** 2)
        out[i:i + hop * 2] += np.fft.irfft(X * g, hop * 2)
    out = out[:n]; env_ = np.linspace(0, 1, n) ** 2 if rise else np.linspace(1, 0, n) ** 1.5
    return out * env_
def boom():
    t = ts(2.5); f = 30 + 90 * np.exp(-t * 9)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    n = fftfilt(rng.standard_normal(len(t)), 40, 3000) * np.exp(-t * 4) * .5
    return np.tanh((s + n) * 1.5)
def crash():
    t = ts(2.8); n = fftfilt(rng.standard_normal(len(t)), 3500)
    return n * np.exp(-t * 1.6) * (1 - np.exp(-t * 300))
def whoosh(dur, up=True):
    s = sweep_noise(dur, 300 if up else 6000, 6000 if up else 300, 1.0, True)
    return s * np.sin(np.linspace(0, np.pi, len(s))) ** .5
def zap():
    t = ts(.6); f = 2400 * np.exp(-t * 7) + 80
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5) * .5
def tick(f=2600):
    t = ts(.03); return np.sin(2 * np.pi * f * t) * np.exp(-t * 180)
def stab(notes, dur=.4):
    t = ts(dur); s = sum(saw(note_hz(n), t, .01, 9000) for n in notes)
    return fftfilt(s, 150, 5000) * np.exp(-t * 7) / len(notes)
def twang():
    t = ts(.5); f = 160 * (1 + .25 * np.exp(-t * 30))
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) + .4 * np.sin(4 * np.pi * np.cumsum(f) / SR)) * np.exp(-t * 9)
def thunk():
    t = ts(.6); f = 70 + 220 * np.exp(-t * 40)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 10)
    w = fftfilt(rng.standard_normal(len(t)), 300, 2500) * np.exp(-t * 35)
    return np.tanh((s + w * .8) * 2)

# ------------------------------------------------------------------ harmony (F minor: Fm Db Ab Eb)
CH = [[53, 56, 60, 65], [49, 53, 56, 61], [56, 60, 63, 68], [51, 55, 58, 63]]
ROOT = [41, 37, 44, 39]
ARP = [[65, 68, 72, 75], [61, 65, 68, 73], [68, 72, 75, 80], [63, 67, 70, 75]]
def bar_idx(t): return int(t // BAR) % 4

FULL = [(4.0, 22.0), (26.0, 34.0)]
BREAK = (22.0, 26.0)
def in_full(t): return any(a <= t < b for a, b in FULL)

# pads everywhere (filtered in intro / break)
for b in range(int(DUR // BAR) + 1):
    t0 = b * BAR
    if t0 >= 34: break
    br = 700 if t0 < 2 else 1200 if t0 < 4 else 1100 if BREAK[0] <= t0 < 24 else 2200
    add(pad(CH[b % 4], BAR + .6, br), t0, .32, rev=.5, duck=True)

# drums + bass + arp in full sections
k = kick(); cl = clap(); hc = hat(); ho = hat(True); sn = snare()
for i in range(int(DUR / (BEAT / 4))):
    t = i * BEAT / 4; step = i % 16
    if not in_full(t): continue
    if t >= 33.98: continue
    if step % 4 == 0: add(k, t, 1.0)
    if step in (4, 12): add(cl, t, .55, rev=.25)
    if step % 4 == 2: add(ho, t, .16, pan=.2)
    if step % 2 == 1: add(hc, t, .1, pan=-.3)
    if step in (14, 15) and (int(t // BAR) % 2): add(hc, t, .12, pan=.4)
    # bass: off-beat 8ths
    if step % 4 == 2 or step == 0:
        r = ROOT[bar_idx(t)]
        add(sub(note_hz(r), BEAT * .45), t, .5, duck=True)
        add(reese(note_hz(r + 12), BEAT * .45), t, .18, duck=True)
    # arp
    if step % 2 == 0 and t >= 8.0:
        nn = ARP[bar_idx(t)][(i // 2) % 4]
        add(pluck(nn + (12 if (i // 8) % 4 == 3 else 0)), t, .085, pan=.35 * np.sin(i * .7), rev=.35, duck=True)

# intro / break textures
add(zap(), .05, .5, rev=.6)
add(sweep_noise(1.6, 200, 4000), .4, .3, rev=.4)
add(whoosh(.7), .3, .35, pan=-.6); add(whoosh(.7), .3, .35, pan=.6)
add(whoosh(.8), .85, .3)
for i in range(16):                       # snare roll into the drop
    t = 3.0 + (1 - (1 - i / 16) ** 1.4) * .9
    add(sn, t, .12 + .3 * i / 16, rev=.2)
add(sweep_noise(1.2, 400, 9000), 2.8, .45, rev=.3)
for t0 in (2.0, 2.5, 3.0, 3.5):           # heartbeat sub in intro tail
    add(kick(), t0, .55 if t0 > 2 else 0)
for t, n in [(22.0, [53, 56, 60]), (22.5, [53, 56, 60]), (23.0, [49, 53, 56]), (23.5, [49, 53, 56])]:
    add(stab([x + 12 for x in n]), t, .5, rev=.5); add(sub(note_hz(n[0] - 12), .4), t, .55)
for i in range(8):
    add(hc, 24.35 + i * BEAT / 2, .09, pan=.3 * (-1) ** i)
add(sweep_noise(1.6, 300, 8000), 24.4, .35, rev=.3)
for i in range(12):
    t = 25.0 + (1 - (1 - i / 12) ** 1.3) * .95
    add(sn, t, .1 + .25 * i / 12, rev=.2)

# counter ticks 8.15 -> 9.8 accelerating with rising pitch
t = 8.15; i = 0
while t < 9.75:
    u = (t - 8.15) / 1.6
    add(tick(1800 + 2200 * u), t, .25 * (1 - u * .4), pan=.4 * np.sin(i)); i += 1
    t += .085 * (1 - u) ** 1.6 + .03
add(sweep_noise(1.6, 600, 10000), 8.2, .3)

# transitions
for t0, d in [(3.55, .5), (7.55, .5), (11.6, .45), (15.55, .5), (25.6, .45), (30.0, .55)]:
    add(whoosh(d), t0, .38, rev=.3)
# glitch stutters
for a, b in [(3.86, 4.06), (7.86, 8.04), (11.88, 12.04), (21.9, 22.12), (22.98, 23.12), (25.86, 26.04), (30.36, 30.54)]:
    tt = a
    while tt < b:
        add(fftfilt(rng.standard_normal(int(.02 * SR)), 2000, 9000) * .5, tt, .25, pan=rng.uniform(-.6, .6)); tt += .03

# HITS (mirrors index.html)
HITS = [(2.0, 1.0), (4.0, 1.1), (8.0, .5), (9.8, 1.2), (12.0, .6), (16.0, .8), (22.0, .9), (26.0, .6), (30.5, 1.2)]
for t0, kk in HITS:
    add(boom(), t0, .55 * kk, rev=.3)
    add(crash(), t0, .2 * kk, rev=.5)
add(fftfilt(rng.standard_normal(int(.2 * SR)), 2000) * np.exp(-ts(.2) * 20), 4.32, .25)
add(stab([65, 68, 72, 77], .6), 9.8, .45, rev=.6)
add(stab([65, 68, 72, 77], .6), 30.5, .5, rev=.7)
# arrow
add(twang(), 28.2, .5, rev=.3, pan=-.4)
add(whoosh(.36), 28.27, .55, pan=-.2)
add(thunk(), 28.62, .9, rev=.35, pan=.3)
add(crash(), 28.62, .22, rev=.5, pan=.3)
add(boom(), 28.62, .45)
add(stab([60, 65, 68, 72], .45), 29.05, .45, rev=.5)
# outro final chord swell
add(pad([53, 60, 65, 68, 72], 4.5, 2600), 30.5, .4, rev=.8)

# ------------------------------------------------------------------ sidechain + reverb + master
kick_times = [i * BEAT for i in range(int(DUR / BEAT)) if in_full(i * BEAT) and i * BEAT < 33.98]
sc = np.ones(N)
for kt in kick_times:
    i = int(kt * SR); n = min(int(BEAT * SR), N - i); x = np.arange(n) / SR
    sc[i:i+n] = np.minimum(sc[i:i+n], 1 - .75 * np.exp(-x * 9))
L += DUCK_L * sc; R += DUCK_R * sc

def reverb(x, seconds=2.4, seed=0):
    r = np.random.default_rng(seed); n = int(seconds * SR); tt = np.arange(n) / SR
    ir = r.standard_normal(n) * np.exp(-tt * 3.0); ir = fftfilt(ir, 200, 6000); ir /= np.sqrt(np.sum(ir ** 2))
    m = len(x) + n; F = 1 << (m - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, F) * np.fft.rfft(ir, F), F)[:len(x)]
L += reverb(SEND_L, seed=1) * .35; R += reverb(SEND_R, seed=2) * .35

# fade
fade = np.clip((DUR - .05 - np.arange(N) / SR) / 1.2, 0, 1); fade = np.minimum(fade, np.clip(np.arange(N) / SR / .02, 0, 1))
L *= fade; R *= fade
mx = max(np.abs(L).max(), np.abs(R).max())
L = np.tanh(L / mx * 1.4) ; R = np.tanh(R / mx * 1.4)
pk = max(np.abs(L).max(), np.abs(R).max()); L *= .89 / pk; R *= .89 / pk

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'soundtrack.wav')
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.stack([L, R], 1) * 32767).astype('<i2').tobytes())
print('wrote', out)
