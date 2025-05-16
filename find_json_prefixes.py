import os

def extract_prefix(filename):
    """
    ファイル名の最後の拡張子の前の部分をプレフィックスとして抽出する
    例: 'file.name.prefix.json' -> 'prefix'
    """
    parts = filename.split('.')
    if len(parts) < 3 or parts[-1].lower() != 'json':
        return None
    return parts[-2]

def find_json_prefixes_with_files(root_dir):
    """
    プレフィックスごとに最初に検出されたファイル名を記録して返す
    """
    prefix_to_file = {}
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            if fname.lower().endswith('.json'):
                prefix = extract_prefix(fname)
                if prefix and prefix not in prefix_to_file:
                    prefix_to_file[prefix] = os.path.join(dirpath, fname)
    return prefix_to_file

if __name__ == "__main__":
    root_directory = input("検索したいディレクトリパスを入力してください: ")
    prefix_file_map = find_json_prefixes_with_files(root_directory)
    
    print("抽出されたプレフィックスと最初に検出されたファイル名:")
    for prefix, filepath in sorted(prefix_file_map.items()):
        print(f"プレフィックス: {prefix}  -  ファイル名: {os.path.basename(filepath)}")
