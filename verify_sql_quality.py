"""验证SUC0009.sql的条件必填处理和整体SQL质量"""
import os

output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output_stg_file')

# 统计各种SQL模式
stats = {
    'total': 0,
    'has_check_name': 0,
    'has_stg_table': 0,
    'has_dm_table': 0,
    'has_busi_date': 0,
    'has_select_distinct': 0,
    'placeholder': 0,
    'template_based': 0,
    'assembled': 0,
    'conditional': 0,  # 条件必填
    'has_check_expression': 0,
}

for folder in os.listdir(output_dir):
    folder_path = os.path.join(output_dir, folder)
    if not os.path.isdir(folder_path):
        continue
    for fname in os.listdir(folder_path):
        if not fname.endswith('.sql'):
            continue
        fpath = os.path.join(folder_path, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        stats['total'] += 1
        if 'check_name' in content:
            stats['has_check_name'] += 1
        if 'stg_table_name' in content:
            stats['has_stg_table'] += 1
        if 'FROM' in content.upper() and 'TODO_DM_TABLE' not in content:
            stats['has_dm_table'] += 1
        if 'BUSI_DATE' in content or 'busi_date' in content.lower():
            stats['has_busi_date'] += 1
        if 'SELECT DISTINCT' in content.upper() or 'select distinct' in content:
            stats['has_select_distinct'] += 1
        if '-- !!! 未自动生成' in content:
            stats['placeholder'] += 1
        elif 'TODO' in content and 'stg_table_name' in content:
            stats['placeholder'] += 1
        elif '${CHECK_NAME}' in content:
            stats['assembled'] += 1  # 模板变量未替换
        elif 'inner join' in content.lower() or 'INNER JOIN' in content:
            stats['template_based'] += 1
        else:
            stats['assembled'] += 1
        
        if 'IS NULL' in content or 'is null' in content:
            stats['has_check_expression'] += 1

# 条件必填检查 - 从占位SQL找条件必填
for folder in os.listdir(output_dir):
    folder_path = os.path.join(output_dir, folder)
    if not os.path.isdir(folder_path):
        continue
    for fname in os.listdir(folder_path):
        if not fname.endswith('.sql'):
            continue
        fpath = os.path.join(folder_path, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        if '条件性必填' in content or '条件必填' in content:
            stats['conditional'] += 1

print("=== SQL质量统计 ===")
for k, v in stats.items():
    pct = f"({v/stats['total']*100:.1f}%)" if stats['total'] else ""
    print(f"  {k}: {v} {pct}")

# 读取生成日志的最后50行
log_path = os.path.join(output_dir, 'generation_log.txt')
if os.path.exists(log_path):
    print("\n=== 生成日志最后30行 ===")
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for line in lines[-30:]:
        print(line.rstrip())