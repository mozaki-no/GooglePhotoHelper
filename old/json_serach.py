import os
import json
import sys
import re

def search_string_in_json(directory, pattern, use_regex=False):
    matched_files = []

    # 先にJSONファイルをすべて取得
    json_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))

    total = len(json_files)
    if total == 0:
        print("⚠️ JSONファイルが見つかりませんでした。")
        return matched_files

    for idx, file_path in enumerate(json_files, 1):
        # 進捗表示
        print(f"\r[{idx}/{total}] 検索中: {file_path}", end="", flush=True)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            text = json.dumps(data, ensure_ascii=False)

            if use_regex:
                if re.search(pattern, text):
                    matched_files.append(file_path)
            else:
                if pattern in text:
                    matched_files.append(file_path)

        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
            print(f"\n⚠️ スキップ: {file_path}（エラー: {e}）")

    print()  # 改行

    return matched_files


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("使い方: python search_json.py <検索対象ディレクトリ> <検索文字列 or 正規表現> [--regex]")
        sys.exit(1)

    target_dir = sys.argv[1]
    search_term = sys.argv[2]
    use_regex = "--regex" in sys.argv

    results = search_string_in_json(target_dir, search_term, use_regex)

    print("\n🔍 検索結果:")
    if results:
        for path in results:
            print(f"✅ 見つかりました: {path}")
    else:
        print("❌ 一致するファイルは見つかりませんでした。")
