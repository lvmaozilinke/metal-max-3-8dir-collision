# Metal Max 3 · 8-Direction Movement + Per-Axis Collision Patch

**One-click Windows tool** that converts any Metal Max 3 NDS ROM (Japanese original,
Chinese translation, English/other fan translations) into a build with **8-direction
movement and per-axis wall collision**. No ROM is included — you need your own copy.

> ⚠️ **Known limitation**: multiplayer / link-play does **not** work in this build.
> Use the original (or a dedicated link-play) build for multiplayer; `.sav` saves are
> interchangeable between the two.

把 **任意语言版本的 Metal Max 3 NDS ROM**（日文原版、中文汉化版、英文/其他语言改版）
一键转换成“八方向移动 + 逐轴碰撞”修复版。

生成结果与已发布的 **版21** 完全一致（同样的二进制、同样的 SHA-256）。

---

## ⚠️ 已知限制：联机功能不可用

**这个修复版只适合单机游玩，联机（通信）功能会失效。**
想联机请使用专门的联机版 ROM / 原版，不要用本工具转换出来的 ROM。

- **原因**：八方向补丁的代码（约 686 字节）放在 ARM9 镜像的 `0x0200ABE0–0x0200B000`
  区域。这段代码平时单机流程完全不执行（启动、走路、菜单、战斗都不经过），
  所以曾经被判断为“死代码区”；但实际上它是联机/通信功能会调用的一段活代码
  （镜像里有 90 处分支跳入、5 处指针指向它），补丁覆盖了它 686/1056 字节，
  因此联机时相关逻辑出错。
- **单机不受影响**：启动、移动、碰撞、动画、相机、乘车、存档/读档均已实测正常。
- **存档通用**：存档（`.sav`）在“八方向修复版”和原版/联机版之间是通用的——
  在修复版里存的档可以拿到联机版继续玩，反之亦然。所以常见用法是：
  **单人用修复版，联机时换成联机版（用同一个 .sav）。**

---

## 一、怎么用（Windows，双击即可）

1. 安装 **Python 3.8+**（安装时勾选 `Add Python to PATH`）
   <https://www.python.org/downloads/>
2. 把要转换的 `.nds` 放进 **`rom/`** 文件夹（可以一次放多个）
3. 双击 **`一键转换_八方向.bat`**
4. 转换好的 ROM 在 **`output/`** 文件夹，文件名后缀 `_八方向修复.nds`

控制台会显示每个 ROM 的处理结果：

| 结果 | 含义 |
|---|---|
| `[完成]` | 转换成功 |
| `[跳过] 已经是修复版` | 这个 ROM 之前已经转过，不会重复处理 |
| `[跳过] 补丁点的原始字节与预期不同` | 该 ROM 的代码布局和已知版本不同（不是受支持的 MM3 版本），为避免改坏会跳过 |
| `[失败]` | 重新压缩回读校验失败（不会写出半成品） |

### 命令行用法（可选）

```bat
python mm3_8dir.py                     :: 处理 rom/ 下所有 .nds
python mm3_8dir.py a.nds b.nds         :: 只处理指定文件
python mm3_8dir.py --out D:\out        :: 指定输出目录
python mm3_8dir.py --force             :: 补丁点不匹配也强行写入（不推荐）
```

---

## 二、这个修复版都改了什么

1. **八方向移动 + 逐轴碰撞**
   斜向移动时每帧向引擎发两次“逐轴移动请求”，每个轴单独做碰撞判定，
   所以斜着走也能被墙挡住，不会穿墙；斜向速度用 `0xB50`（≈ 4096/√2）归一化，
   不会比直走更快。贴墙时只保留能走的那一轴，滑行手感与原版一致。

2. **后三名队员的斜向行走动画与朝向**
   斜向时引擎原本只会给队长播放行走动画，三名随从会站着不动或朝向错误。
   修复版在精灵动画更新函数里把队长的行走位、可见动画帧同步给三名随从
   （乘车时自动跳过，随从保持自己的动画）。

3. **队列间距 / 不抖动**
   斜向时引擎每帧会追加两条轨迹记录，修复版按“帧计数差为 2 就合并成一条”的方式
   折算，使随从间距与原始四向版本一致（不压缩、不抖动、不叠人）。

4. **贴上下墙滑行时相机跟随**
   引擎只在“最后一次移动请求成功”时才推进相机；修复版会根据上一帧哪个轴被挡住，
   自动决定两次请求的先后顺序，保证成功的那次收尾。

5. **修复汉化版“全新启动黑屏 / 游戏中存档卡死”**
   早期版本把补丁写在 0x020122DC 附近，覆盖了宽字符字符串比较/搜索库，
   导致新开档黑屏、存档卡死。现在补丁代码集中放在 0x0200ABE0–0x0200B000，
   不再动任何字符串库（这段区域只被联机/通信功能调用，代价见上面的“已知限制”）。

---

## 三、原理 / 安全性

- NDS 的 ARM9 区域（ROM 头 `0x20` 偏移、`0x2C` 长度）会被装载器原样加载到
  `0x02000000`；前 `0x4000` 字节是明文自解压 stub，之后是压缩数据。
- 本工具用 `pack.py` 解码出完整 ARM9 镜像 → 按补丁表逐处替换
  （**每一处都先校验原始字节**）→ 用同样的格式重新压缩写回。
- 只改动 ARM9 区域，ROM 的其它部分（文件系统、ARM7、叠加层、头部）一个字节都不动。
- 写入前会做“解压回读一致性”校验，校验不过不会输出文件。

补丁数据在 `mm3_patch_data.py`，共 9 段、680 字节，全部集中在：
移动/队伍映射代码、精灵动画更新、轨迹追加函数与 0x0200ABE0–0x0200B000 区域。

---

## 四、文件说明

| 文件 | 作用 |
|---|---|
| `一键转换_八方向.bat` | 双击入口（自动找 Python） |
| `mm3_8dir.py` | 转换主程序（解码 / 校验 / 打补丁 / 重压缩） |
| `mm3_patch_data.py` | 补丁表（偏移 + 原始字节 + 修复后字节） |
| `pack.py` | Metal Max 3 的 ARM9 自解压格式编解码器 |
| `rom/` | 放待转换的 `.nds` |
| `output/` | 转换结果 |

---

## 五、已验证

| ROM | 结果 |
|---|---|
| 中文汉化版（`mm3_test.nds`，原始未改） | 转换后与 版21 **逐字节相同**（SHA-256 `3e32e12f…`） |
| 中文汉化版 版21 | 识别为“已经是修复版”，跳过 |
| 英文改版 `Metal Max 3 (Japan) [T-En by Metal Dreamers v1.0]` | 转换成功，全新启动画面与未改版逐帧一致 |

游戏内实测（中文版）：斜向/正向行走动画正常、四人朝向一致、不倒着走、
贴墙滑行相机跟随、乘车时随从动画正常、存档/读档正常、不穿墙；
队长乘车（或中途上下车）时，车下跟随的队员行走动画正常播放、速度正常、停下即站立；
用本版新建的即时存档（模拟器状态）存取正常（旧版即时存档里带旧代码，需重存）。

**未包含 / 已知失效**：联机（通信）功能——原因与对策见文首“已知限制”；
存档与原版/联机版通用。

---

## English (short)

`一键转换_八方向.bat` (double-click) converts every `.nds` in `rom/` into the
8-direction / per-axis-collision fixed build; results go to `output/`.
Requires Python 3.8+. Only the ARM9 area of the ROM is rewritten (verified
byte-for-byte against the released build 版21). Works on the Japanese original,
the Chinese translation and the English fan translation.

**Known limitation: multiplayer / link-play does not work in this build.**
The 8-direction patch code occupies `0x0200ABE0–0x0200B000`, a module that is
never used in single-player but *is* used by the link/wireless feature, so it
breaks when linking. Single-player (movement, collision, animation, camera,
vehicles, save/load) is unaffected. Save files (`.sav`) are interchangeable
between this build and the original / dedicated link-play build — use the
8-direction build for solo play and switch to the link-play build for
multiplayer with the same save.
