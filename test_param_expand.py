"""
临时脚本：仅对特定检查项执行 generate_stg_checks 并打印展开的 SQL 片段。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_stg_checks import load_report_checks, load_my_poor_solution, load_param_config, generate_sql_from_template, find_mapping_for_check, is_project_related

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
report_check_path = os.path.join(base_dir, 'report_check_list.xlsx')
my_poor_solution_path = os.path.join(base_dir, 'my_poor_solution.xlsx')
param_config_path = os.path.join(base_dir, 'code_param_list.xlsx')

checks = load_report_checks(report_check_path)
mapping = load_my_poor_solution(my_poor_solution_path, None)
param_config = load_param_config(param_config_path)

# 选择几个已知会展开的检查项
target_codes = ['103.1707', '304.1900']
for check in checks:
    if check.check_code not in target_codes:
        continue
    # 使用主函数生成 SQL，内部会处理映射缺失情况
    sql = generate_sql_for_check(check, mapping, {}, {}, None)
    print('\n--- Check', check.check_code, '---')
    print(sql[:500])
    # 直接调用参数展开函数
    from generate_stg_checks import generate_param_expanded_sqls
    expanded = generate_param_expanded_sqls(sql, check, insp, param_config, stg_key, {}, is_project_related(check), None)
    for i, exp in enumerate(expanded[:3]):
        print('\n[Expanded %d] combo=%s' % (i+1, exp.get('param_combo')))
        print(exp['sql'][:500])
