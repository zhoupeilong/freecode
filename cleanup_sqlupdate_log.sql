-- ============================================================
-- URP_SQLUPDATE_LOG 表历史数据清理脚本
-- 功能：清理指定日期以前的历史数据
-- 支持：Oracle、达梦、OceanBase
-- ============================================================

-- ************************************************************
-- 参数说明：
--   days: 保留天数，例如输入30表示删除30天以前的数据
--   请根据实际情况修改下面的参数值
-- ************************************************************

-- 【请修改此参数】保留天数（天）
DEFINE DAYS_TO_KEEP = 30;

-- ============================================================
-- Oracle/达梦 版本
-- ============================================================
-- 1. 查看将删除的数据量（执行前先确认）
-- SELECT COUNT(*) AS DELETE_COUNT
-- FROM URP_SQLUPDATE_LOG
-- WHERE CREATE_TIME < SYSDATE - &DAYS_TO_KEEP;

-- 2. 执行清理
-- DELETE FROM URP_SQLUPDATE_LOG
-- WHERE CREATE_TIME < SYSDATE - &DAYS_TO_KEEP;

-- 3. 提交事务
-- COMMIT;

-- ============================================================
-- OceanBase (MySQL模式) 版本
-- ============================================================
-- 1. 查看将删除的数据量（执行前先确认）
-- SELECT COUNT(*) AS DELETE_COUNT
-- FROM URP_SQLUPDATE_LOG
-- WHERE CREATE_TIME < DATE_SUB(NOW(), INTERVAL &DAYS_TO_KEEP DAY);

-- 2. 执行清理
-- DELETE FROM URP_SQLUPDATE_LOG
-- WHERE CREATE_TIME < DATE_SUB(NOW(), INTERVAL &DAYS_TO_KEEP DAY);

-- 3. 提交事务
-- COMMIT;

-- ============================================================
-- 使用示例（根据实际数据库选择对应版本）
-- ============================================================
-- Oracle:
--   DEFINE DAYS_TO_KEEP = 30;
--   DELETE FROM URP_SQLUPDATE_LOG WHERE CREATE_TIME < SYSDATE - &DAYS_TO_KEEP;
--   COMMIT;

-- 达梦:
--   DEFINE DAYS_TO_KEEP = 30;
--   DELETE FROM URP_SQLUPDATE_LOG WHERE CREATE_TIME < SYSDATE - &DAYS_TO_KEEP;
--   COMMIT;

-- OceanBase:
--   SET @DAYS_TO_KEEP = 30;
--   DELETE FROM URP_SQLUPDATE_LOG WHERE CREATE_TIME < DATE_SUB(NOW(), INTERVAL @DAYS_TO_KEEP DAY);
--   COMMIT;