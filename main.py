import logging
import os
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor
from collections import Counter
import metadata_utils
from metadata_utils import (
    check_exiftool, collect_files, process_file_with_dirs, SUPPORTED_EXTENSIONS
)

LOG_FILE = "google_photo_helper.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")  # ファイルのみ
    ]
)

def prompt_dir(prompt, default):
    while True:
        path = input(f"{prompt}（デフォルト: {default}）: ").strip()
        if not path:
            path = default
        if prompt.startswith("入力") and not os.path.isdir(path):
            print("入力ディレクトリが存在しません。もう一度入力してください。")
            continue
        if prompt.startswith("出力") and not os.path.isdir(path):
            try:
                os.makedirs(path, exist_ok=True)
                print(f"出力ディレクトリを作成しました: {path}")
            except Exception as e:
                print(f"出力ディレクトリ作成に失敗: {e}")
                sys.exit(1)
        return path

def process_file_wrapper(args):
    file_path, target_dir, output_dir, unknown_dir = args
    return process_file_with_dirs(file_path, target_dir, output_dir, unknown_dir)

def process_files_parallel(files, target_dir, output_dir, unknown_dir):
    with ProcessPoolExecutor() as executor:
        arglist = [(f, target_dir, output_dir, unknown_dir) for f in files]
        return list(tqdm(executor.map(process_file_wrapper, arglist), total=len(files), desc="処理中", unit="ファイル"))

def main():
    print("Google Photo Helper 起動")
    input_dir = prompt_dir("入力ディレクトリ（TARGET_DIR）を入力してください", metadata_utils.TARGET_DIR)
    output_dir = prompt_dir("出力ディレクトリ（OUTPUT_DIR）を入力してください", metadata_utils.OUTPUT_DIR)
    unknown_dir = os.path.join(output_dir, "date_unknown")

    check_exiftool()
    files = collect_files(input_dir, SUPPORTED_EXTENSIONS)
    results = process_files_parallel(files, input_dir, output_dir, unknown_dir)
    c = Counter(results)
    total = sum(c.values())
    print("------ 処理集計 ------")
    print(f"処理対象ファイル: {total}")
    print(f"成功           : {c.get('success', 0)}")
    print(f"date_unknown   : {c.get('date_unknown', 0)}")
    print(f"スキップ       : {c.get('skipped', 0)}")
    print(f"エラー         : {c.get('error', 0)}")
    print("----------------------")

if __name__ == "__main__":
    main()