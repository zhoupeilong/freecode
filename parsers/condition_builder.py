"""
condition_builder.py - 根据前置条件生成 extra_condition SQL 片段

处理两种情况：
1. 必填字段：直接生成 "AND trim(k.字段) IS NULL"
2. 条件必填字段：根据前置表/字段/值生成 EXISTS 或 AND 条件
"""

import re
from typing import Optional
from parsers.report_check_parser import ReportCheckInfo


def build_extra_condition(check_info: ReportCheckInfo,
                          dm_table_alias: str = "k",
                          joined_tables: list = None) -> str:
    """
    根据检查项的前置条件生成 extra_condition SQL 片段。

    Args:
        check_info: 报表检查项
        dm_table_alias: DM 表的别名（默认 'k'）
        joined_tables: 已经 JOIN 的表列表（用于判断是否需要 EXISTS）

    Returns:
        extra_condition SQL 片段（不含 WHERE 关键字）
    """
    conditions = []

    # 1. 如果是条件必填，且前置条件非空
    if check_info.is_conditional and check_info.has_precondition:
        condition = _build_conditional_condition(check_info, dm_table_alias, joined_tables)
        if condition:
            conditions.append(condition)

    # 2. 如果有前置表和前置字段（无论是否条件必填）
    elif check_info.pre_table and check_info.pre_column:
        condition = _build_pre_table_condition(check_info, dm_table_alias, joined_tables)
        if condition:
            conditions.append(condition)

    return '\n'.join(conditions)


def _build_conditional_condition(check_info: ReportCheckInfo,
                                  dm_table_alias: str,
                                  joined_tables: list = None) -> str:
    """
    为条件必填字段生成前置条件。

    格式示例：
    - 简单条件: AND k.sfhlwdk = '1'
    - EXISTS 条件: AND EXISTS (SELECT 1 FROM URP3_TUSP.DM_CTRC_CPTZZBB p WHERE p.sfhlwdk = '1' AND p.主键 = k.主键)
    """
    if not check_info.pre_table:
        # 只有条件描述，没有前置表
        # 尝试从条件描述中提取条件
        return _parse_precondition_text(check_info.precondition, dm_table_alias)

    pre_table = check_info.pre_table.strip()
    pre_column = check_info.pre_column.strip() if check_info.pre_column else ""
    pre_value = check_info.pre_value.strip() if check_info.pre_value else ""

    # 检查前置表是否已经在 JOIN 列表中
    pre_table_short = pre_table.split('.')[-1] if '.' in pre_table else pre_table
    is_joined = joined_tables and pre_table_short.upper() in [t.upper() for t in joined_tables]

    if is_joined:
        # 前置表已在主查询中，直接使用 AND 条件
        alias = _find_table_alias(pre_table_short, joined_tables)
        condition = f"AND {alias}.{pre_column} = {pre_value}"
        return condition
    else:
        # 前置表不在主查询中，使用 EXISTS 子查询
        # 需要确定主键关联条件 - 这里简化处理，使用常见的关联字段
        return f"AND EXISTS (SELECT 1 FROM {pre_table} p WHERE p.{pre_column} = {pre_value} AND p.count_proj_code = {dm_table_alias}.count_proj_code)"


def _build_pre_table_condition(check_info: ReportCheckInfo,
                                dm_table_alias: str,
                                joined_tables: list = None) -> str:
    """为有前置表的检查项生成条件"""
    pre_table = check_info.pre_table.strip()
    pre_column = check_info.pre_column.strip() if check_info.pre_column else ""
    pre_value = check_info.pre_value.strip() if check_info.pre_value else ""

    if not pre_column:
        return ""

    pre_table_short = pre_table.split('.')[-1] if '.' in pre_table else pre_table
    is_joined = joined_tables and pre_table_short.upper() in [t.upper() for t in joined_tables]

    if is_joined:
        alias = _find_table_alias(pre_table_short, joined_tables)
        return f"AND {alias}.{pre_column} = {pre_value}"
    else:
        return f"AND EXISTS (SELECT 1 FROM {pre_table} p WHERE p.{pre_column} = {pre_value} AND p.count_proj_code = {dm_table_alias}.count_proj_code)"


def _find_table_alias(table_name: str, joined_tables: list) -> str:
    """从已 JOIN 的表列表中找到表名对应的别名"""
    # 简化处理：使用表名的首字母小写作为别名
    if not table_name:
        return "p"
    # 常见别名映射
    alias_map = {
        'DM_CTRC_CPTZZBB': 'k',
        'DM_CTRC_CPJBXXZBB': 'k',
        'DW_D_COUNT_PROJ_INFO': 'proj',
    }
    # 默认使用 'p'
    return alias_map.get(table_name, 'p')


def _parse_precondition_text(precondition: str, dm_table_alias: str) -> str:
    """
    从条件描述文本中解析出 SQL 条件。

    例如："<是否互联网贷款>选择是时" -> AND k.sfhlwdk = '1'
    目前返回注释，后续可用 NLP 或配置表处理。
    """
    if not precondition:
        return ""

    # 尝试提取简单的条件模式
    # 模式1: "<字段名>选择是时" -> AND 字段名 = '1'
    pattern1 = re.compile(r'<([^>]+)>选择是时')
    match = pattern1.search(precondition)
    if match:
        return f"-- 条件: {precondition} (需要人工补充具体条件)"

    # 模式2: "<字段名>不应为空" -> 必填，无需额外条件
    if '不应为空' in precondition or '不为空' in precondition or '必填' in precondition:
        return ""

    # 默认：返回注释
    return f"-- 条件: {precondition} (需要人工补充具体条件)"


def build_check_where_clause(check_info: ReportCheckInfo,
                              dm_table_alias: str = "k",
                              dm_field: str = "",
                              joined_tables: list = None) -> str:
    """
    生成完整的 WHERE 子句片段。

    包含：
    1. 必填检查: trim(k.字段) IS NULL
    2. 条件必填的前置条件

    Args:
        check_info: 报表检查项
        dm_table_alias: DM 表别名
        dm_field: DM 表中对应的字段名
        joined_tables: 已 JOIN 的表列表

    Returns:
        WHERE 子句片段
    """
    parts = []

    # 必填检查
    if dm_field:
        parts.append(f"trim({dm_table_alias}.{dm_field}) IS NULL")

    # 前置条件
    extra = build_extra_condition(check_info, dm_table_alias, joined_tables)
    if extra:
        parts.append(extra)

    return '\n'.join(parts)


if __name__ == "__main__":
    # 测试入口
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    from parsers.report_check_parser import load_report_checks

    xlsx_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "..", "report_check_list.xlsx"))

    checks = load_report_checks(xlsx_path)

    # 测试条件必填的前3条
    conditional_checks = [c for c in checks if c.is_conditional and c.has_precondition]

    print("=== 条件必填 - extra_condition 生成示例 ===")
    for c in conditional_checks[:3]:
        condition = build_extra_condition(c)
        print(f"\n勾稽: {c.check_code} - {c.check_name[:40]}...")
        print(f"  前置表: {c.pre_table}")
        print(f"  前置字段: {c.pre_column}")
        print(f"  前置值: {c.pre_value}")
        print(f"  生成条件:\n  {condition}")

    # 测试必填
    mandatory_checks = [c for c in checks if not c.is_conditional]
    print("\n\n=== 必填 - WHERE 子句生成示例 ===")
    for c in mandatory_checks[:2]:
        where_clause = build_check_where_clause(c, dm_field=c.report_field)
        print(f"\n勾稽: {c.check_code} - {c.check_name[:40]}...")
        print(f"  WHERE 子句:\n  {where_clause}")