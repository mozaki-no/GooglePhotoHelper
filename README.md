# Google Photo Helper

GoogleフォトのTakeoutアーカイブから  
**Exifや作成日を復元し、年別フォルダに仕分けて出力する**  
高機能自動整理ツールです。

---

## 特長

- Google Takeoutからダウンロードしたフォルダを**そのまま指定するだけ**
- 画像/動画の「本来の撮影日時」をEXIF・ファイル更新日時ともに復元
- 年別フォルダ（例: `2022/`）で自動分類
- 付随するJSONメタデータから柔軟に日時取得
- 拡張子違いや`(1)`付きリネーム、`.supplemental-metadata`省略なども賢くマッチ
- ログ出力・インジケータ付きの**わかりやすい進行表示**
- エラーや「日付不明」ファイルは専用フォルダに隔離
- Python標準＆ExifToolのみで完結

---

## 必要なもの

- Python 3.8 以上
- pip install 必須ライブラリ  
pip install tqdm pillow ffmpeg-python
- [ExifTool](https://exiftool.org/)（**exiftool.exe**を`main.py`と同じディレクトリに置く）
- ダウンロードしたファイルを「**exiftool.exe**」にリネームして配置

---

## 使い方

### 1. **GoogleフォトのTakeoutをダウンロード**
- [Google Takeout](https://takeout.google.com/)で「Googleフォト」を選択し、PCにダウンロード
- ダウンロードしたフォルダ（`Takeout/Google フォト/...`など）を**任意の場所にまとめる**

### 2. **Python環境のセットアップ**
- 必要なライブラリをインストール（コマンドプロンプトで実行）
pip install tqdm pillow ffmpeg-python


### 3. **ExifToolの準備**
- https://exiftool.org/ から**Windows版ExifTool**をダウンロード
- `exiftool(-k).exe`を`exiftool.exe`にリネームして、スクリプトと同じ場所へ置く

### 4. **GooglePhotoHelperの起動**
- `main.py`を実行
- ダブルクリックでも、コマンドプロンプトでもOK
- 実行すると**入力フォルダと出力フォルダを対話式で聞かれます**
  - 何も入力せずEnterなら、デフォルト（Downloads→Documents/GooglePhotoHelper）で動作

### 5. **処理完了後**
- 成功、日付不明、スキップ、エラー数を集計して表示
- 詳細なログは**google_photo_helper.log**に記録されます

---

## デフォルトの入出力場所

- **入力（TARGET_DIR）**  
`C:/Users/あなたのユーザー名/Downloads`
- **出力（OUTPUT_DIR）**  
`C:/Users/あなたのユーザー名/Documents/GooglePhotoHelper`
- **日付不明ファイル**  
出力フォルダ内 `date_unknown/` サブフォルダ

---

## よくある質問

**Q. どの画像/動画形式に対応？**  
A. jpg, jpeg, png, gif, webp, heic, arw, dng, nef, mov, mp4, m4v, rw2 など多数

**Q. 日付不明ファイルはどうなる？**  
A. どちらのメタデータからも撮影日が取得できない場合、`date_unknown/`サブフォルダへ格納されます。

**Q. どこにログが残りますか？**  
A. `google_photo_helper.log`にすべての詳細ログが記録されます。

**Q. ExifToolの場所やファイル名が違うと動きますか？**  
A. スクリプトと同じディレクトリに「exiftool.exe」として置く必要があります。

**Q. スクリプト実行時、フォルダが無ければ自動作成されますか？**  
A. 入力フォルダは存在確認あり、出力フォルダは**自動で作成**されます。

---

## 注意・免責

- 本ツールの利用は自己責任でお願いします。
- 元ファイルは自動で移動されます。**必ずバックアップを取った上でご利用ください。**
- 大量ファイルを一気に処理する場合はPCの空き容量・動作時間にご注意ください。


