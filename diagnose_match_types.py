"""诊断匹配类型：精确匹配 vs 报表名匹配 vs DM字段映射补充"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.report_check_parser import load_report_checks
from parsers.etl_mapper import load_my_poor_solution, find_mapping_for_check

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
checks = load_report_checks(base_dir + r'\report_check_list.xlsx')
mapping = load_my_poor_solution(base_dir + r'\my_poor_solution.xlsx')

# 分类每条检查项的匹配类型
match_types = {
    'exact': 0,      # 精确字段别名匹配
    'case_insensitive': 0,  # 大小写不敏感匹配
    'table_only': 0,  # 同报表名匹配（可能字段不同！）
    'dm_supplement': 0,     # DM字段映射补充
    'none': 0,       # 无匹配
}

table_only_mismatches = []  # 字段不匹配的记录

for check in checks:
    field_alias = f"{check.report_table}.{check.report_field}"
    
    # 策略1: 精确匹配
    if field_alias in mapping.inspection_map:
        match_types['exact'] += 1
        continue
    
    # 策略2: 大小写不敏感
    found_ci = False
    for key in mapping.inspection_map:
        if key.upper() == field_alias.upper():
            found_ci = True
            break
    if found_ci:
        match_types['case_insensitive'] += 1
        continue
    
    # 策略3: 同报表名匹配（可能字段不同！）
    found_table = False
    for key, rows in mapping.inspection_map.items():
        key_parts = key.split('.')
        if len(key_parts) == 2 and key_parts[0].upper() == check.report_table.upper():
            found_table = True
            # 检查字段名是否一致
            row = rows[0]
            dm_field = row.dm_field
            if dm_field != check.report_field:
                table_only_mismatches.append({
                    'check_code': check.check_code,
                    'report_table': check.report_table,
                    'report_field': check.report_field,
                    'matched_dm_field': dm_field,
                    'matched_stg_field': row.stg_field,
                    'matched_sql': '有' if row.sql_template else '无',
                })
            break
    
    if found_table:
        match_types['table_only'] += 1
        continue
    
    # 策略4: DM字段映射
    dm_key = f"{check.report_table}.{check.report_field}"
    if dm_key in mapping.dm_field_map:
        match_types['dm_supplement'] += 1
        continue
    
    match_types['none'] += 1

print("=== 匹配类型分布 ===")
total = len(checks)
for k, v in match_types.items():
    pct = v / total * 100
    print(f"  {k}: {v} ({pct:.1f}%)")

print(f"\n=== 同报表名匹配中字段不一致的记录数: {len(table_only_mismatches)} ===")
print(f"（这些记录的report_field与dm_field不同，SQL模板可能查了错误的字段）")

if table_only_mismatches:
    print(f"\n前20条字段不一致的记录:")
    for item in table_only_mismatches[:20]:
        print(f"  {item['check_code']}: {item['report_table']}.{item['report_field']} → 错误匹配到 {item['matched_dm_field']} (STG: {item['matched_stg_field']}, SQL: {item['matched_sql']})")