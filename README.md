# GIF IT UP 2026 — reproducible build

[English](#english) | [日本語](#日本語)

## English

This repository rebuilds, bit for bit, the three animated GIFs that Satoru Nakamura (The University of Tokyo) submitted to [GIF IT UP 2026](https://gifitup.net/).
All three start from openly licensed items found through [Japan Search](https://jpsearch.go.jp/).
The images themselves are not stored here: the scripts download them from the holding institutions and check their sha256.

### The three GIFs

| folder | title | source item | licence |
|---|---|---|---|
| `yose` | *He looks fierce, but he is really nice* | Utagawa Kuniyoshi, "Mikake wa kowai ga tonda ii hito da" (c. 1847), Tokyo Fuji Art Museum — https://jpsearch.go.jp/item/tfam_art_db-9801 | CC0 |
| `mushi` | *The page that molts* (Science category) | Kurimoto Tanshū, *Senchūfu*, National Diet Library (pid 2576062, image 83) — https://jpsearch.go.jp/item/dignl-2576062 | Public domain |
| `globe` | *Where on Earth is Japan?* | *Shintei bankoku zenzu* (cover title *Kaisei bankoku yochi zenzu*), 1852, National Diet Library (pid 2543045, image 4) — https://jpsearch.go.jp/item/dignl-2543045 | Public domain |

The idea behind all three: each source already hides a trick or a wonder in its own design, and the motion reveals it.

- **yose** — a face made entirely of people (*yose-e*). The face yawns; its jaw, a sleeping man, slides out into the face's own hand, which turns out to be two more men who bounce him back into place.
- **mushi** — an Edo-period insect album whose note describes how a cicada leaves its skin. The drawn nymph does exactly what the note says.
- **globe** — a Japanese world map that shows the round Earth as two flat circles. The circles close into a globe, spin, stop on Japan, and unroll again.

### What was added to the source, and what was not

Every pixel in the three GIFs comes from the source item. Nothing was generated, inpainted or upscaled by AI.

- **yose**: when the figures move, parts that the print hid behind other figures become visible. These were closed with outline curves in the print's own ink colour and filled with texture copied from the same figure (the falling man's head, back, arm and hips; the back of the lower hand man; the nose man's red loincloth, made by stretching the folds of the print's own red cloth). Every completed area is marked in [`docs/yose_completion_overlay.png`](docs/yose_completion_overlay.png). No face was added: the falling man is drawn from behind.
- **mushi**: the only added line is the thin crack on the nymph's back, drawn in the album's ink colour. The pale, freshly moulted cicada is the same drawing, lightened.
- **globe**: the map's pixels are wrapped onto a sphere with ordinary image warping. The close-up on Japan uses a higher-resolution IIIF image of the same item. The red seal is cut out of the map's own title.

### How AI was used

The scripts were written and run with Claude Code (Anthropic), an AI coding assistant: cutting out the figures (masks), closing hidden outlines, the transforms and timing of the motion, and GIF encoding.
No generative image AI was used.
The author chose the works and the gags, and reviewed and corrected every step.
The yose figure masks in `yose/user_masks/` were painted by hand by the author on top of the script's first proposal.

### Build

Requirements: Python 3 with the packages in `requirements.txt`, plus `ffmpeg` and `gifsicle` (exact versions in [`TOOLS.md`](TOOLS.md)).

```
pip install -r requirements.txt
zsh build.zsh            # download sources, build all three, compare md5
zsh build.zsh yose       # build one (yose / mushi / globe)
```

The GIFs are written to `build/<name>.gif`, and their md5 are compared with `checksums.md5`.
A clean build matched all three, twice, with the versions in `TOOLS.md`. Other library versions may produce a GIF that looks the same but differs in bytes.

### Layout

- `build.zsh` — runs everything; `checksums.md5` — expected md5 of the three GIFs
- `<name>/fetch.py` — downloads the source image and checks its sha256
- `yose/` — `complete.py` (completion of hidden parts), `build_v4.py` (animation), `user_masks/` and `work/masks_traced/` (figure masks), `trace.py` (how the masks were snapped to the ink lines; kept for the record, not run by the build)
- `mushi/src/`, `globe/src/` — animation and encoding scripts
- `docs/notes/gifitup2026.md` — lab notebook (Japanese): decisions, rejected ideas, lessons

### Licence

Code (`*.py`, `*.zsh`, `*.sh`): MIT (see [`LICENSE`](LICENSE)).
Masks and documents: CC BY 4.0.
The source items keep their own terms (CC0 / public domain).
The submitted GIFs are released by GIF IT UP under CC BY 4.0.

## 日本語

GIF IT UP 2026 に出す 3 本のアニメーション GIF を、元の資料から作り直すためのリポジトリです。

画像の生成に生成AIは使っていない。すべての画素は元の資料から来ている。プログラムは Claude Code の助けを借りて書いた。

作者: 中村 覚 (Satoru Nakamura, The University of Tokyo)

### 3 本の元資料

| 名前 | 作品 | 所蔵・URL | 利用条件 |
|---|---|---|---|
| yose | 歌川国芳「みかけはこはいがとんだいゝ人だ」 | 公益財団法人東京富士美術館 https://jpsearch.go.jp/item/tfam_art_db-9801 | CC0 |
| mushi | 栗本丹洲『千蟲譜』(国立国会図書館 pid 2576062, 画像 83) | https://jpsearch.go.jp/item/dignl-2576062 | パブリックドメイン (NDL) |
| globe | 白井通気『新訂萬國全圖』1852 (国立国会図書館 pid 2543045, 画像 4) | https://jpsearch.go.jp/item/dignl-2543045 | パブリックドメイン (NDL) |

元画像はこのリポジトリに入れていません。`fetch.py` が元のサイトから取り、sha256 を確かめます。

### 作り方

```
pip install -r requirements.txt     # ほかに ffmpeg と gifsicle (TOOLS.md)
zsh build.zsh                       # 取得 + 3 本の生成 + md5 の照合
zsh build.zsh yose                  # 1 本だけ (yose / mushi / globe)
```

出力は `build/<name>.gif`。末尾に `checksums.md5` との照合結果が出ます(3 本とも OK を確認済み、2 回)。

### 補足

- yose: 動くと隠れる部分(人の後ろ側)は、同じ絵の輪郭線を、版画のインクの色で描き足して補っています。
  質感は同じ人物の画素の写しです。補った箇所は `docs/yose_completion_overlay.png` に示します。
  切り抜きの形は `yose/user_masks/` (手で塗ったラベル) と、それを墨線に合わせて整えた `yose/work/masks_traced/` です
  (整える処理は `yose/trace.py`。履歴として置いてあり、ビルドでは実行しません)。
- mushi: 足した線は、画帳のインクの色で描いたひび割れ 1 本だけです。ほかはすべて元画像の画素です。
- globe: 地図を球に貼る処理だけで、画素の描き足しはありません(題字の朱印も元の地図の画素を切り出したものです)。
- 動きを決める式は変えていません。ファイルの場所だけを、各フォルダからの相対パスにしました。

### ライセンス

- コード (`*.py`, `*.zsh`, `*.sh`): MIT License (`LICENSE`)
- マスク画像・文書 (`yose/user_masks/`, `yose/work/masks_traced/`, `docs/`): CC BY 4.0
- 元の資料は各所蔵機関の条件に従います (上の表)。
