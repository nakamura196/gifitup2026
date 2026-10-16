# GIF IT UP 2026 — 再現可能なビルド

GIF IT UP 2026 に出す 3 本のアニメーション GIF を、元の資料から作り直すためのリポジトリです。

画像の生成に生成AIは使っていない。すべての画素は元の資料から来ている。プログラムは Claude Code の助けを借りて書いた。

作者: 中村 覚 (Satoru Nakamura, The University of Tokyo)

## 3 本の元資料

| 名前 | 作品 | 所蔵・URL | 利用条件 |
|---|---|---|---|
| yose | 歌川国芳「みかけはこはいがとんだいゝ人だ」 | 公益財団法人東京富士美術館 https://jpsearch.go.jp/item/tfam_art_db-9801 | CC0 |
| mushi | 栗本丹洲『千蟲譜』(国立国会図書館 pid 2576062, 画像 83) | https://jpsearch.go.jp/item/dignl-2576062 | パブリックドメイン (NDL) |
| globe | 白井通気『新訂萬國全圖』1852 (国立国会図書館 pid 2543045, 画像 4) | https://jpsearch.go.jp/item/dignl-2543045 | パブリックドメイン (NDL) |

元画像はこのリポジトリに入れていません。`fetch.py` が元のサイトから取り、sha256 を確かめます。

## 作り方

```
pip install -r requirements.txt     # ほかに ffmpeg と gifsicle (TOOLS.md)
zsh build.zsh                       # 取得 + 3 本の生成 + md5 の照合
zsh build.zsh yose                  # 1 本だけ (yose / mushi / globe)
```

出力は `build/<name>.gif`。末尾に `checksums.md5` との照合結果が出ます(3 本とも OK を確認済み、2 回)。

## 補足

- yose: 動くと隠れる部分(人の後ろ側)は、同じ絵の輪郭線を、版画のインクの色で描き足して補っています。
  質感は同じ人物の画素の写しです。補った箇所は `docs/yose_completion_overlay.png` に示します。
  切り抜きの形は `yose/user_masks/` (手で塗ったラベル) と、それを墨線に合わせて整えた `yose/work/masks_traced/` です
  (整える処理は `yose/trace.py`。履歴として置いてあり、ビルドでは実行しません)。
- mushi: 足した線は、画帳のインクの色で描いたひび割れ 1 本だけです。ほかはすべて元画像の画素です。
- globe: 地図を球に貼る処理だけで、画素の描き足しはありません(題字の朱印も元の地図の画素を切り出したものです)。
- 動きを決める式は変えていません。ファイルの場所だけを、各フォルダからの相対パスにしました。

## English (short)

Build repository for three animated GIFs submitted to GIF IT UP 2026, rebuilt from public-domain / CC0 sources
(Tokyo Fuji Art Museum, CC0; National Diet Library, public domain; links above).
No generative AI was used for images; every pixel comes from the source material. The code was written with the help of Claude Code.
`zsh build.zsh` downloads the sources (sha256-verified), builds the three GIFs into `build/` and compares their md5 with `checksums.md5`.
yose: hidden parts of the figures are completed with outline curves in the print's ink colour and texture copied from the same figures
(see `docs/yose_completion_overlay.png`). mushi: one crack line in the album's ink colour is the only addition.

## ライセンス / Licence

- コード (`*.py`, `*.zsh`, `*.sh`): MIT License (`LICENSE`)
- マスク画像・文書 (`yose/user_masks/`, `yose/work/masks_traced/`, `docs/`): CC BY 4.0
- 元の資料は各所蔵機関の条件に従います (上の表)。

Code: MIT (see `LICENSE`). Masks and documents: CC BY 4.0. Source items keep their own terms (CC0 / public domain).
