import os
import json
import time
import shutil
import fnmatch
import subprocess
from datetime import datetime
from PIL import Image
import piexif
import pytz
import sys
import re

# 設定
target_file_dir = "C:/Users/baris/Desktop/photo_work/done/ALL_PHOTOS/date-unknown"
json_dir = "C:/Users/baris/Desktop/photo_work/unzip/ALL/Takeout"
output_dir = "C:/Users/baris/Desktop/photo_work/date_restore"
unmatched_log_path = "unmatched_title_log.txt"  # ← 追加：title不一致ログファイル

image_exts = {".jpg", ".jpeg", ".png"}
video_exts = {".mp4", ".mov", ".avi", ".mkv"}

os.makedirs(output_dir, exist_ok=True)

# JSONファイルを再帰的に取得
json_map = {}
for root, _, files in os.walk(json_dir):
    for file in files:
        if file.endswith(".json"):
            json_map[file] = os.path.join(root, file)

def convert_to_dms(coord):
    degrees = int(abs(coord))
    minutes = int((abs(coord) - degrees) * 60)
    seconds = float((abs(coord) - degrees - minutes / 60) * 3600)
    return [(degrees, 1), (minutes, 1), (int(seconds * 100), 100)]

def set_file_timestamp(path, dt):
    ts = time.mktime(dt.timetuple())
    os.utime(path, (ts, ts))

def update_video_metadata(filepath, dt):
    dt_str = dt.strftime("%Y-%m-%dT%H:%M:%S+09:00")
    temp_file = filepath + ".temp.mp4"

    if sys.platform == "win32":
        command = f'ffmpeg -y -i "{filepath}" -metadata creation_time="{dt_str}" -codec copy "{temp_file}"'
        result = subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        command = [
            "ffmpeg", "-y",
            "-i", filepath,
            "-metadata", f"creation_time={dt_str}",
            "-codec", "copy",
            temp_file
        ]
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if result.returncode == 0:
        os.replace(temp_file, filepath)
        print(f"🎥 動画更新: {os.path.basename(filepath)}")
    else:
        print(f"⚠️ ffmpeg失敗: {filepath}")

# title不一致ログ初期化
with open(unmatched_log_path, "w", encoding="utf-8") as log_file:
    log_file.write("title不一致ファイル一覧:\n")

# メイン処理
for file in os.listdir(target_file_dir):
    file_path = os.path.join(target_file_dir, file)
    if not os.path.isfile(file_path):
        continue

    name, ext = os.path.splitext(file)
    ext = ext.lower()

    # 正規表現で安全に括弧などを扱うためにエスケープ
    escaped_file = re.escape(file)
    pattern = re.compile(rf"^{escaped_file}.*\.json$", re.IGNORECASE)

    matched_json = None
    for json_filename, json_path in json_map.items():
        if pattern.match(json_filename):
            matched_json = json_path
            break

    if not matched_json:
        print(f"❌ JSON見つからず: {file}")
        continue

    try:
        with open(matched_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        # title チェック（拡張子の大文字小文字無視）
        json_title = data.get("title", "").strip()
        if json_title.lower() != file.lower():
            print(f"⚠️ title不一致: JSONのtitle='{json_title}' / ファイル='{file}' → スキップ")
            with open(unmatched_log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"{file} → JSON title: {json_title}\n")
            continue

        time_str = data.get("photoTakenTime", {}).get("formatted")
        if not time_str:
            print(f"⚠️ 撮影日時なし: {file}")
            continue

        dt_utc = datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S %Z")
        dt_utc = pytz.utc.localize(dt_utc)
        dt_jst = dt_utc.astimezone(pytz.timezone("Asia/Tokyo"))

        updated = False

        if ext in image_exts:
            if ext in [".jpg", ".jpeg"]:
                lat = data.get("geoData", {}).get("latitude", 0.0)
                lon = data.get("geoData", {}).get("longitude", 0.0)
                alt = data.get("geoData", {}).get("altitude", 0.0)

                img = Image.open(file_path)
                exif_dict = piexif.load(img.info.get("exif", b""))
                dt_str = dt_jst.strftime("%Y:%m:%d %H:%M:%S")

                exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = dt_str
                exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = dt_str

                gps_ifd = {}
                gps_ifd[piexif.GPSIFD.GPSLatitudeRef] = b'N' if lat >= 0 else b'S'
                gps_ifd[piexif.GPSIFD.GPSLatitude] = convert_to_dms(lat)
                gps_ifd[piexif.GPSIFD.GPSLongitudeRef] = b'E' if lon >= 0 else b'W'
                gps_ifd[piexif.GPSIFD.GPSLongitude] = convert_to_dms(lon)
                gps_ifd[piexif.GPSIFD.GPSAltitudeRef] = 0 if alt >= 0 else 1
                gps_ifd[piexif.GPSIFD.GPSAltitude] = (int(abs(alt * 100)), 100)
                exif_dict["GPS"] = gps_ifd

                img.save(file_path, "jpeg", exif=piexif.dump(exif_dict))
                print(f"🖼 EXIF更新: {file}")
                updated = True

            set_file_timestamp(file_path, dt_jst)
            updated = True

        elif ext in video_exts:
            set_file_timestamp(file_path, dt_jst)
            update_video_metadata(file_path, dt_jst)
            updated = True

        else:
            set_file_timestamp(file_path, dt_jst)
            updated = True

        if updated:
            dest_path = os.path.join(output_dir, file)
            shutil.move(file_path, dest_path)  # コピー→移動に変更
            print(f"✅ 移動完了: {file}")

    except Exception as e:
        print(f"❌ エラー（{file}）: {e}")