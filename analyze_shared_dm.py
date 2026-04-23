"""
analyze_shared_dm.py - 分析共享DM指标

功能：
1. 关联report_check_list.xlsx和urp_dm_field_mapping.xlsx
2. 找出不同报表勾稽代码引用相同DM指标字段的情况
3. 标记共享的报表勾稽代码（S表示Share）
4. 确定应该生成STG巡检代码的勾稽代码（优先DQ开头）

输出：
- 共享DM指标映射表（供generate_stg_checks.py使用）
- 分析报告
"""

import os
import sys
import json
import re
import pandas as pd
from typing import Dict, List, Set, Tuple
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def is_dq_prefix(code: str) -> bool:
    """判断勾稽代码是否以DQ开头（定期报送）"""
    return str(code).strip().upper().startswith('DQ')


def is_numeric_prefix(code: str) -> bool:
    """判断勾稽代码是否以数字开头"""
    return bool(re.match(r'^\d+', str(code).strip()))


def load_and_merge_data(report_xlsx: str, dm_mapping_xlsx: str) -> pd.DataFrame:
    """
    加载并关联报表勾稽和DM字段映射

    Returns:
        合并后的DataFrame，包含勾稽代码、DM表名、DM字段名
    """
    # 加载报表勾稽列表
    report_df = pd.read_excel(report_xlsx, sheet_name='Sheet1')
    report_df = report_df[['报表名称', '报表字段', '勾稽代码', '报表勾稽名称', '是否必填']].copy()

    # 加载DM字段映射
    dm_df = pd.read_excel(dm_mapping_xlsx, sheet_name='URP_DM字段映射')
    dm_df = dm_df[['URP_TABLE_NAME', 'URP_COLUMN_NAME', 'DM_TABLE_NAME', 'DM_COLUMN_NAME']].copy()

    # 关联：报表名称+报表字段 = URP表名+URP字段名
    merged = report_df.merge(
        dm_df,
        left_on=['报表名称', '报表字段'],
        right_on=['URP_TABLE_NAME', 'URP_COLUMN_NAME'],
        how='inner'
    )

    # 过滤掉没有DM字段的记录
    merged = merged[merged['DM_COLUMN_NAME'].notna()].copy()

    # 统一勾稽代码格式
    merged['勾稽代码_str'] = merged['勾稽代码'].astype(str).str.strip()

    # 标记类型
    merged['code_type'] = merged['勾稽代码_str'].apply(
        lambda x: 'DQ' if is_dq_prefix(x) else ('NUM' if is_numeric_prefix(x) else 'OTHER')
    )

    print(f"合并后记录数: {len(merged)}")
    print(f"  - DQ开头: {sum(merged['code_type'] == 'DQ')}")
    print(f"  - 数字开头: {sum(merged['code_type'] == 'NUM')}")

    return merged


def find_shared_dm_indicators(merged_df: pd.DataFrame) -> pd.DataFrame:
    """
    找出被多个不同勾稽代码引用的DM指标

    Returns:
        共享DM指标DataFrame，包含：
        - DM_TABLE_NAME, DM_COLUMN_NAME: DM表和字段
        - 引用此DM指标的所有勾稽代码列表
        - selected_code: 应该生成STG巡检的勾稽代码（优先DQ开头）
        - is_shared: 是否共享
    """
    # 按DM指标分组，收集所有勾稽代码
    grouped = merged_df.groupby(['DM_TABLE_NAME', 'DM_COLUMN_NAME']).agg({
        '勾稽代码_str': lambda x: list(set(x)),
        'code_type': lambda x: list(set(x)),
        '报表名称': lambda x: list(set(x)),
        '报表字段': lambda x: list(set(x)),
    }).reset_index()

    grouped['code_count'] = grouped['勾稽代码_str'].apply(len)
    grouped['is_shared'] = grouped['code_count'] > 1

    # 只保留共享的DM指标
    shared = grouped[grouped['is_shared']].copy()

    # 选择生成STG巡检的勾稽代码（优先DQ开头）
    def select_stg_code(codes, code_types):
        """
        选择生成STG巡检代码的勾稽代码
        规则：
        1. 优先选择DQ开头的（定期报送）
        2. 如果没有DQ开头的，选择数字开头的
        3. 否则选择第一个
        """
        dq_codes = [c for c in codes if is_dq_prefix(c)]
        if dq_codes:
            return dq_codes[0]  # 返回第一个DQ开头的

        num_codes = [c for c in codes if is_numeric_prefix(c)]
        if num_codes:
            return num_codes[0]

        return codes[0]

    shared['selected_code'] = shared.apply(
        lambda r: select_stg_code(r['勾稽代码_str'], r['code_type']), axis=1
    )

    # 标记各勾稽代码是否为选中的生成目标
    def mark_selected_codes(row):
        selected = row['selected_code']
        all_codes = row['勾稽代码_str']
        result = {}
        for code in all_codes:
            result[code] = 'S' if code == selected else 'C'  # S=Share(生成), C=Common(共用)
        return result

    shared['code_share_status'] = shared.apply(mark_selected_codes, axis=1)

    return shared


def generate_exclusion_set(shared_df: pd.DataFrame) -> Set[str]:
    """
    生成需要排除的勾稽代码集合
    这些勾稽代码引用的DM指标已被其他勾稽代码共享，不需要单独生成STG巡检

    Returns:
        排除的勾稽代码集合
    """
    exclusion_set = set()

    for _, row in shared_df.iterrows():
        selected = row['selected_code']
        all_codes = row['勾稽代码_str']

        # 除了选中的，其他都排除
        for code in all_codes:
            if code != selected:
                exclusion_set.add(code)

    return exclusion_set


def export_mapping(shared_df: pd.DataFrame, output_path: str):
    """导出共享DM指标映射为JSON"""
    mapping = {}

    for _, row in shared_df.iterrows():
        dm_key = f"{row['DM_TABLE_NAME']}.{row['DM_COLUMN_NAME']}"
        mapping[dm_key] = {
            'all_codes': row['勾稽代码_str'],
            'selected_code': row['selected_code'],
            'share_status': row['code_share_status'],
            'report_tables': list(set(row['报表名称'])),
            'report_fields': list(set(row['报表字段'])),
        }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print(f"\n共享DM指标映射已导出到: {output_path}")
    return mapping


def generate_report(merged_df: pd.DataFrame, shared_df: pd.DataFrame,
                   exclusion_set: Set[str], report_output: str):
    """生成分析报告"""
    report_lines = []

    report_lines.append("=" * 80)
    report_lines.append("STG巡检代码共享分析报告")
    report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)
    report_lines.append("")

    # 总体统计
    report_lines.append("一、总体统计")
    report_lines.append("-" * 40)
    report_lines.append(f"报表勾稽记录总数: {len(merged_df)}")
    report_lines.append(f"有DM字段映射的记录数: {len(merged_df[merged_df['DM_COLUMN_NAME'].notna()])}")
    report_lines.append(f"共享DM指标数量: {len(shared_df)}")
    report_lines.append(f"需要排除的勾稽代码数: {len(exclusion_set)}")
    report_lines.append("")

    # 类型分布
    report_lines.append("二、勾稽代码类型分布")
    report_lines.append("-" * 40)
    code_type_counts = merged_df['code_type'].value_counts()
    for code_type, count in code_type_counts.items():
        report_lines.append(f"  {code_type}: {count}")
    report_lines.append("")

    # 共享DM指标样例
    report_lines.append("三、共享DM指标样例（前20条）")
    report_lines.append("-" * 40)
    report_lines.append(f"{'DM指标':<45} {'引用勾稽代码':<30} {'生成目标':<15}")
    report_lines.append("-" * 90)

    for i, row in shared_df.head(20).iterrows():
        dm_key = f"{row['DM_TABLE_NAME']}.{row['DM_COLUMN_NAME']}"
        codes_str = ', '.join(row['勾稽代码_str'][:5])
        if len(row['勾稽代码_str']) > 5:
            codes_str += f"..."
        selected = row['selected_code']
        report_lines.append(f"{dm_key:<45} {codes_str:<30} {selected:<15}")

    report_lines.append("")

    # 选中目标统计
    report_lines.append("四、生成目标勾稽代码统计")
    report_lines.append("-" * 40)
    selected_codes = shared_df['selected_code'].value_counts()
    dq_count = sum(1 for x in selected_codes.index if is_dq_prefix(x))
    num_count = sum(1 for x in selected_codes.index if is_numeric_prefix(x))
    report_lines.append(f"  DQ开头（定期报送）: {dq_count}")
    report_lines.append(f"  数字开头: {num_count}")
    report_lines.append(f"  总计: {len(selected_codes)}")
    report_lines.append("")

    # 排除的勾稽代码样例
    report_lines.append("五、需要排除的勾稽代码样例（前30条）")
    report_lines.append("-" * 40)
    exclusion_list = sorted(list(exclusion_set))
    for code in exclusion_list[:30]:
        report_lines.append(f"  {code}")
    if len(exclusion_list) > 30:
        report_lines.append(f"  ... 共 {len(exclusion_list)} 个")

    report_lines.append("")
    report_lines.append("=" * 80)

    report_text = '\n'.join(report_lines)
    print(report_text)

    with open(report_output, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"\n报告已导出到: {report_output}")

    return report_text


def main():
    # 路径配置
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_xlsx = os.path.join(project_root, 'report_check_list.xlsx')
    dm_mapping_xlsx = os.path.join(project_root, 'urp_dm_field_mapping.xlsx')
    output_dir = os.path.join(project_root, 'output_stg_file')

    os.makedirs(output_dir, exist_ok=True)

    mapping_output = os.path.join(output_dir, 'shared_dm_mapping.json')
    report_output = os.path.join(output_dir, 'shared_dm_analysis_report.txt')

    # 1. 加载并关联数据
    print("步骤1: 加载并关联数据...")
    merged_df = load_and_merge_data(report_xlsx, dm_mapping_xlsx)

    # 2. 查找共享DM指标
    print("\n步骤2: 查找共享DM指标...")
    shared_df = find_shared_dm_indicators(merged_df)
    print(f"找到 {len(shared_df)} 个共享DM指标")

    # 3. 生成排除集合
    print("\n步骤3: 生成排除集合...")
    exclusion_set = generate_exclusion_set(shared_df)
    print(f"需要排除 {len(exclusion_set)} 个勾稽代码")

    # 4. 导出映射
    print("\n步骤4: 导出共享DM指标映射...")
    export_mapping(shared_df, mapping_output)

    # 5. 生成报告
    print("\n步骤5: 生成分析报告...")
    generate_report(merged_df, shared_df, exclusion_set, report_output)

    print("\n" + "=" * 60)
    print("分析完成!")
    print("=" * 60)

    # 返回结果供其他模块使用
    return {
        'shared_df': shared_df,
        'exclusion_set': exclusion_set,
        'mapping_output': mapping_output,
    }


if __name__ == '__main__':
    main()