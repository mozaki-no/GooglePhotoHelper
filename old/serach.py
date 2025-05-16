import os
import json

# 設定
target_file_dir = "C:/Users/baris/Downloads/photo_work/goal/ALL_PHOTOS/date-unknown"  # 実ファイルがあるディレクトリ
json_dir = "C:/Users/baris/Downloads/photo_work/unzip/Takeout"        # JSONファイルがあるルートディレクトリ（再帰的に検索）
output_path = "C:/Users/baris/Downloads/photo_work/check_result.json"         # 出力先ファイル名


# 実ファイル一覧を取得（target_file_dir直下のみ）
target_files = [
    f for f in os.listdir(target_file_dir)
    if os.path.isfile(os.path.join(target_file_dir, f))
]

# JSONファイルの一覧を再帰的に取得（globでなくos.walkを使用）
json_file_set = set()
for root, _, files in os.walk(json_dir):
    for file in files:
        if file.endswith(".json"):
            json_file_set.add(file)  # 正確なファイル名のみ追加

results = []

for file in target_files:
    # 対応するJSONファイル名候補を作成
    candidate1 = f"{file}.json"
    candidate2 = f"{file}.supplemental-metadata.json"
    candidate3 = f"{file}.supplemen.json"  # 既存
    candidate4 = f"{file}.suppl.json"     # 新たに追加した候補

    # JSONが存在するかどうかをチェック
    exists = candidate1 in json_file_set or candidate2 in json_file_set or candidate3 in json_file_set or candidate4 in json_file_set

    results.append({
        "target_file": file,
        "expected_json_candidates": [candidate1, candidate2, candidate3, candidate4],
        "json_exists": exists
    })

# 結果をJSONで出力
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"✅ チェック完了: {len(results)} 件のファイルについてJSON存在判定し、'{output_path}' に出力しました。")