"""Test logger module"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from utils.logger import Logger

test_log = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'output_stg_file', 'test_generation_log.txt'))
logger = Logger(test_log)
logger.section("测试日志")
logger.info("这是一条测试日志")
logger.warn("映射缺失：DM表 DM_CTRC_XSFSXXZBB 未找到对应的DW表", Logger.WARN_MAPPING_MISSING)
logger.warn("同一DW表出现多次LEFT JOIN: DW_D_FUND_AGENCY_INFO", Logger.WARN_DUP_TABLE_JOIN)
logger.error("严重错误：无法解析SQL模板")
logger.summary(1746, 1328, 418, 1700, 5, 0)

print('日志文件已写入: {}'.format(test_log))

# 验证文件内容
with open(test_log, 'r', encoding='utf-8') as f:
    content = f.read()
    print('--- 日志内容 (前500字符) ---')
    print(content[:500])