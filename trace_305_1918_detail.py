"""深入对比验证：305.1918 的 report_check_list vs 巡检列 vs 生成SQL"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.report_check_parser import load_report_checks
from parsers.etl_mapper import load_my_poor_solution, find_mapping_for_check

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
checks = load_report_checks(os.path.join(base_dir, "report_check_list.xlsx"))
mapping = load_my_poor_solution(os.path.join(base_dir, "my_poor_solution.xlsx"))

# 找到305.1918
check = [c for c in checks if c.check_code == "305.1918"][0]
result = find_mapping_for_check(check, mapping)

print("=" * 70)
print("勾稽代码 305.1918 完整数据链路验证")
print("=" * 70)

print("\n【第1层】report_check_list.xlsx 原始数据")
print(f"  报表名(report_table): {check.report_table}")
print(f"  报表字段(report_field): {check.report_field}")
print(f"  勾稽代码: {check.check_code}")
print(f"  勾稽名称: {check.check_name}")
print(f"  是否必填: {check.is_mandatory}")
print(f"  前置条件: {check.precondition}")
print(f"  前置表: {check.pre_table}")
print(f"  前置字段: {check.pre_column}")
print(f"  前置值: {check.pre_value}")

print("\n【第2层】巡检列映射(InspectionRow)")
print(f"  字段别名(field_alias): {result.field_alias}")
print(f"  DM表: {result.dm_table}")
print(f"  DM字段: {result.dm_field}")
print(f"  STG表: {result.stg_table}")
print(f"  STG表中文名: {result.stg_table_cn}")
print(f"  STG字段: {result.stg_field}")
print(f"  STG字段中文名: {result.stg_field_cn}")
print(f"  取数来源: {result.stg_table}")
print(f"  取数来源字段: {result.stg_field}")
print(f"  检验表达式: {result.check_expression}")
print(f"  关联体系ID: {result.link_id}")

print("\n【第3层】对照：report_field 与 DM字段 是否一致？")
print(f"  report_field: {check.report_field} (XMJLHXMFZRGH = 项目经理或项目负责人工号)")
print(f"  DM字段（DM_CTRC_XTCPLXRXXZBB）: {result.dm_field} (FGXMDGSGGGH)")
print(f"  是否一致: {'是' if check.report_field == result.dm_field else '否 ⚠️'}")

print("\n【第4层】check_name 对照")
print(f"  report_check_list 中的勾稽名称: {check.check_name}")
print(f"  巡检列中的 check_name (模板中): SQL模板的CHECK_NAME占位符会被替换为检查项名称")

# 查看巡检列中同报表的所有行
field_alias_key = f"{check.report_table}.{check.report_field}"
if field_alias_key in mapping.inspection_map:
    rows = mapping.inspection_map[field_alias_key]
    print(f"\n【第5层】巡检列中 {field_alias_key} 的所有行 ({len(rows)} 条)")
    for i, r in enumerate(rows):
        print(f"\n  行{i+1}:")
        print(f"    DM字段: {r.dm_field}")
        print(f"    STG表: {r.stg_table}")
        print(f"    STG字段: {r.stg_field}")
        print(f"    检验表达式: {r.check_expression[:80] if r.check_expression else 'N/A'}...")
        
        # 关键检查：report_field(XMJLHXMFZRGH) 和 DM字段(FGXMDGSGGGH) 是否对应？
        # report_check_list中的字段名是报表字段名（URP层）
        # DM字段是DM层的字段名
        # 两者通过DM字段映射表（DD层）关联
        
print("\n【关键问题分析】")
print(f"  报表字段(report_field): {check.report_field}")
print(f"    → 含义: 项目经理或项目负责人工号")
print(f"  DM层字段(dm_field): {result.dm_field}")
print(f"    → 含义: 分管项目的公司高管工号")
print(f"  ")
print(f"  ⚠️ 问题: 报表要求的字段是'项目经理或项目负责人工号'(XMJLHXMFZRGH)")
print(f"  但巡检列SQL模板检查的是'分管项目的公司高管工号'(FGXMDGSGGGH)")
print(f"  ")
print(f"  这是因为巡检列可能有多行，每行对应不同的STG来源字段。")
print(f"  当前实现取了第一行，但实际应该取与report_field对应的行。")

# 检查是否有多行
all_rows = mapping.inspection_map.get(field_alias_key, [])
print(f"\n  同一字段别名的行数: {len(all_rows)}")
if len(all_rows) > 1:
    print(f"  ⚠️ 警告: 同一字段别名有{len(all_rows)}行，当前只取了第一行！")
    for i, r in enumerate(all_rows):
        print(f"    行{i+1}: DM={r.dm_field}, STG={r.stg_table}.{r.stg_field}, check_expr={r.check_expression[:60]}")
else:
    print(f"  只有一行，匹配正确。")

# 再检查：report_field 是否真的等于dm_field?
# 在report_check_list中，report_field是URP层字段名
# 在巡检列中，dm_field是DM层字段名
# URP层字段名和DM层字段名可能不同！
# 我们需要确认report_field(XMJLHXMFZRGH)和DM字段(FGXMDGSGGGH)的关系

print("\n\n【查看DM字段映射表】")
dm_key = f"{check.report_table}.{check.report_field}"
if dm_key in mapping.dm_field_map:
    dm_rows = mapping.dm_field_map[dm_key]
    print(f"  DM字段映射 ({dm_key}):")
    for dr in dm_rows:
        print(f"    TAB_NAME: {dr.tab_name}, TAB_COL: {dr.tab_col}")
        print(f"    REF_TAB: {dr.ref_tab}, REF_COL: {dr.ref_col}")
        print(f"    source_table: {dr.source_table}, source_col: {dr.source_col}")
else:
    print(f"  DM字段映射中未找到 {dm_key}")
    
    # 尝试搜索
    found = False
    for key, dm_rows in mapping.dm_field_map.items():
        if check.report_field in key:
            if not found:
                print(f"  模糊搜索结果（包含 {check.report_field}）:")
            for dr in dm_rows[:2]:
                print(f"    {key} → REF_TAB={dr.ref_tab}, REF_COL={dr.ref_col}")
            found = True
    if not found:
        print(f"  完全找不到 {check.report_field} 相关的DM字段映射")