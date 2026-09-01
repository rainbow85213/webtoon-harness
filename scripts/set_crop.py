#!/usr/bin/env python3
"""뷰어의 패널 크롭 위치(object-position, op)를 일괄 조정한다.

크롭은 조립 단계 CSS이므로 재렌더 없이 바꿀 수 있다.
컷 높이(ph)는 승인된 완급이라 건드리지 않는다 — op 만 바꾼다.

사용: python3 scripts/set_crop.py <index.html> P2=25 P3=78 ...
"""
import re, sys
from pathlib import Path

def main(argv):
    path = Path(argv[1]); changes = {}
    for a in argv[2:]:
        k, v = a.split('='); changes[int(k.lstrip('Pp'))] = int(v)
    src = path.read_text(encoding='utf-8'); out = []; n = 0
    for ln in src.split('\n'):
        m = re.search(r'src:"panels/panel_(\d+)\.(?:png|jpg)"', ln)
        if m and int(m.group(1)) in changes:
            pid = int(m.group(1)); new = changes[pid]
            ln2, k = re.subn(r'op:"\d+%"', f'op:"{new}%"', ln)
            if k: n += 1; ln = ln2
        out.append(ln)
    path.write_text('\n'.join(out), encoding='utf-8')
    print(f"{path.name}: {n}개 크롭 조정")

if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
