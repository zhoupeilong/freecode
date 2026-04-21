"""追踪勾稽代码 305.1918 的完整数据链路"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.report_check_parser import load_report_checks
from parsers.etl_mapper import load_my_poor_solution, find_mapping_for_check, InspectionRow

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
checks = load_report_checks(os.path.join(base_dir, "report_check_list.xlsx"))
mapping = load_my_poor_solution(os.path.join(base_dir, "my_poor_solution.xlsx"))

# 1. 找到勾稽代码 305.1918 对应的检查项
target_code = "305.1918"
target_checks = [c for c in checks if c.check_code == target_code]

print(f"=== 勾稽代码 {target_code} 对应的检查项 ===")
for c in target_checks:
    print(f"  record_id: {c.record_id}")
    print(f"  report_table: {c.report_table}")
    print(f"  report_field: {c.report_field}")
    print(f"  check_code: {c.check_code}")
    print(f"  check_name: {c.check_name}")
    print(f"  is_mandatory: {c.is_mandatory} (conditional={c.is_conditional})")
    print(f"  precondition: {c.precondition}")
    print(f"  pre_table: {c.pre_table}")
    print(f"  pre_column: {c.pre_column}")
    print(f"  pre_value: {c.pre_value}")

# 2. 查找巡检列映射
check = target_checks[0]
field_alias = f"{check.report_table}.{check.report_field}"
print(f"\n=== 查找巡检列映射 ===")
print(f"  字段别名: {field_alias}")

result = find_mapping_for_check(check, mapping)
if result:
    print(f"  匹配类型: InspectionRow")
    print(f"  DM表: {result.dm_table}")
    print(f"  DM字段: {result.dm_field}")
    print(f"  STG表: {result.stg_table}")
    print(f"  STG字段: {result.stg_field}")
    print(f"  STG表中文名: {result.stg_table_cn}")
    print(f"  STG字段中文名: {result.stg_field_cn}")
    print(f"  关联体系ID: {result.link_id}")
    print(f"  SQL模板: {'有' if result.sql_template else '无'}")
    print(f"  检验表达式: {result.check_expression}")
    print(f"  取数来源: {result.stg_table}")
    print(f"  取数来源字段: {result.stg_field}")
    if result.sql_template:
        print(f"\n  === SQL模板 (前500字符) ===")
        print(f"  {result.sql_template[:500]}")
else:
    print(f"  未找到映射!")
    
    # 尝试查找该报表名在任何映射中的记录
    print(f"\n  === 模糊搜索 ===")
    found_in_insp = False
    for key, rows in mapping.inspection_map.items():
        if check.report_table.upper() in key.upper():
            print(f"  巡检列匹配: {key}")
            found_in_insp = True
            if found_in_sp:
                break
    
    # DM字段映射
    dm_key = f"{check.report_table}.{check.report_field}"
    if dm_key in mapping.dm_field_map:
        dm_rows = mapping.dm_field_map[dm_key]
        for dm_row in dm_rows[:3]:
            print(f"  DM字段映射: ref_tab={dm_row.ref_tab}, ref_col={dm_row.ref_col}")

# 3. 查找在所有检查项中的序号（SUC编号）
for i, c in enumerate(checks, start=1):
    if c.check_code == target_code:
        print(f"\n=== SUC编号 ===")
        print(f"  SUC编号: SUC{i:04d}")
        print(f"  子文件夹: SUC{((i-1)//100)*100+1:04d}_SUC{((i-1)//100)*100+100:04d}")
        break