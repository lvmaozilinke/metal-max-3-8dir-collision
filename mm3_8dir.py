# -*- coding: utf-8 -*-
"""
Metal Max 3 (NDS) 八方向移动 / 逐轴碰撞 修复工具
=================================================

把 rom/ 文件夹里的任意 Metal Max 3 ROM（日文原版 / 中文汉化版 / 其他语言版本）
转换成“八方向移动 + 逐轴碰撞”修复版，效果与发布的 版21 完全一致：

  * 斜向移动（每帧两次逐轴碰撞请求，斜向速度归一化为 0xB50）
  * 后三名队员跟随斜向移动时的行走动画与朝向与队长一致
  * 斜向/贴墙滑行时队列间距与原始四向版本一致（不抖动、不叠人）
  * 贴上下墙滑行时相机正常跟随
  * 乘车时随从保持自己的行走动画
  * 修复了原版汉化 ROM 的“全新启动黑屏 / 游戏中存档卡死”（字符串库被覆盖的问题）

用法：
  1) 把 .nds 放进 rom/ 文件夹（可以一次放多个）
  2) 双击 “一键转换_八方向.bat”
  3) 输出在 output/ 文件夹，文件名后缀 _八方向修复.nds

也支持命令行：
  python mm3_8dir.py                 # 处理 rom/ 下所有 .nds
  python mm3_8dir.py a.nds b.nds     # 指定文件
  python mm3_8dir.py --force         # 补丁点不匹配时也强行写入（不推荐）
  python mm3_8dir.py --out DIR       # 指定输出目录

原理：
  NDS 的 ARM9 区域（ROM 头 0x20/0x2C 指定的偏移与长度）被 DS 装载器原样加载到
  0x02000000，前 0x4000 字节是明文 stub，之后是自解压数据。本工具用 pack.py
  解码出完整的 ARM9 镜像，按补丁表逐处替换（每处都先校验原始字节），再按同样
  的格式重新压缩写回，ROM 的其它部分（文件系统、ARM7、叠加层等）一个字节都不动。
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pack
from mm3_patch_data import IMAGE_SIZE, PATCHES

OUT_SUFFIX = '_八方向修复'


# --------------------------------------------------------------------------
# ARM9 区域重建（与制作 版21 时使用的 packer/repack_img.py 相同）
# --------------------------------------------------------------------------
def compress_suffix(image, a, max_chain=512, lazy=True):
    S = image[a:]
    toks = pack._lz77_tokens(S[::-1], max_chain=max_chain, lazy=lazy)
    cons = pack._pack_tokens(toks)
    return cons, len(cons) + 9


def build_region(image, arm9_size, max_chain=512, lazy=True):
    """把镜像重新压进 arm9_size 字节的 ARM9 区域，自动选择最优的明文前缀长度 a。"""
    cand = None
    lo, hi = 0x4000, arm9_size
    while lo <= hi:
        mid = (lo + hi) // 2
        cons, C = compress_suffix(image, mid, max_chain, lazy)
        if mid + C <= arm9_size:
            cand = (mid, cons, C)
            lo = mid + 1
        else:
            hi = mid - 1
    if cand is None:
        raise ValueError('镜像压不进 ARM9 区域（可能不是受支持的版本）')
    a, cons, C = cand
    P = len(image) - a
    stored = cons[::-1] + b'\xFF' + struct.pack('<II', C | (pack.EXTRA << 24), P - C)
    assert len(stored) == C
    region = bytearray(b'\xFF' * arm9_size)
    region[:a] = image[:a]
    region[a:a + C] = stored
    return bytes(region), dict(a=a, C=C, slack=arm9_size - a - C)


# --------------------------------------------------------------------------
# 补丁检查 / 应用
# --------------------------------------------------------------------------
def check_patch_state(img):
    """返回 ('patched'|'pristine'|'mismatch', 详情)。"""
    already = 0
    mism = []
    for off, old, new in PATCHES:
        cur = img[off:off + len(old)]
        if cur == new:
            already += 1
        elif cur != old:
            mism.append((off, cur, old))
    if mism:
        return 'mismatch', mism
    if already == len(PATCHES):
        return 'patched', []
    return 'pristine', []


def apply_patch(img):
    out = bytearray(img)
    for off, old, new in PATCHES:
        out[off:off + len(new)] = new
    return bytes(out)


def convert_one(path, out_dir, force=False):
    name = os.path.basename(path)
    print('-' * 70)
    print('处理：', name)
    rom = open(path, 'rb').read()
    if len(rom) < 0x8000:
        print('  [跳过] 文件太小，不是 NDS ROM')
        return 'skip'
    if rom[0x0C:0x14] == b'\x00' * 8 and rom[0x00:0x0C] == b'\x00' * 12:
        print('  [跳过] 没有 NDS 头')
        return 'skip'
    try:
        off, size, reg = pack.rom_arm9_region(rom)
        img = pack.decode(reg)
    except Exception as e:
        print('  [跳过] 解析 ARM9 失败：', e)
        return 'skip'

    if len(img) != IMAGE_SIZE:
        print('  [跳过] ARM9 镜像长度 0x%X，期望 0x%X（不是本工具支持的 MM3 版本）'
              % (len(img), IMAGE_SIZE))
        return 'skip'

    state, detail = check_patch_state(img)
    if state == 'patched':
        print('  [跳过] 已经是修复版（补丁点与修复版完全一致）')
        return 'patched'
    if state == 'mismatch':
        print('  [警告] %d 处补丁点的原始字节与预期不同，这个 ROM 的代码布局和已知版本不一样：'
              % len(detail))
        for off, cur, old in detail[:8]:
            print('       +0x%06X  当前=%s  预期=%s'
                  % (off, cur.hex(), old.hex()))
        if len(detail) > 8:
            print('       ...（共 %d 处）' % len(detail))
        if not force:
            print('  [跳过] 为避免把 ROM 改坏，已跳过；确认要强行打补丁请加 --force')
            return 'mismatch'
        print('  [强行] 继续按补丁表写入（有把该 ROM 改坏的风险）')

    new_img = apply_patch(img)
    region, info = build_region(new_img, size)
    back = pack.decode(region)
    diffs = [i for i in range(len(new_img)) if back[i] != new_img[i]]
    if diffs:
        print('  [失败] 重新压缩后回读不一致，已中止（ROM 未写入）。前几处：%s'
              % [hex(x) for x in diffs[:5]])
        return 'error'
    if struct.unpack_from('<I', region, pack.DEST_FIELD_OFF)[0] != 0x02000000 + size:
        print('  [失败] 自解压目标地址校验失败，已中止（ROM 未写入）')
        return 'error'

    out = bytearray(rom)
    out[off:off + size] = region
    stem, ext = os.path.splitext(name)
    if stem.endswith(OUT_SUFFIX):
        stem = stem[:-len(OUT_SUFFIX)]
    out_path = os.path.join(out_dir, stem + OUT_SUFFIX + ext)
    if os.path.exists(out_path):
        os.remove(out_path)
    open(out_path, 'wb').write(bytes(out))
    print('  [完成] 输出：%s' % out_path)
    print('         明文前缀 a=0x%X，压缩块 C=0x%X，余量 %d 字节'
          % (info['a'], info['C'], info['slack']))
    return 'ok'


def collect_inputs(argv):
    files = [a for a in argv if not a.startswith('-')]
    if files:
        return [f for f in files if os.path.isfile(f)]
    rom_dir = os.path.join(HERE, 'rom')
    src = rom_dir if os.path.isdir(rom_dir) else HERE
    out = []
    for fn in sorted(os.listdir(src)):
        if fn.lower().endswith('.nds'):
            if OUT_SUFFIX in fn:
                continue
            out.append(os.path.join(src, fn))
    return out


def main(argv):
    force = '--force' in argv
    out_dir = os.path.join(HERE, 'output')
    if '--out' in argv:
        i = argv.index('--out')
        if i + 1 < len(argv):
            out_dir = os.path.abspath(argv[i + 1])
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    files = collect_inputs(argv)
    print('=' * 70)
    print(' Metal Max 3 八方向移动 / 逐轴碰撞 修复工具')
    print(' 输入：%d 个 ROM' % len(files))
    print(' 输出目录：%s' % out_dir)
    print(' 注意：本修复版只适合单机游玩，联机（通信）功能不可用；')
    print('       存档与原始/联机版通用，联机时请换用专门的联机版 ROM。')
    print('=' * 70)
    if not files:
        print('没有找到 .nds 文件。请把 ROM 放进 rom/ 文件夹后重试。')
        return 0

    stats = {}
    for f in files:
        try:
            r = convert_one(f, out_dir, force=force)
        except Exception as e:
            print('  [异常]', e)
            r = 'error'
        stats[r] = stats.get(r, 0) + 1

    print('=' * 70)
    print(' 汇总：成功 %d，已是修复版 %d，跳过 %d，补丁点不匹配 %d，失败 %d'
          % (stats.get('ok', 0), stats.get('patched', 0), stats.get('skip', 0),
             stats.get('mismatch', 0), stats.get('error', 0)))
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
