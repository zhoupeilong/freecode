"""检查v2生成结果：分析未匹配的检查项"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.report_check_parser import load_report_checks
from parsers.etl_mapper import load_my_poor_solution, find_mapping_for_check, ETLMapping
from parsers.etl_mapper import InspectionRow

# 加载数据
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
report_check_path = os.path.join(base_dir, "report_check_list.xlsx")
my_poor_solution_path = os.path.join(base_dir, "my_poor_solution.xlsx")

checks = load_report_checks(report_check_path)
mapping = load_my_poor_solution(my_poor_solution_path)

# 分析匹配情况
matched = 0
unmatched = []
matched_with_sql = 0
matched_without_sql = 0

for check in checks:
    result = find_mapping_for_check(check, mapping)
    if result:
        matched += 1
        if result.sql_template:
            matched_with_sql += 1
        else:
            matched_without_sql += 1
    else:
        unmatched.append(check)

print(f"总检查项: {len(checks)}")
print(f"匹配成功: {matched} ({matched/len(checks)*100:.1f}%)")
print(f"  有SQL模板: {matched_with_sql}")
print(f"  无SQL模板: {matched_without_sql}")
print(f"未匹配: {len(unmatched)} ({len(unmatched)/len(checks)*100:.1f}%)")

# 分析未匹配的报表名分布
unmatched_tables = {}
for check in unmatched:
    t = check.report_table
    if t not in unmatched_tables:
        unmatched_tables[t] = []
    unmatched_tables[t].append(check)

print(f"\n未匹配涉及的报表名: {len(unmatched_tables)} 个")
print("\n前20个未匹配报表名及其检查项数量:")
for t, items in sorted(unmatched_tables.items(), key=lambda x: -len(x[1]))[:20]:
    print(f"  {t}: {len(items)} 条")

# 尝试在巡检列中查找可能的模糊匹配
print("\n=== 模糊匹配尝试 ===")
for table, items in sorted(unmatched_tables.items(), key=lambda x: -len(x[1]))[:10]:
    # 尝试在巡检列中查找相似的
    found_similar = []
    for key in mapping.inspection_map.keys():
        key_table = key.split('.')[0] if '.' in key else key
        # 去掉前缀后比较核心名称
        table_core = table.replace('URP_SRDT5_', '').replace('URP_TPRT_', '').replace('DM_', '')
        key_core = key_table.replace('URP_SRDT5_', '').replace('URP_TPRT_', '').replace('DM_', '')
        if table_core[:4] == key_core[:4] and table_core != key_core:
            found_similar.append(key_table)
    
    if found_similar:
        print(f"  {table} (→ 可能匹配: {found_similar[:3]})")
    else:
        print(f"  {table} (→ 无相似匹配)")