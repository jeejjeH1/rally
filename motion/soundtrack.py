# Synthesizes a 25s electronic soundtrack synced to the scene timeline in index.html.
import numpy as np, wave

SR, DUR = 44100, 25.0
N = int(SR * DUR)
t = np.arange(N) / SR
L = np.zeros(N); Rr = np.zeros(N)
rng = np.random.default_rng(3)

BPM = 128; BEAT = 60 / BPM; START = 0.75
IMPACTS = [0.75, 8.7]
CUTS = [3.3, 6.7, 10.8, 15.8, 18.6, 21.8]

def add(sig, at, gain=1.0, pan=0.0):
    i = int(at * SR); n = min(len(sig), N - i)
    if n <= 0: return
    L[i:i+n] += sig[:n] * gain * (1 - max(pan, 0))
    Rr[i:i+n] += sig[:n] * gain * (1 + min(pan, 0))

def env(n, a, d):
    x = np.arange(n) / SR
    return np.minimum(x / a, 1) * np.exp(-x / d)

def kick():
    n = int(.45 * SR); x = np.arange(n) / SR
    f = 45 + 110 * np.exp(-x * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 7) + .3 * np.tanh(rng.standard_normal(n) * np.exp(-x * 300))

def hat(open_=False):
    n = int((.18 if open_ else .05) * SR)
    s = rng.standard_normal(n); s = np.diff(np.concatenate([[0], s]))
    return s * np.exp(-np.arange(n) / SR / (.06 if open_ else .012))

def clap():
    n = int(.3 * SR); s = rng.standard_normal(n)
    e = sum(np.exp(-np.maximum(np.arange(n) / SR - k * .012, 0) * 40) * (np.arange(n) / SR >= k * .012) for k in range(3))
    return np.diff(np.concatenate([[0], s])) * e * .6

def note(freq, dur, kind='saw'):
    n = int(dur * SR); x = np.arange(n) / SR
    out = np.zeros(n)
    for det in (-0.12, 0, 0.12):
        ph = (freq * 2 ** (det / 12) * x) % 1
        out += (2 * ph - 1) if kind == 'saw' else np.sin(2 * np.pi * freq * x)
    return out / 3

def lowpass(s, a):
    # cheap low-pass: two cascaded moving averages with window ~ 1/a samples
    w = max(1, int(1 / a))
    for _ in range(2):
        c = np.cumsum(np.concatenate([[0.0], s]))
        s = (c[w:] - c[:-w]) / w
        s = np.concatenate([np.zeros(w - 1), s])
    return s

def impact():
    n = int(2.5 * SR); x = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(30 + 90 * np.exp(-x * 8)) / SR) * np.exp(-x * 1.6)
    noise = rng.standard_normal(n) * np.exp(-x * 4) * .5
    return np.tanh((boom + noise) * 1.5)

def whoosh(d=0.6, rev=False):
    n = int(d * SR); x = np.linspace(0, 1, n)
    s = lowpass(rng.standard_normal(n), .08) * 3
    e = np.sin(np.pi * x) ** 2
    return s * (e[::-1] if rev else e)

def riser(d):
    n = int(d * SR); x = np.arange(n) / SR; p = x / d
    f = 200 * 2 ** (p * 3)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * .4
    noise = (lowpass(rng.standard_normal(n), .05) * (1 - p) + lowpass(rng.standard_normal(n), .4) * p) * 2
    return (tone + noise) * p ** 2

# --- chords (A minor: Am F C G), 2 beats each... one bar each
CHORDS = [[220, 261.6, 329.6], [174.6, 220, 261.6], [261.6, 329.6, 392], [196, 246.9, 293.7]]
BASS = [55, 43.65, 65.41, 49]
bar = BEAT * 4
k = 0
for b in range(int(DUR / bar) + 1):
    at = b * bar
    ch = CHORDS[b % 4]
    pad = sum(note(f, bar, 'saw') for f in ch) / 3
    pad = lowpass(pad, .04) * env(len(pad), .3, 3)
    add(pad, at, .18, -.2); add(pad, at + .012, .18, .2)

# --- drums & bass from the first impact; bigger after the drop
beat_t = START
i = 0
while beat_t < DUR - 0.8:
    drop = beat_t >= 8.7
    quiet = 6.7 <= beat_t < 8.7 or beat_t > 23.6
    if not quiet:
        add(kick(), beat_t, .9)
        add(hat(), beat_t + BEAT / 2, .12 if not drop else .18, .3)
        if drop: add(hat(), beat_t + BEAT * .75, .08, -.3)
        if i % 2 == 1: add(clap(), beat_t, .35 if drop else .22)
        b = int((beat_t - START) / bar) % 4
        bl = note(BASS[b], BEAT * .9, 'saw')
        bl = lowpass(bl, .06 if drop else .03) * env(len(bl), .005, .25)
        add(bl, beat_t + BEAT / 2, .55 if drop else .4)
    i += 1; beat_t += BEAT

# --- arp lead after drop
arp_notes = [440, 523.3, 659.3, 880, 659.3, 523.3]
at = 8.7; j = 0
while at < 23.5:
    f = arp_notes[j % len(arp_notes)] * (1 if int((at - 8.7) / bar) % 2 == 0 else 0.89)
    s = note(f, BEAT / 4, 'saw') * env(int(BEAT / 4 * SR), .002, .07)
    add(s, at, .10, .4 if j % 2 else -.4)
    at += BEAT / 4; j += 1

for x in IMPACTS: add(impact(), x, .9)
for c in CUTS: add(whoosh(.5), c - .45, .35)
add(riser(1.9), 6.8, .45)
add(whoosh(1.0, rev=True), 0.0, .4)

mix = np.stack([L, Rr], 1)
mix = np.tanh(mix * 1.1)
fade = np.ones(N); fn = int(1.5 * SR); fade[-fn:] = np.linspace(1, 0, fn)
mix *= fade[:, None]
mix /= np.abs(mix).max() / .92
with wave.open('out/soundtrack.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print('ok')
