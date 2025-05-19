import os
import shutil
import json
import re
import subprocess
from datetime import datetime, timezone, timedelta
from PIL import Image, ExifTags
import ffmpeg
import logging

# ---------- 設定 ----------
USER_HOME = os.path.expanduser("~")
TARGET_DIR = os.path.join(USER_HOME, "Downloads")
OUTPUT_DIR = os.path.join(USER_HOME, "Documents", "GooglePhotoHelper")
UNKNOWN_DIR = os.path.join(OUTPUT_DIR, "date_unknown")
SUPPORTED_EXTENSIONS = {
    ".arw", ".dng", ".gif", ".heic", ".jpeg", ".jpg",
    ".m4v", ".mov", ".mp4", ".nef", ".png", ".rw2", ".webp"
}
TIMEZONE = timezone(timedelta(hours=9))  # JST
EXIFTOOL_PATH = os.path.join(os.path.dirname(__file__), "exiftool.exe")

# ---------- 初期チェック ----------
def check_exiftool():
    try:
        result = subprocess.run([EXIFTOOL_PATH, "-ver"], capture_output=True)
        if result.returncode != 0:
            raise Exception(result.stderr)
    except Exception as e:
        logging.error("ExifToolが使用できません: %s", e)
        exit(1)

# ---------- 高速化用キャッシュ ----------
json_cache = {}
def get_cached_json_files(directory):
    if directory not in json_cache:
        try:
            json_files = [
                os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith(".json")
            ]
            json_cache[directory] = json_files
        except Exception as e:
            logging.warning("JSONキャッシュ取得失敗 (%s): %s", directory, e)
            json_cache[directory] = []
    return json_cache[directory]

# ---------- ユーティリティ関数 ----------
def run_exiftool_with_fallback(cmd):
    # 必ずバイナリ受信。decodeはしない（必要なら個別で）
    result = subprocess.run(
        cmd,
        check=True,
        capture_output=True
    )
    return result

def collect_files(root_dir, extensions):
    files = []
    for root, _, filenames in os.walk(root_dir):
        valid_files = [os.path.join(root, f) for f in filenames if os.path.splitext(f)[1].lower() in extensions]
        files.extend(valid_files)
    return files

def safe_filename(path):
    return os.path.basename(path)

def parse_exif_date(date_str):
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(date_str[:19], fmt).replace(tzinfo=TIMEZONE)
        except Exception:
            continue
    return None

def extract_metadata(file_path):
    metadata = {}
    try:
        # 画像ファイルのEXIF情報を取得
        if file_path.lower().endswith((".jpg", ".jpeg", ".png", ".heic")):
            try:
                image = Image.open(file_path)
                exif_data = image._getexif()
                if exif_data:
                    for tag, value in exif_data.items():
                        tag_name = ExifTags.TAGS.get(tag, tag)
                        metadata[tag_name] = value
                return metadata
            except Exception as e:
                logging.warning("画像のEXIF情報取得失敗 (%s): %s", file_path, e)
        # 動画ファイルの作成日を取得
        elif file_path.lower().endswith((".mp4", ".mov", ".m4v")):
            try:
                probe = ffmpeg.probe(file_path, select_streams='v:0', show_entries='format_tags=creation_time', of='json')
                creation_time = probe['format']['tags'].get('creation_time', None)
                if creation_time:
                    metadata['CreationDate'] = creation_time
                return metadata
            except Exception as e:
                logging.warning("動画のメタデータ取得失敗 (%s): %s", file_path, e)
    except Exception as e:
        logging.warning("メタデータ取得失敗 (%s): %s", file_path, e)
    return metadata

def get_creation_date(json_data, file_path):
    logging.debug(f"[get_creation_date] {file_path}, json_data: {json_data}")
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
        logging.warning("JSON日時変換失敗 (%s): %s", file_path, e)
    # JSONから取得できなかった場合はExifから取得
    try:
        metadata = extract_metadata(file_path)
        logging.debug("Exif取得成功: %s -> %s", file_path, metadata)
        for tag in ["EXIF:DateTimeOriginal", "QuickTime:CreateDate", "CreationDate", "FileModifyDate"]:
            date_str = metadata.get(tag)
            if date_str:
                dt = parse_exif_date(date_str)
                if dt:
                    return dt
    except Exception as e:
        logging.warning("Exif日時取得失敗 (%s): %s", file_path, e)
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

# ---------- 正規表現パターン管理 ----------
def get_json_patterns(name, ext):
    """
    GoogleフォトTakeout由来のJSONにマッチする正規表現リストを返す。
    追加や変更はこの関数だけ直せば全体に反映される。
    """
    return [
        rf"^{re.escape(name)}(\..*?)?\.json$",
        rf"^{re.escape(name)}{re.escape(ext)}(\..*?)?\.json$",
        rf"^{re.escape(name)}(\.[0-9a-f]+)?\.json$",
        rf"^{re.escape(name)}\.(heic|jpg|jpeg|png|mp4|mov|m4v)(\..*?)?\.json$",
        rf"^{re.escape(name)}\.[0-9]+\.json$",
        rf"^{re.escape(name)}.*?\.json$"
    ]

# ---------- supplemental-metadata補助パターン ----------
def get_json_patterns_for_any_supplemental(name, ext):
    """
    例: name = "B9DE6C2F-xxx(1)", ext = ".jpg"
    .jpg. .json （.supplemental-metadataや.supplや省略にも対応）
    """
    m = re.match(r"^(.*)\((\d+)\)$", name)
    if m:
        base = m.group(1)
        idx = m.group(2)
        # .jpg.何か(1).json（「何か」部分は1つのドット区切り単語, 0回でも可、省略OK）
        return [
            rf"^{re.escape(base)}\.jpg(?:\.[^.]+)?\({idx}\)\.json$",
            rf"^{re.escape(base)}\.{ext[1:]}(?:\.[^.]+)?\({idx}\)\.json$"
        ]
    return []

# ---- find_json_candidates を書き換え ----
def find_json_candidates(file_path):
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)
    name = normalize_base_name(name)
    candidates = []
    json_files = get_cached_json_files(directory)
    json_patterns = get_json_patterns(name, ext)
    supplemental_patterns = get_json_patterns_for_any_supplemental(name, ext)
    try:
        for jf in json_files:
            full_json_path = os.path.join(directory, jf)
            matched = False
            for pattern in json_patterns:
                if re.match(pattern, os.path.basename(jf), re.IGNORECASE):
                    candidates.append(full_json_path)
                    matched = True
                    break
            # JSONの中のタイトルを確認
            if not matched:
                try:
                    with open(full_json_path, encoding="utf-8") as f:
                        data = json.load(f)
                        title = data.get("title", "")
                        if title.startswith(name):
                            candidates.append(full_json_path)
                except json.JSONDecodeError:
                    logging.warning("JSONデコード失敗: %s", full_json_path)
                except (KeyError, OSError) as e:
                    logging.warning("JSON解析中にエラー: %s (%s)", full_json_path, e)
        # --- ここで補助パターンでも再試行 ---
        if supplemental_patterns:
            for jf in json_files:
                full_json_path = os.path.join(directory, jf)
                if full_json_path in candidates:
                    continue
                for sup_pat in supplemental_patterns:
                    if re.match(sup_pat, os.path.basename(jf), re.IGNORECASE):
                        candidates.append(full_json_path)
    except Exception as e:
        logging.error("[find_json_candidates] 例外発生 (%s): %s", file_path, e)
    return list(set(candidates))



def load_json_data(json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logging.warning("JSONパースエラー: %s", json_path)
    except FileNotFoundError:
        logging.warning("JSONファイルが見つかりません: %s", json_path)
    except Exception as e:
        logging.warning("JSON読込中エラー: %s (%s)", json_path, e)
    return {}

def get_relative_path(path, base):
    return os.path.relpath(path, base)

def move_to_unknown_with_structure(file_path, target_dir, unknown_dir):
    rel_path = get_relative_path(file_path, target_dir)
    dst_path = os.path.join(unknown_dir, rel_path)
    move_file_safely(file_path, dst_path)

def update_file_timestamp(file_path, dt):
    ts = dt.timestamp()
    os.utime(file_path, (ts, ts))

# ExifTool書き込み対応拡張子
EXIFTOOL_WRITEABLE = {".jpg", ".jpeg", ".tif", ".tiff"}

def process_file_with_dirs(file_path, target_dir, output_dir, unknown_dir):
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        logging.info("%s は除外対象です", file_path)
        return "skipped"
    json_candidates = find_json_candidates(file_path)
    metadata = {}
    for jc in json_candidates:
        metadata = load_json_data(jc)
        if metadata:
            break
    taken_time = get_creation_date(metadata, file_path)
    if not taken_time:
        move_to_unknown_with_structure(file_path, target_dir, unknown_dir)
        return "date_unknown"
    year_folder = os.path.join(output_dir, str(taken_time.year))
    dest_filename = os.path.basename(file_path)
    new_file_path = move_file_safely(file_path, os.path.join(year_folder, dest_filename))
    # すべてのファイルでファイルシステムの作成・更新日時も上書き
    if taken_time:
        update_file_timestamp(new_file_path, taken_time)
    try:
        ts_str = taken_time.strftime("%Y:%m:%d %H:%M:%S")
        if ext in EXIFTOOL_WRITEABLE:
            run_exiftool_with_fallback(
                [EXIFTOOL_PATH, f"-AllDates={ts_str}", "-overwrite_original", new_file_path]
            )
        else:
            logging.info(f"ExifTool書き込み非対応拡張子のためスキップ: {new_file_path}")
    except Exception as e:
        logging.error("Exif 書き込みエラー: %s -> %s", file_path, e)
        return "error"
    return "success"
