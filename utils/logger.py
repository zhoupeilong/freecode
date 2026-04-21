"""
logger.py - 统一日志输出模块

输出格式：
[时间戳] 级别 - 消息

级别：
- INFO: 常规步骤记录
- WARN: 映射缺失、条件解析错误、参数占位符等
- ERROR: 严重错误
"""

import os
from datetime import datetime
from typing import Optional


class Logger:
    """生成过程日志记录器"""

    # 预定义 WARN 类型
    WARN_PRIORITY_UNRESOLVED = "WARN_PRIORITY_UNRESOLVED"
    WARN_PARAM_MISMATCH = "WARN_PARAM_MISMATCH"
    WARN_DEPENDENCY_UNMATCHED = "WARN_DEPENDENCY_UNMATCHED"
    WARN_MULTI_SOURCE = "WARN_MULTI_SOURCE"
    WARN_PARAM_PLACEHOLDER = "WARN_PARAM_PLACEHOLDER"
    WARN_DUP_TABLE_JOIN = "WARN_DUP_TABLE_JOIN"
    WARN_WHERE_CONDITION = "WARN_WHERE_CONDITION"
    WARN_MAPPING_MISSING = "WARN_MAPPING_MISSING"
    WARN_CONDITION_PARSE = "WARN_CONDITION_PARSE"

    def __init__(self, log_path: str):
        """
        初始化日志记录器。

        Args:
            log_path: 日志文件路径
        """
        self.log_path = log_path
        self._ensure_dir()
        # 清空或创建日志文件
        with open(self.log_path, 'w', encoding='utf-8') as f:
            f.write(f"=== STG 巡检脚本生成日志 ===\n")
            f.write(f"=== 创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")

    def _ensure_dir(self):
        """确保日志文件目录存在"""
        dir_path = os.path.dirname(self.log_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

    def _write(self, level: str, message: str):
        """写入日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{timestamp}] {level} - {message}\n"
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(line)

    def info(self, message: str):
        """记录 INFO 级别日志"""
        self._write("INFO", message)

    def warn(self, message: str, warn_type: Optional[str] = None):
        """
        记录 WARN 级别日志

        Args:
            message: 警告消息
            warn_type: 预定义警告类型（可选）
        """
        if warn_type:
            self._write(f"WARN [{warn_type}]", message)
        else:
            self._write("WARN", message)

    def error(self, message: str):
        """记录 ERROR 级别日志"""
        self._write("ERROR", message)

    def section(self, title: str):
        """写入分节标题"""
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"  {title}\n")
            f.write(f"{'='*60}\n")

    def summary(self, total: int, mandatory: int, conditional: int,
                generated: int, warnings: int, errors: int):
        """写入摘要统计"""
        self.section("生成摘要")
        summary_text = (
            f"检查项总数: {total}\n"
            f"  必填: {mandatory}\n"
            f"  条件必填: {conditional}\n"
            f"生成 SQL 条数: {generated}\n"
            f"警告数: {warnings}\n"
            f"错误数: {errors}\n"
        )
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(summary_text)


if __name__ == "__main__":
    # 测试入口
    test_log = os.path.join(os.path.dirname(__file__), "..", "..", "output_stg_file", "generation_log.txt")
    test_log = os.path.abspath(test_log)

    logger = Logger(test_log)
    logger.section("测试日志")
    logger.info("这是一条测试日志")
    logger.warn("映射缺失：DM表 DM_CTRC_XSFSXXZBB 未找到对应的DW表", Logger.WARN_MAPPING_MISSING)
    logger.warn("同一DW表出现多次LEFT JOIN: DW_D_FUND_AGENCY_INFO", Logger.WARN_DUP_TABLE_JOIN)
    logger.error("严重错误：无法解析SQL模板")

    print(f"日志文件已写入: {test_log}")