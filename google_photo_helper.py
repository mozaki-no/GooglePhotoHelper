# 目的：Google Photoのアーカイブからexifや作成日を復元して年別にフォルダ分けして出力する

# 使い方
# 1.Goohle Photoの写真をGoogle Takeoutで出力
# 2.Takeoutフォルダを一つにまとめる
# 3.設定部分部分を任意のフォルダに設定する
# 4.Pythonや必要なライブラリをインストールする
#   pip install tqdm
# 5.exifTool.exeを用意する(exifTool.exeにリネームしてこのスクリプトと同じ場所に置くか、好きな場所においてPATHを通す)
#   https://exiftool.org/
# 6.実行する
#   python google_photo_helper.py

import os
import shutil
import json
import re
import subprocess
from datetime import datetime, timezone, timedelta
from tqdm import tqdm

# ---------- 設定 ----------
TARGET_DIR = "C:/Users/baris/Desktop/photo_work/unzip/ALL"
OUTPUT_DIR = "C:/Users/baris/Desktop/photo_work/done"
UNKNOWN_DIR = os.path.join(OUTPUT_DIR, "date_unknown")
DAYS_TO_MOVE_FROM_UNKNOWN = 30
SUPPORTED_EXTENSIONS = {
    ".arw", ".dng", ".gif", ".heic", ".jpeg", ".jpg",
    ".m4v", ".mov", ".mp4", ".nef", ".png", ".rw2", ".webp"
}
TIMEZONE = timezone(timedelta(hours=9))  # JST
EXIFTOOL_PATH = os.path.join(os.path.dirname(__file__), "exiftool.exe")

# ---------- 初期チェック ----------
def check_exiftool():
    try:
        result = subprocess.run([EXIFTOOL_PATH, "-ver"], capture_output=True, text=True, encoding="utf-8")
        if result.returncode != 0:
            raise Exception(result.stderr)
    except Exception as e:
        print("ExifToolが使用できません:", e)
        exit(1)

# ---------- ユーティリティ関数 ----------
def safe_filename(path):
    return os.path.basename(path)

def parse_exif_date(date_str):
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(date_str[:19], fmt).replace(tzinfo=TIMEZONE)
        except Exception as e:
            continue
    return None

def extract_metadata(file_path):
    try:
        norm_path = os.path.abspath(os.path.normpath(file_path))

        result = subprocess.run(
            [EXIFTOOL_PATH, "-json", "-charset", "filename=UTF8", norm_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False
        )
        if result.returncode != 0:
            raise Exception(result.stderr.decode("utf-8", errors="replace"))
        output = result.stdout.decode("utf-8", errors="replace")
        data = json.loads(output)
        return data[0] if data else {}
    except Exception as e:
        print(f"[WARN] メタデータ取得失敗 ({file_path}): {e}")
        return {}

def get_creation_date(json_data, file_path):
    try:
        ts_raw = json_data.get("photoTakenTime", {}).get("timestamp")
        if ts_raw:
            ts = int(ts_raw)
            if ts > 1e12:
                ts = ts // 1000
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(TIMEZONE)
            current_year = datetime.now().year
            if 2000 <= dt.year <= current_year + 1:
                return dt
    except Exception as e:
        print(f"[WARN] JSON日時変換失敗 ({file_path}): {e}")

    # JSONから取得できなかった場合はExifから取得
    try:
        metadata = extract_metadata(file_path)
        print(f"[DEBUG] Exif取得成功: {file_path} -> {metadata}")
        for tag in ["EXIF:DateTimeOriginal", "QuickTime:CreateDate", "CreationDate", "FileModifyDate"]:
            date_str = metadata.get(tag)
            if date_str:
                dt = parse_exif_date(date_str)
                if dt:
                    return dt
    except Exception as e:
        print(f"[WARN] Exif日時取得失敗 ({file_path}): {e}")

    return None

def ensure_unique_path(dst_path):
    base, ext = os.path.splitext(dst_path)
    count = 1
    while os.path.exists(dst_path):
        dst_path = f"{base}_{count}{ext}"
        count += 1
    return dst_path

def move_file_safely(src, dst):
    dst = ensure_unique_path(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
    return dst

def normalize_base_name(name):
    return re.sub(r"-編集済み$", "", name)

def find_json_candidates(file_path):
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)

    name = normalize_base_name(name)

    media_match = re.match(r"^(.*?)(\((\d+)\))?$", name)
    if media_match:
        base_name = media_match.group(1)
        index = media_match.group(3)
    else:
        base_name = name
        index = None

    candidates = []
    for jf in os.listdir(directory):
        if not jf.lower().endswith(".json"):
            continue

        json_patterns = [
            rf"^{re.escape(base_name)}{re.escape(ext)}(\..*?)?(\(\d+\))?\.json$",
            rf"^{re.escape(base_name)}{re.escape(ext)}\.json$",
            rf"^{re.escape(base_name)}{re.escape(ext)}\.json$",
            rf"^{re.escape(base_name)}(\..*?)?(\(\d+\))?\.json$",
            rf"^{re.escape(base_name)}\.json$"
        ]

        if ext in [".mp4", ".mov", ".m4v"]:
            json_patterns.extend([
                rf"^{re.escape(base_name)}(\..*?)?(\(\d+\))?\.json$",
                *[
                    rf"^{re.escape(base_name)}{re.escape(alt_ext)}(\..*?)?(\(\d+\))?\.json$"
                    for alt_ext in [".heic", ".jpg", ".jpeg"]
                ],
                rf"^{re.escape(base_name)}\.(heic|jpg|jpeg)(\..*?)?(\(\d+\))?\.json$"
            ])

        for pattern in json_patterns:
            if re.match(pattern, jf, re.IGNORECASE):
                candidates.append(os.path.join(directory, jf))
                break

    return candidates

def load_json_data(json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def get_relative_path(path, base):
    return os.path.relpath(path, base)

def move_to_unknown_with_structure(file_path):
    rel_path = get_relative_path(file_path, TARGET_DIR)
    dst_path = os.path.join(UNKNOWN_DIR, rel_path)
    move_file_safely(file_path, dst_path)

def update_file_timestamp(file_path, dt):
    ts = dt.timestamp()
    os.utime(file_path, (ts, ts))

def extract_metadata(file_path):
    try:
        result = subprocess.run(
            [EXIFTOOL_PATH, "-json", "-charset", "filename=UTF8", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if result.returncode != 0:
            raise Exception(result.stderr.decode("utf-8", errors="replace"))
        output = result.stdout.decode("utf-8", errors="replace")
        data = json.loads(output)
        return data[0] if data else {}
    except Exception as e:
        print(f"[WARN] メタデータ取得失敗 ({file_path}): {e}")
        return {}


def move_old_unknown_files():
    now = datetime.now(tz=TIMEZONE)
    cutoff = now - timedelta(days=DAYS_TO_MOVE_FROM_UNKNOWN)

    all_files = []
    for root, _, files in os.walk(UNKNOWN_DIR):
        for f in files:
            all_files.append(os.path.join(root, f))

    for file_path in tqdm(all_files, desc="古い未分類ファイルを移動中", unit="ファイル", mininterval=0.1):
        try:
            should_move = False

            mtime = datetime.fromtimestamp(os.path.getmtime(file_path), tz=TIMEZONE)
            if mtime < cutoff:
                should_move = True

            metadata = extract_metadata(file_path)

            for tag in ["EXIF:DateTimeOriginal", "QuickTime:CreateDate", "CreationDate"]:
                date_str = metadata.get(tag)
                if date_str:
                    try:
                        dt = datetime.strptime(date_str[:19], "%Y:%m:%d %H:%M:%S").replace(tzinfo=TIMEZONE)
                        if dt < cutoff:
                            should_move = True
                            break
                    except:
                        continue

            if should_move:
                year_folder = os.path.join(OUTPUT_DIR, str(mtime.year))
                rel_path = os.path.relpath(file_path, UNKNOWN_DIR)
                dest_path = os.path.join(year_folder, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.move(file_path, dest_path)

        except Exception as e:
            print(f"[WARN] date_unknownファイルの移動失敗 {file_path}: {e}")

def process_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        print(f" {file_path} は除外対象です")
        return

    json_candidates = find_json_candidates(file_path)
    metadata = {}

    for jc in json_candidates:
        metadata = load_json_data(jc)
        if metadata:
            break

    taken_time = get_creation_date(metadata, file_path)

    if not taken_time:
        move_to_unknown_with_structure(file_path)
        return

    if ext in [".mp4", ".mov", ".m4v"] and metadata.get("photoTakenTime"):
        update_file_timestamp(file_path, taken_time)

    year_folder = os.path.join(OUTPUT_DIR, str(taken_time.year))
    dest_filename = os.path.basename(file_path)
    new_file_path = move_file_safely(file_path, os.path.join(year_folder, dest_filename))

    try:
        ts_str = taken_time.strftime("%Y:%m:%d %H:%M:%S")
        subprocess.run(
            [EXIFTOOL_PATH, f"-AllDates={ts_str}", "-overwrite_original", new_file_path],
            check=True, capture_output=True, text=True, encoding="utf-8"
        )
    except Exception as e:
        print(f"Exif 書き込みエラー: {file_path} -> {e}")

def main():
    check_exiftool()
    files = []
    for root, dirs, filenames in os.walk(TARGET_DIR):
        for f in filenames:
            if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS:
                files.append(os.path.join(root, f))

    for f in tqdm(files, desc="処理中", unit="ファイル", mininterval=0.1):
        try:
            process_file(f)
        except Exception as e:
            print(f"処理失敗: {f} -> {e}")
            move_to_unknown_with_structure(f)

    move_old_unknown_files()

if __name__ == "__main__":
    main()
