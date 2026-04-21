"""抽样验证v2生成的SQL文件"""
import os
import glob

output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output_stg_file')

# 读取几个不同类型的SQL文件
test_files = [
    'SUC0001_SUC0100/SUC0001.sql',  # 第一个
    'SUC0001_SUC0100/CUC0009.sql',   # 可能不存在
]

# 找实际存在的文件
all_sqls = []
for folder in sorted(os.listdir(output_dir)):
    folder_path = os.path.join(output_dir, folder)
    if os.path.isdir(folder_path):
        for f in sorted(os.listdir(folder_path))[:2]:
            if f.endswith('.sql'):
                all_sqls.append(os.path.join(folder_path, f))

# 抽样：有SQL模板的（前几个）
print("=== 抽样验证 ===\n")

# 选不同位置的文件
sample_indices = [0, 1, 50, 100, 200, 500, 1000, 1500, 1740]
for idx in sample_indices:
    if idx < len(all_sqls):
        fpath = all_sqls[idx]
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 判断类型
        if '-- !!! 未自动生成' in content:
            sql_type = 'PLACEHOLDER(需人工)'
        elif '${CHECK_NAME}' in content or 'TODO' in content:
            sql_type = 'INCOMPLETE(未替换占位符)'
        else:
            sql_type = 'GENERATED'
        
        fname = os.path.basename(fpath)
        folder = os.path.basename(os.path.dirname(fpath))
        print(f"\n--- {folder}/{fname} [{sql_type}] ---")
        # 只打印前30行
        lines = content.split('\n')[:30]
        for line in lines:
            print(line)
        if len(content.split('\n')) > 30:
            print(f"  ... (共 {len(content.split(chr(10)))} 行)")

# 统计
total = 0
placeholder = 0
generated = 0
with_template = 0
has_check_name = 0
has_stg_table = 0

for fpath in all_sqls:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    total += 1
    if '-- !!! 未自动生成' in content:
        placeholder += 1
    else:
        generated += 1
        if 'SELECT DISTINCT' in content:
            generated += 0
        if 'check_name' in content.lower():
            has_check_name += 1
        if 'stg_table_name' in content.lower():
            has_stg_table += 1

print(f"\n\n=== 统计 ===")
print(f"总文件数: {total}")
print(f"自动生成: {generated}")
print(f"需人工补充: {placeholder}")
print(f"有check_name: {has_check_name}")
print(f"有stg_table_name: {has_stg_table}")