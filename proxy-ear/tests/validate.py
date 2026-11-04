"""
validate.py — 代理耳朵的自检：用「已知答案」的信号，看工具读得对不对。

为什么不用真实音乐：本机没有 ffmpeg、没有音频解码库，也找不到本地音乐文件。
而成品音乐没有真值——你觉得「这里该起鸡皮疙瘩」没法当答案。
所以用四种真值明确的信号：

  1. 纯正弦 440Hz           → 质心 ≈ 440Hz
  2. 前 1 秒 300Hz、后 1 秒 3000Hz → 质心跃升 ≈ 10 倍
  3. 音量台阶：-12dB 跳到 0dB      → 检出跃升 ≈ +12dB
  4. 静音 → 有声             → 跃升巨大，且能指出位置

用法: python tests/validate.py
"""

import os
import sys
import tempfile
import wave

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from proxy_ear import analyze  # noqa: E402

SR = 44100


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    pcm = (x * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def tone(f, dur, amp=0.5):
    t = np.arange(int(dur * SR)) / SR
    return amp * np.sin(2 * np.pi * f * t)


def centroid_at(frames, t):
    return min(frames, key=lambda f: abs(f['t'] - t))['centroid']


def jump_at(frames, t):
    # 找 t 附近最大的一次跃升
    near = [i for i, f in enumerate(frames) if abs(f['t'] - t) < 0.6]
    best = 0.0
    for i in near:
        if i == 0:
            continue
        d = frames[i]['db'] - frames[i - 1]['db']
        best = max(best, d)
    return best


def check(name, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {name}  :: {detail}")
    return ok


def main():
    tmp = tempfile.mkdtemp(prefix='proxy-ear-validate-')
    results = []

    # 1. 纯正弦
    p = os.path.join(tmp, 'sine440.wav')
    write_wav(p, tone(440, 2.0))
    fr = analyze(*_read(p))
    c = float(np.median([f['centroid'] for f in fr]))
    results.append(check('纯正弦 440Hz 的质心', abs(c - 440) < 60, f'实测 {c:.0f}Hz'))

    # 2. 换音：300 → 3000
    p = os.path.join(tmp, 'switch.wav')
    write_wav(p, np.concatenate([tone(300, 1.0), tone(3000, 1.0)]))
    fr = analyze(*_read(p))
    c1, c2 = centroid_at(fr, 0.4), centroid_at(fr, 1.6)
    results.append(check('低频转高频，质心应跃升', c2 > c1 * 3, f'{c1:.0f}Hz → {c2:.0f}Hz'))

    # 3. 音量台阶 +12dB
    p = os.path.join(tmp, 'step.wav')
    quiet = tone(440, 1.0, amp=0.125)     # 约 -18dBFS
    loud = tone(440, 1.0, amp=0.5)        # 约 -6dBFS
    write_wav(p, np.concatenate([quiet, loud]))
    fr = analyze(*_read(p))
    j = jump_at(fr, 1.0)
    results.append(check('音量台阶应检出 ~+12dB', 9 <= j <= 15, f'实测 +{j:.1f}dB'))

    # 4. 静音 → 有声
    p = os.path.join(tmp, 'silence.wav')
    write_wav(p, np.concatenate([np.zeros(int(1.0 * SR)), tone(880, 1.0)]))
    fr = analyze(*_read(p))
    j = jump_at(fr, 1.0)
    peak_t = max(range(len(fr)), key=lambda i: fr[i]['db'])
    results.append(check('静音后出现声音', j > 30, f'跃升 +{j:.1f}dB，最响在 {fr[peak_t]["t"]:.2f}s'))

    print(f"\n{sum(results)}/{len(results)} 通过")
    return 0 if all(results) else 1


def _read(path):
    with wave.open(path, 'rb') as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float64) / 32768.0
    return x, sr


if __name__ == '__main__':
    sys.exit(main())
