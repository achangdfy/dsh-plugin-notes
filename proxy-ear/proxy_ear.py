#!/usr/bin/env python3
"""
proxy-ear — 用可测的东西，逼近「听起来怎么样」。

给自己用，也给听不见的人用：一个 wav 进去，每秒一行的响度、频谱质心、
低频占比、变化点；外加「最像冲击」「最像换了个东西」的两个时刻列表。

依赖：numpy。（读 wav 用标准库的 wave，不装别的。）

    python proxy_ear.py song.wav
    python proxy_ear.py song.wav --hop 0.1 --per-second 2

读法：
    响度跃升大      → 有推力
    谱通量大        → 换了东西（新声部、转调、和声切换）
    质心突然下降    → 变厚 / 变闷
    低频占比上升    → 加了重量

警告：这些都是代理指标。它能说「27 秒确实跳了 16 dB」，
      不能说「好听」，更不能说「会起鸡皮疙瘩」。
"""

import argparse
import sys
import wave

import numpy as np


def read_wav(path):
    with wave.open(path, 'rb') as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        raise SystemExit('只支持 16bit PCM 的 wav；其它格式先转一下。')
    x = np.frombuffer(raw, dtype='<i2').astype(np.float64) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def analyze(x, sr, hop_s=0.25, win_s=0.5):
    hop, nwin = int(hop_s * sr), int(win_s * sr)
    win = np.hanning(nwin)
    freqs = np.fft.rfftfreq(nwin, 1 / sr)
    frames, prev = [], None
    for start in range(0, max(1, len(x) - nwin), hop):
        seg = x[start:start + nwin] * win
        rms = float(np.sqrt(np.mean(seg ** 2)) + 1e-12)
        db = 20 * np.log10(rms + 1e-9)
        spec = np.abs(np.fft.rfft(seg))
        tot = spec.sum() + 1e-12
        frames.append(dict(
            t=start / sr,
            db=db,
            centroid=float((spec * freqs).sum() / tot),
            low=float(spec[freqs < 200].sum() / tot),
            flux=0.0 if prev is None else float(np.sqrt(np.mean((spec - prev) ** 2))),
        ))
        prev = spec
    return frames


def bar(v, lo, hi, width=28):
    k = 0.0 if hi <= lo else max(0.0, min(1.0, (v - lo) / (hi - lo)))
    return '█' * int(k * width)


def main():
    ap = argparse.ArgumentParser(description='听不见的时候，用数字看声音。')
    ap.add_argument('wav')
    ap.add_argument('--hop', type=float, default=0.25, help='帧移（秒），默认 0.25')
    ap.add_argument('--window', type=float, default=0.5, help='窗长（秒），默认 0.5')
    ap.add_argument('--per-second', type=float, default=1.0, help='每几秒打一行，默认 1')
    ap.add_argument('--top', type=int, default=3, help='冲击/变化各列几处，默认 3')
    a = ap.parse_args()

    x, sr = read_wav(a.wav)
    frames = analyze(x, sr, a.hop, a.window)
    if not frames:
        raise SystemExit('文件太短。')

    dbs = [f['db'] for f in frames]
    lo, hi = min(dbs), max(dbs)
    print(f'{a.wav}')
    print(f'{len(x)/sr:.2f}s · {len(frames)} 帧 · 响度 {lo:.1f} ~ {hi:.1f} dBFS')
    print(f'直流偏移(整段均值) {x.mean():+.5f}  ← 接近 0 才正常\n')
    print(' 时间   响度          亮度(质心)   低频   变化')
    step = max(1, int(round(a.per_second / a.hop)))
    for i, f in enumerate(frames):
        if i % step:
            continue
        print(f"{f['t']:5.2f}s {f['db']:6.1f} {bar(f['db'], lo, hi)} "
              f"{f['centroid']:6.0f}Hz  {f['low']*100:4.0f}%  {f['flux']:6.1f}")

    jumps = []
    for i in range(1, len(frames)):
        jumps.append((frames[i]['db'] - frames[i - 1]['db'], frames[i], frames[i - 1]))
    jumps.sort(key=lambda j: j[0], reverse=True)

    print(f"\n最像「冲击」的时刻（响度跃升最大的 {a.top} 处）:")
    for d, f, prev in jumps[:a.top]:
        print(f"  {f['t']:5.2f}s  {d:+.1f} dB  → {f['db']:.1f} dBFS")

    print(f"\n最像「换了个东西」的时刻（谱通量最大的 {a.top} 处）:")
    for f in sorted(frames[1:], key=lambda f: f['flux'], reverse=True)[:a.top]:
        print(f"  {f['t']:5.2f}s  novelty={f['flux']:.1f}  质心 {f['centroid']:.0f}Hz")

    if max(frames, key=lambda f: f['low'])['low'] > 0.95 and max(frames, key=lambda f: f['centroid'])['centroid'] < 60:
        print('\n⚠ 质心极低 + 低频占比接近 100%：八成不是「闷」，是直流偏移。')
        print('  查一下合成/导出那步，尤其是相位累加和包络。')


if __name__ == '__main__':
    try:
        main()
    except FileNotFoundError:
        sys.exit('找不到文件。')
