"""追踪305.1918的匹配逻辑 - 核心问题诊断"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.etl_mapper import load_my_poor_solution

mapping = load_my_poor_solution(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'my_poor_solution.xlsx'))

# 核心问题：report_check_list中305.1918的字段是 XMJLHXMFZRGH
# 但巡检列中匹配到的是 FGXMDGSGGGH
# 这是因为 find_mapping_for_check 没有精确匹配到 XMJLHXMFZRGH
# 而是通过"同一报表名"找到了第一行

print("=== 精确匹配测试 ===")
key1 = "URP_SRDT5_XTCPLXRXXB.XMJLHXMFZRGH"
key2 = "URP_TPRT_XTCPLXRXXB.XMJLHXMFZRGH"
key3 = "URP_SRDT5_XTCPLXRXXB.FGXMDGSGGGH"

print(f"Exact URP_SRDT5_XTCPLXRXXB.XMJLHXMFZRGH: {key1 in mapping.inspection_map}")
print(f"Exact URP_TPRT_XTCPLXRXXB.XMJLHXMFZRGH: {key2 in mapping.inspection_map}")
print(f"Exact URP_SRDT5_XTCPLXRXXB.FGXMDGSGGGH: {key3 in mapping.inspection_map}")

# 看看XTCPLXRXXB在巡检列中有哪些行
print("\n=== 巡检列中含XTCPLXRXXB的所有字段别名 ===")
xtcplxr_entries = [(k, len(v)) for k, v in mapping.inspection_map.items() if 'XTCPLXRXXB' in k.upper()]
for k, cnt in xtcplxr_entries[:30]:
    rows = mapping.inspection_map[k]
    r = rows[0]
    print(f"  {k}: {cnt} 行, DM={r.dm_table}, DM_field={r.dm_field}, STG={r.stg_table}.{r.stg_field}")

# 看看有没有XMJLHXMFZRGH字段
print("\n=== 搜索含XMJLHXMFZRGH的条目 ===")
xmjl_entries = [(k, len(v)) for k, v in mapping.inspection_map.items() if 'XMJLHXMFZRGH' in k.upper()]
print(f"含XMJLHXMFZRGH的条目: {xmjl_entries}")

# 搜索含项目经理相关字段的条目
print("\n=== 搜索可能的字段名变体 ===")
check_names = ['XMJLHXMFZRGH', 'FGXMDGSGGGH', 'XMJL', 'FGXMDG']
for cn in check_names:
    entries = [(k, len(v)) for k, v in mapping.inspection_map.items() if cn in k.upper()]
    print(f"  含 '{cn}' 的条目数: {len(entries)}")
    for k, cnt in entries[:5]:
        rows = mapping.inspection_map[k]
        r = rows[0]
        print(f"    {k}: DM_field={r.dm_field}")

# 关键：show how find_mapping_for_check resolves
print("\n=== find_mapping_for_check 匹配过程 ===")
from parsers.report_check_parser import load_report_checks
checks = load_report_checks(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'report_check_list.xlsx'))
check = [c for c in checks if c.check_code == '305.1918'][0]

field_alias = f"{check.report_table}.{check.report_field}"
print(f"  report_table: {check.report_table}")
print(f"  report_field: {check.report_field}")
print(f"  目标别名: {field_alias}")
print(f"  精确匹配: {field_alias in mapping.inspection_map}")

# 报表名匹配：同一报表名有多少行？
table_rows = [(k, len(v)) for k, v in mapping.inspection_map.items() 
               if k.split('.')[0].upper() == check.report_table.upper()]
print(f"  同一报表名(XTCPLXRXXB)的条目数: {len(table_rows)}")
print(f"  第一条（被匹配的）: {table_rows[0] if table_rows else 'N/A'}")

# URP_TPRT_XTCPLXRXXB vs URP_SRDT5_XTCPLXRXXB
print("\n=== TPRT vs SRDT5 前缀差异 ===")
tprt_entries = [(k, len(v)) for k, v in mapping.inspection_map.items() if 'URP_TPRT_XTCPLXRXXB' in k]
srdt5_entries = [(k, len(v)) for k, v in mapping.inspection_map.items() if 'URP_SRDT5_XTCPLXRXXB' in k]
print(f"  URP_TPRT_XTCPLXRXXB 条目数: {len(tprt_entries)}")
print(f"  URP_SRDT5_XTCPLXRXXB 条目数: {len(srdt5_entries)}")
print(f"  结论: report_check_list使用URP_SRDT5_前缀，但巡检列只有URP_TPRT_前缀！")