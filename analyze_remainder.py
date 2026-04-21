"""尝试通过DM字段映射提sheet来补充未匹配的检查项"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.report_check_parser import load_report_checks
from parsers.etl_mapper import load_my_poor_solution, find_mapping_for_check, ETLMapping, InspectionRow

# 加载数据
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
report_check_path = os.path.join(base_dir, "report_check_list.xlsx")
my_poor_solution_path = os.path.join(base_dir, "my_poor_solution.xlsx")

checks = load_report_checks(report_check_path)
mapping = load_my_poor_solution(my_poor_solution_path)

# 找出未匹配的检查项
unmatched = []
for check in checks:
    result = find_mapping_for_check(check, mapping)
    if result is None:
        unmatched.append(check)

print(f"未匹配检查项: {len(unmatched)}")

# 尝试通过DM字段映射补充
new_matched = 0
still_unmatched = []

for check in unmatched:
    # 尝试在DM字段映射中查找
    key = f"{check.report_table}.{check.report_field}"
    if key in mapping.dm_field_map:
        new_matched += 1
        dm_rows = mapping.dm_field_map[key]
        dm_row = dm_rows[0]
        print(f"  通过DM字段映射补充: {key} → DM={dm_row.ref_tab}.{dm_row.ref_col}, "
              f"STG={dm_row.source_table or 'N/A'}.{dm_row.source_col or 'N/A'}")
    else:
        still_unmatched.append(check)

print(f"\n通过DM字段映射额外匹配: {new_matched}")
print(f"仍然未匹配: {len(still_unmatched)}")

# 看看仍然未匹配的报表名
still_tables = {}
for check in still_unmatched:
    t = check.report_table
    if t not in still_tables:
        still_tables[t] = 0
    still_tables[t] += 1
print(f"\n仍然未匹配的报表分布:")
for t, cnt in sorted(still_tables.items(), key=lambda x: -x[1]):
    print(f"  {t}: {cnt} 条")

# 检查这些报表是否在巡检列的其他字段中出现过
print("\n=== 在巡检列中搜索未匹配报表名 ===")
for table in sorted(still_tables.keys()):
    found = False
    for key in mapping.inspection_map:
        if table.upper() in key.upper():
            found = True
            break
    for key in mapping.dm_field_map:
        if table.upper() in key.upper():
            found = True
            break
    
    # 进一步模糊：看看去掉前缀后是否有匹配
    table_core = table.upper().replace('URP_SRDT5_', '').replace('URP_TPRT_', '').replace('DM_', '').replace('URP_TPRT_', '')
    for key in mapping.inspection_map:
        key_core = key.split('.')[0].upper().replace('URP_SRDT5_', '').replace('URP_TPRT_', '').replace('DM_', '')
        if table_core == key_core or key_core.startswith(table_core[:5]):
            found = True
            break
    
    if not found:
        print(f"  {table} → 完全无匹配 (核心: {table_core})")
    else:
        print(f"  {table} → 有模糊匹配 (核心: {table_core})")