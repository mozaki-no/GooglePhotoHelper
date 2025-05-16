import os

def list_extensions(directory):
    extensions = set()

    for root, _, files in os.walk(directory):
        for file in files:
            _, ext = os.path.splitext(file)
            if ext:  # 空文字列（拡張子なし）は除外
                extensions.add(ext.lower())

    return sorted(extensions)

# 使用例
if __name__ == "__main__":
    target_dir = input("検索対象のディレクトリを入力してください: ").strip()
    
    if os.path.isdir(target_dir):
        exts = list_extensions(target_dir)
        print("見つかった拡張子:")
        for ext in exts:
            print(ext)
    else:
        print("指定されたパスは存在しないか、ディレクトリではありません。")
