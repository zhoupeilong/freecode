"""确认305.1918的精确匹配来源"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.etl_mapper import load_my_poor_solution

mapping = load_my_poor_solution(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'my_poor_solution.xlsx'))

key = 'URP_SRDT5_XTCPLXRXXB.XMJLHXMFZRGH'
print(f"Exact in inspection_map: {key in mapping.inspection_map}")
print(f"In dm_field_map: {key in mapping.dm_field_map}")

if key in mapping.dm_field_map:
    rows = mapping.dm_field_map[key]
    print(f"DM field rows: {len(rows)}")
    for r in rows:
        print(f"  ref_tab: {r.ref_tab}, ref_col: {r.ref_col}, source: {r.source_table}.{r.source_col}")

# 搜索所有含有 XMJLHXMFZRGH 的条目
print("\n=== 搜索含 XMJLHXMFZRGH 的巡检列条目 ===")
for k, rows in mapping.inspection_map.items():
    for r in rows:
        if 'XMJLHXMFZRGH' in r.dm_field.upper() or 'XMJLHXMFZRGH' in r.stg_field.upper():
            print(f"  {k}: dm={r.dm_table}.{r.dm_field}, stg={r.stg_table}.{r.stg_field}")
            print(f"    check_expression: {r.check_expression[:80] if r.check_expression else 'N/A'}")

# 检查 find_mapping_for_check 内部逻辑
from parsers.report_check_parser import load_report_checks
from parsers.etl_mapper import find_mapping_for_check
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
checks = load_report_checks(base_dir + r'\report_check_list.xlsx')
check = [c for c in checks if c.check_code == '305.1918'][0]

# 手动追踪 find_mapping_for_check 的每一步
field_alias = f"{check.report_table}.{check.report_field}"
print(f"\n=== 手动追踪 find_mapping_for_check ===")
print(f"field_alias: {field_alias}")

# Step 1: 精确匹配
if field_alias in mapping.inspection_map:
    print(f"Step 1 EXACT: Found in inspection_map!")
    rows = mapping.inspection_map[field_alias]
    print(f"  rows: {len(rows)}, first dm_field={rows[0].dm_field}")
else:
    print(f"Step 1: Not found in inspection_map")
    
    # Step 2: 大小写
    found_ci = False
    for k in mapping.inspection_map:
        if k.upper() == field_alias.upper():
            print(f"Step 2 CI: Found {k}")
            found_ci = True
            break
    if not found_ci:
        print(f"Step 2: Not found (case-insensitive)")
        
        # Step 3: DM field mapping
        dm_key = f"{check.report_table}.{check.report_field}"
        if dm_key in mapping.dm_field_map:
            dm_rows = mapping.dm_field_map[dm_key]
            dm_row = dm_rows[0]
            print(f"Step 3 (NEW): DM field mapping found!")
            print(f"  ref_tab: {dm_row.ref_tab}, ref_col: {dm_row.ref_col}")
            
            # Find reference row
            ref_row = None
            for ik, irows in mapping.inspection_map.items():
                for r in irows:
                    if r.dm_table == dm_row.ref_tab and r.sql_template:
                        ref_row = r
                        print(f"  Reference row found: {ik}")
                        print(f"    ref dm_field: {r.dm_field}, ref stg_field: {r.stg_field}")
                        break
                if ref_row:
                    break
            
            if ref_row:
                print(f"\n  RESULT: Using reference row's SQL template with DM field override")
                print(f"  Created InspectionRow with:")
                print(f"    field_alias: {field_alias}")
                print(f"    dm_field: {dm_row.ref_col} (=XMJLHXMFZRGH?)")
                print(f"    stg_field: {dm_row.source_col}")
                print(f"    sql_template: FROM REFERENCE ROW (which has hardcoded fields of {ref_row.dm_field})")
        else:
            print(f"Step 3: Not found in dm_field_map either!")