"""
cleanup_sqlupdate_log.py - URP_SQLUPDATE_LOG表历史数据清理脚本

功能：
- 清理URP_SQLUPDATE_LOG表指定日期以前的历史数据
- 支持通过--days参数传入天数
- 兼容Oracle、达梦、OceanBase三种数据库

使用方式：
    python cleanup_sqlupdate_log.py --days 30
    python cleanup_sqlupdate_log.py --days 90 --db-type oracle
"""

import argparse
import sys
from datetime import datetime, timedelta


def generate_cleanup_sql(days: int, db_type: str = 'oracle') -> str:
    """
    生成清理URP_SQLUPDATE_LOG表的SQL语句

    Args:
        days: 保留天数，即删除days天以前的数据
        db_type: 数据库类型 (oracle/dm/oceanbase)

    Returns:
        生成的SQL语句
    """
    if days <= 0:
        raise ValueError("天数必须大于0")

    # 根据数据库类型生成不同的SQL
    if db_type.lower() == 'oracle':
        # Oracle: 使用SYSDATE - numtodsinterval
        sql = f"""-- ============================================================
-- URP_SQLUPDATE_LOG 表历史数据清理脚本
-- 清理 {days} 天以前的历史数据
-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- 数据库类型: Oracle
-- ============================================================

-- 1. 查看将删除的数据量（执行前先确认）
SELECT COUNT(*) AS DELETE_COUNT
FROM URP_SQLUPDATE_LOG
WHERE CREATE_TIME < SYSDATE - {days};

-- 2. 执行清理
DELETE FROM URP_SQLUPDATE_LOG
WHERE CREATE_TIME < SYSDATE - {days};

-- 3. 提交事务
COMMIT;

-- 4. 查看清理后的表记录数
SELECT COUNT(*) AS REMAIN_COUNT FROM URP_SQLUPDATE_LOG;
"""
    elif db_type.lower() == 'dm':
        # 达梦: 使用SYSDATE - 整数（达梦也支持）
        sql = f"""-- ============================================================
-- URP_SQLUPDATE_LOG 表历史数据清理脚本
-- 清理 {days} 天以前的历史数据
-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- 数据库类型: 达梦(DM)
-- ============================================================

-- 1. 查看将删除的数据量（执行前先确认）
SELECT COUNT(*) AS DELETE_COUNT
FROM URP_SQLUPDATE_LOG
WHERE CREATE_TIME < SYSDATE - {days};

-- 2. 执行清理
DELETE FROM URP_SQLUPDATE_LOG
WHERE CREATE_TIME < SYSDATE - {days};

-- 3. 提交事务
COMMIT;

-- 4. 查看清理后的表记录数
SELECT COUNT(*) AS REMAIN_COUNT FROM URP_SQLUPDATE_LOG;
"""
    elif db_type.lower() == 'oceanbase':
        # OceanBase (MySQL模式): 使用DATE_SUB(NOW(), INTERVAL)
        sql = f"""-- ============================================================
-- URP_SQLUPDATE_LOG 表历史数据清理脚本
-- 清理 {days} 天以前的历史数据
-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- 数据库类型: OceanBase (MySQL模式)
-- ============================================================

-- 1. 查看将删除的数据量（执行前先确认）
SELECT COUNT(*) AS DELETE_COUNT
FROM URP_SQLUPDATE_LOG
WHERE CREATE_TIME < DATE_SUB(NOW(), INTERVAL {days} DAY);

-- 2. 执行清理
DELETE FROM URP_SQLUPDATE_LOG
WHERE CREATE_TIME < DATE_SUB(NOW(), INTERVAL {days} DAY);

-- 3. 提交事务
COMMIT;

-- 4. 查看清理后的表记录数
SELECT COUNT(*) AS REMAIN_COUNT FROM URP_SQLUPDATE_LOG;
"""
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}，支持的类型: oracle, dm, oceanbase")

    return sql


def generate_date_based_sql(cutoff_date: str, db_type: str = 'oracle') -> str:
    """
    根据指定日期生成清理SQL

    Args:
        cutoff_date: 截止日期，格式 YYYY-MM-DD
        db_type: 数据库类型

    Returns:
        生成的SQL语句
    """
    # 验证日期格式
    try:
        datetime.strptime(cutoff_date, '%Y-%m-%d')
    except ValueError:
        raise ValueError("日期格式错误，应为 YYYY-MM-DD")

    if db_type.lower() == 'oracle':
        sql = f"""-- ============================================================
-- URP_SQLUPDATE_LOG 表历史数据清理脚本
-- 清理 {cutoff_date} 以前的历史数据
-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- 数据库类型: Oracle
-- ============================================================

-- 1. 查看将删除的数据量（执行前先确认）
SELECT COUNT(*) AS DELETE_COUNT
FROM URP_SQLUPDATE_LOG
WHERE CREATE_TIME < TO_DATE('{cutoff_date}', 'YYYY-MM-DD');

-- 2. 执行清理
DELETE FROM URP_SQLUPDATE_LOG
WHERE CREATE_TIME < TO_DATE('{cutoff_date}', 'YYYY-MM-DD');

-- 3. 提交事务
COMMIT;

-- 4. 查看清理后的表记录数
SELECT COUNT(*) AS REMAIN_COUNT FROM URP_SQLUPDATE_LOG;
"""
    elif db_type.lower() == 'dm':
        sql = f"""-- ============================================================
-- URP_SQLUPDATE_LOG 表历史数据清理脚本
-- 清理 {cutoff_date} 以前的历史数据
-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- 数据库类型: 达梦(DM)
-- ============================================================

-- 1. 查看将删除的数据量（执行前先确认）
SELECT COUNT(*) AS DELETE_COUNT
FROM URP_SQLUPDATE_LOG
WHERE CREATE_TIME < TO_DATE('{cutoff_date}', 'YYYY-MM-DD');

-- 2. 执行清理
DELETE FROM URP_SQLUPDATE_LOG
WHERE CREATE_TIME < TO_DATE('{cutoff_date}', 'YYYY-MM-DD');

-- 3. 提交事务
COMMIT;

-- 4. 查看清理后的表记录数
SELECT COUNT(*) AS REMAIN_COUNT FROM URP_SQLUPDATE_LOG;
"""
    elif db_type.lower() == 'oceanbase':
        sql = f"""-- ============================================================
-- URP_SQLUPDATE_LOG 表历史数据清理脚本
-- 清理 {cutoff_date} 以前的历史数据
-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- 数据库类型: OceanBase (MySQL模式)
-- ============================================================

-- 1. 查看将删除的数据量（执行前先确认）
SELECT COUNT(*) AS DELETE_COUNT
FROM URP_SQLUPDATE_LOG
WHERE CREATE_TIME < '{cutoff_date}';

-- 2. 执行清理
DELETE FROM URP_SQLUPDATE_LOG
WHERE CREATE_TIME < '{cutoff_date}';

-- 3. 提交事务
COMMIT;

-- 4. 查看清理后的表记录数
SELECT COUNT(*) AS REMAIN_COUNT FROM URP_SQLUPDATE_LOG;
"""
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}，支持的类型: oracle, dm, oceanbase")

    return sql


def main():
    parser = argparse.ArgumentParser(
        description='URP_SQLUPDATE_LOG表历史数据清理脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python cleanup_sqlupdate_log.py --days 30
  python cleanup_sqlupdate_log.py --days 90 --db-type oracle
  python cleanup_sqlupdate_log.py --date 2026-01-01
  python cleanup_sqlupdate_log.py --days 30 --output cleanup_30days.sql
        """
    )

    parser.add_argument(
        '--days',
        type=int,
        help='保留天数，删除该天数以前的数据（如30表示删除30天前的数据）'
    )

    parser.add_argument(
        '--date',
        type=str,
        help='指定截止日期，格式YYYY-MM-DD，删除该日期以前的数据'
    )

    parser.add_argument(
        '--db-type',
        type=str,
        choices=['oracle', 'dm', 'oceanbase'],
        default='oracle',
        help='数据库类型 (默认: oracle)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='输出SQL文件路径（默认输出到控制台）'
    )

    args = parser.parse_args()

    # 参数校验
    if args.days is None and args.date is None:
        parser.error("必须指定 --days 或 --date 参数")

    if args.days is not None and args.date is not None:
        parser.error("不能同时指定 --days 和 --date 参数")

    # 生成SQL
    if args.days is not None:
        sql = generate_cleanup_sql(args.days, args.db_type)
    else:
        sql = generate_date_based_sql(args.date, args.db_type)

    # 输出
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(sql)
        print(f"SQL脚本已生成: {args.output}")
    else:
        print(sql)


if __name__ == '__main__':
    main()