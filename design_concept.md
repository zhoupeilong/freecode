# 概要设计文档（Version 0.1）

## 项目目标
实现 **STG 巡检脚本** 的全自动生成，逆向追溯 `DM → DW → STG`（必要时包含 `DWS`），定位报表字段为空（必填/条件必填）时对应的源数据记录，并输出固定的技术、业务、报送标识字段。

## 业务需求
| 编号 | 需求 |
|---|---|
| R1 | 仅针对报表字段为空（NULL/空字符串）进行检查，包含必填与条件必填。
| R2 | 逆向追溯路径 **DM → DW → STG**（如出现 DWS，则使用 **DM → DWS → DW → STG**）。
| R3 | 输出字段固定：`check_name, stg_table_name, stg_table_name_cn, stg_col_name, stg_col_name_cn, stg_col_value, stg_key, count_proj_code, count_proj_name, trust_manager, deal_manage, trust_manager_b, trust_manager_c, beit_dept, report_flag_tprt, report_flag_east5`。
| R4 | 生成的 SQL 按 100 条/文件、每 100 条放入子文件夹 `SUCxxxx_SUCxxxx`，文件名 `SUCxxxx.sql`（5 位递增）。
| R5 | 每条 SQL 前加入 `-- 检查编号: <check_code>` 注释。
| R6 | 生成 `generation_log.txt` 记录映射缺失、条件构建、文件写入等信息。

## 输入材料
- `report_check_list.xlsx`（报表勾稽代码、是否必填、前置表/字段/值）
- `etl_code_list/**/*.sql`（ETL 清洗脚本，提供层级映射）
- （`conditional_logic.tsv` 已不再使用）

## 交付物
- `./output_stg_file/` 目录，包含若干子文件夹（如 `SUC0001_SUC0100`）与相应的 `SUCxxxx.sql` 文件。
- `generation_log.txt`（日志）
- 概要设计、详细设计 markdown 文档（本文件即概设文档）。
