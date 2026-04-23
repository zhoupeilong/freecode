# 详细设计文档（Version 1.0）

## 1 背景
每月月初报送时报表勾稽问题多时间紧，实施同学需要加班加点处理数据问题，比较痛苦。按经验至少一半的问题属于上游系统数据没及时维护，我们希望能提前发现并处置这些问题，减少月初报送的压力。

## 2 目标
STG 数据巡检的目标是自动找到报送数据缺失字段对应的上游接口字段，方便上游系统批量补录缺数据，提高报送效率。

## 3 交付内容
针对定期报送和 EAST5 报送生成所有必填或者条件必填勾稽的 STG 巡检代码。一次性完整交付所有 STG 巡检脚本几乎不太可能，需要分多个阶段交付，并且能够验证交付成果。本章节设计了一套分阶段交付与验证流程机制。

### 3.1 阶段划分

由于 STG 巡检代码基于 ETL 代码血缘自动生成，困难在于 AI 对代码血缘解析的准确程度，因此按"匹配率"和"准确率"两项核心指标划分四个阶段：

| 阶段 | 版本 | 匹配率 | 准确率 | 核心任务 |
|------|------|--------|--------|----------|
| 第一阶段 | v1.0 | ≥60% | ≥40% | 基于现有依赖和解析能力生成初始版本 |
| 第二阶段 | v2.0 | ≥80% | ≥60% | 补充缺失依赖后重新生成 |
| 第三阶段 | v3.0 | ≥90% | ≥80% | 深度解析所有分支逻辑（参数控制、优先级判断等） |
| 第四阶段 | v4.0 | ≥95% | ≥90% | 深度解析所有空值表现（字段为空、行记录不存在） |

#### 3.1.1 关键词定义

| 术语 | 定义 |
|------|------|
| **匹配率** | 报表勾稽检出问题，STG 巡检脚本也能检出问题。巡检检出条数与报表勾稽检出条数可能不同。计算公式：匹配率 = (巡检检出且报表也检出的条数) / (报表勾稽检出的总条数) |
| **准确率** | 报表勾稽检出问题，STG 巡检脚本也能检出问题，且检出条数相同。计算公式：准确率 = (巡检检出且报表也检出的条数) / (巡检检出的总条数) |
| **分支逻辑** | 字段取值受参数控制、优先级判断等影响，存在多个取值分支。遗漏分支会导致巡检遗漏。 |
| **空值表现** | 字段为空的原因包括：(1) 字段本身为空；(2) LEFT JOIN 关联条件不满足导致行记录不存在。 |

#### 3.1.2 版本差异影响

> **重要客观因素**：血缘解析脚本基于公司开发版本生成，每月发布一个版本。但客户现场可能不会每次版本都升级，导致：
> - **生成时点**：使用公司某版本（参考版本）生成的 STG 巡检脚本
> - **验证时点**：客户现场运行的是另一个版本（目标版本）
> - **版本差异**：两个版本的 ETL 代码可能存在差异（新增字段、修改逻辑、参数变更等），直接影响巡检的匹配率和准确率

**版本差异的处理策略**：

| 场景 | 处理方式 |
|------|----------|
| 参考版本 = 目标版本 | 理想情况，解析结果与现场完全匹配 |
| 参考版本 > 目标版本 | 生成版本新于现场，巡检可能检出现场不存在的新字段问题，匹配率下降 |
| 参考版本 < 目标版本 | 生成版本老于现场，现场有新逻辑未覆盖，可能遗漏问题 |

**版本差异的合理损耗假设**：

由于现场版本升级需要较长的验证周期，无法推动现场及时升级，因此假设 **约 10% 的漏检是由于版本差异导致的客观损耗**，而非解析能力不足。

这意味着在计算匹配率和准确率时：
- 阶段目标（60%、80%等）已经内嵌了版本差异的合理损耗
- 例如 v1.0 目标匹配率 60%，其中约 10% 是版本差异导致的不可控损耗，剩余 50% 反映解析能力
- 推进阶段时，优先解决版本差异之外的能力问题

**版本信息记录**：
- 每次生成巡检脚本时，必须记录以下版本信息：
  - 参考版本号（如 `CTRC_ETL_202604`）
  - 生成时间（精确到秒）
  - 涉及血缘解析的 ETL 代码文件清单及版本
- 验证时需同步记录客户现场的实际版本号
- 比对结果需附加版本差异说明

### 3.2 验证标准

每阶段交付后，需在以下四家客户现场进行验证：

- 昆仑信托
- 国通信托
- 建元信托
- 兴业信托

**阶段成功判定规则**：至少有两家客户的匹配率和准确率同时达到阶段标准，方视为该阶段交付成功。

**示例**（第一阶段）：
- 昆仑信托：匹配率 65%、准确率 42% ✅
- 国通信托：匹配率 58%、准确率 38% ❌（匹配率未达标）
- 建元信托：匹配率 62%、准确率 41% ✅
- 兴业信托：匹配率 55%、准确率 35% ❌

结果：**通过**（昆仑信托和建元信托均达标）

### 3.3 验证流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           分阶段交付与验证流程                               │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
     │ 阶段N   │───▶│ 生成巡检 │───▶│ 部署到   │───▶│ 现场执行 │
     │ 目标设定 │    │ SQL脚本  │    │ 测试环境 │    │ 巡检     │
     └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                     │
                                                     ▼
                    ┌──────────────────────────────────────────┐
                    │          四家客户现场巡检                │
                    │  昆仑信托 / 国通信托 / 建元信托 / 兴业信托 │
                    └──────────────────────────────────────────┘
                                                     │
                                                     ▼
     ┌──────────────────────────────────────────────────────────┐
     │                    结果比对与分析                         │
     │  1. 导出报表勾稽问题清单                                  │
     │  2. 导出 STG 巡检问题清单                                  │
     │  3. 按勾稽代码逐条匹配，计算匹配率和准确率                 │
     │  4. 分析未匹配原因（缺失分支？空值表现？映射错误？）        │
     └──────────────────────────────────────────────────────────┘
                                                     │
                        ┌────────────────────────────┴────────────────────┐
                        │                                                 │
                        ▼                                                 ▼
               ┌──────────────────┐                              ┌──────────────────┐
               │ 至少2家达标      │                              │ 不足2家达标      │
               │ 阶段交付成功     │                              │ 进入下一阶段     │
               │ 进入下一阶段     │                              │ 补充依赖/优化解析│
               └──────────────────┘                              └──────────────────┘
```

### 3.4 数据比对方法

#### 3.4.1 比对输入

| 数据源 | 内容 | 关键字段 |
|--------|------|----------|
| 报表勾稽输出 | 各勾稽代码检出的问题项目清单 | check_code, proj_code, 异常描述 |
| STG 巡检输出 | 各 SUC 检出的问题项目清单 | check_code, proj_code, 异常描述 |

#### 3.4.2 比对步骤

1. **按勾稽代码分组**：分别汇总报表勾稽和 STG 巡检的检出项目列表
2. **逐条匹配**：对同一勾稽代码，对比报表检出的项目与巡检检出的项目
3. **计算指标**：
   - 匹配条数 = 报表检出 ∩ 巡检检出
   - 匹配率 = 匹配条数 / 报表检出总数
   - 准确率 = 匹配条数 / 巡检检出总数
4. **汇总四家结果**：按客户分别汇总，判定是否达标

#### 3.4.3 比对输出

| 字段 | 说明 |
|------|------|
| 阶段 | v1.0 / v2.0 / v3.0 / v4.0 |
| 客户 | 昆仑信托 / 国通信托 / 建元信托 / 兴业信托 |
| 勾稽代码 | 报表勾稽代码 |
| 报表检出数 | 报表勾稽检出的问题项目数 |
| 巡检检出数 | STG 巡检检出的问题项目数 |
| 匹配数 | 双方都检出的项目数 |
| 匹配率 | 匹配数 / 报表检出数 |
| 准确率 | 匹配数 / 巡检检出数 |
| 是否达标 | 匹配率≥阶段目标 AND 准确率≥阶段目标 |

### 3.5 阶段推进规则

| 当前阶段 | 达标情况 | 下一阶段动作 |
|----------|----------|--------------|
| v1.0 | ≥2家达标 | 推进至 v2.0，补充缺失的依赖（参数配置、血缘映射等） |
| v1.0 | <2家达标 | 诊断未达标原因，补充依赖后仍按 v2.0 目标重新生成 |
| v2.0 | ≥2家达标 | 推进至 v3.0，深度解析分支逻辑 |
| v2.0 | <2家达标 | 补充分支逻辑后仍按 v3.0 目标重新生成 |
| v3.0 | ≥2家达标 | 推进至 v4.0，深度解析空值表现 |
| v3.0 | <2家达标 | 补充空值表现分析后仍按 v4.0 目标重新生成 |
| v4.0 | ≥2家达标 | 交付完成，持续运维优化 |
| v4.0 | <2家达标 | 记录遗留问题，纳入后续迭代计划 |

### 3.6 遗留问题追踪

每次阶段验证后，需记录未匹配问题的根因分类：

| 根因分类 | 说明 | 影响阶段 |
|----------|------|----------|
| 依赖缺失 | 缺少参数配置、血缘映射等输入数据 | v1.0 / v2.0 |
| 分支遗漏 | 未解析字段的取值分支（如参数控制、优先级） | v2.0 / v3.0 |
| 空值漏检 | 未考虑 LEFT JOIN 关联不满足导致的行记录不存在 | v3.0 / v4.0 |
| 映射错误 | 字段映射关系错误（STG 表/字段、JOIN 条件） | 全阶段 |
| 解析失败 | ETL 代码结构复杂，解析脚本未能正确处理 | 全阶段 |

遗留问题需更新至 `generation_log.txt` 并纳入下一阶段的优化目标。

## 4 项目结构（生成代码所在的工作区）
```
/output_stg_file/
    ├─ SUC0001_SUC0100/
    │     ├─ SUC0001.sql
    │     ├─ SUC0002.sql
    │     └─ … (至 SUC0100.sql)
    ├─ SUC0101_SUC0200/
    │     └─ …
    ├─ check_suc_mapping.md      ← 勾稽代码↔SUC编号映射表(MD)
    ├─ check_suc_mapping.csv      ← 勾稽代码↔SUC编号映射表(CSV)
    └─ generation_log.txt          ← 生成过程日志
urp_dm_field_mapping.xlsx          ← URP报表字段↔DM指标表字段映射（从ETL代码提取）
param_field_mapping.xlsx           ← DM字段↔参数控制映射（v0.7新增，从ETL清洗代码提取）
scripts/
    ├─ generate_stg_checks.py      ← 主执行入口（v0.7新增参数展开逻辑）
    ├─ parse_urp_dm_mapping.py     ← URP-DM字段映射提取脚本
    ├─ parse_etl_params.py          ← ETL参数依赖提取脚本（v0.7新增）
    ├─ parsers/
    │     ├─ report_check_parser.py   # 读取 report_check_list.xlsx
    │     ├─ etl_mapper.py            # 解析巡检列映射，构建层级映射
    │     ├─ param_config_loader.py   # 加载参数配置、分类、展开（v0.7新增）
    │     └─ condition_builder.py     # 根据前置条件生成 extra_condition
    └─ utils/
          ├─ logger.py                # 统一日志输出
          └─ file_writer.py           # 批量写文件、创建子文件夹
```

## 5 核心类/函数概览
| 模块 | 类/函数 | 说明 |
|------|--------|------|
| **report_check_parser** | `ReportCheckInfo` | `check_code, check_name, is_mandatory (必填/条件必填), pre_table, pre_column, pre_value` |
|  | `load_report_checks(xlsx_path) -> List[ReportCheckInfo]` | 读取 `report_check_list.xlsx`，返回列表。 |
| **etl_mapper** | `ETLMapping` | 保存 **巡检列映射（主）** + **DM字段映射（补充）** + **STG→DW关联体系（SQL模板）** + **STG主键**。`inspection_map: Dict[str, List[InspectionRow]]` 为字段别名→巡检行映射；`dm_field_map: Dict[str, List[DMFieldMapping]]` 为TAB_NAME.COL→DM字段映射。**v0.6变化**：`dm_field_map` 中的DM表→DM字段映射现在可以优先从 `urp_dm_field_mapping.xlsx` 查找，而无需再遍历 `etl_code_list/` 目录解析 SQL。 |
|  | `InspectionRow` | 巡检列中的一行数据，含 `dm_table, dm_field, stg_table, stg_field, check_expression, sql_template, is_from_dm_supplement` 等关键字段。`is_from_dm_supplement=True` 表示该行来自DM字段映射补充（非巡检列精确匹配）。v0.5起：DM补充行有借用模板时使用`_fill_sql_template()`+字段替换，保留JOIN和数据源过滤；无模板时仍使用通用拼装。 |
|  | `DMFieldMapping` | DM字段映射sheet中的一行：`tab_name, tab_col → ref_tab, ref_col, source_table, source_col` |
|  | `find_mapping_for_check(info, mapping)` | 匹配策略：①精确匹配report_table.report_field→巡检列字段别名；②大小写不敏感；③DM字段映射补充（标记is_from_dm_supplement=True）。**已移除"同报表名取第一行"策略**（v0.4修正：会导致字段错配）。 |
| **param_config_loader** | `ParamDefinition` | 参数定义数据类：`param_code, param_name, param_values, default_value, category(business/personalization)` |
|  | `ParamFieldMapping` | 字段→参数映射数据类：`dm_table, dm_field, param_code, case_when_expr, ref_source` |
|  | `load_param_config(xlsx_path)` | 加载 `code_param_list.xlsx`，返回 `{param_code: ParamDefinition}`（v0.7新增） |
|  | `classify_param(param)` | 根据参数值数量和内容特征，分类为 `business`（按值展开）或 `personalization`（保留URP_PARAM_CONFIG查询）（v0.7新增） |
|  | `expand_business_params(params, business_codes)` | 计算业务参数笛卡尔积，返回 `[{param_code: value, ...}, ...]`（v0.7新增） |
| **parse_etl_params** | — | 从 `etl_code_list/` 的ETL清洗代码解析 `#[PARAM]` 占位符和 CASE WHEN 结构，提取 DM字段→参数 的依赖关系，输出 `param_field_mapping.xlsx`（v0.7新增脚本） |
| **condition_builder** | `build_extra_condition(info: ReportCheckInfo) -> str` | 将 **前置表/字段/值** 转为 SQL 条件，例如：`AND EXISTS (SELECT 1 FROM URP3_TUSP.DM_CTRC_CPTZZBB p WHERE p.SFLSXT = '1' AND p.<主键> = dm.<主键>)`。 |
| **file_writer** | `BatchWriter(output_root, batch_size=100)` | 负责 **创建子文件夹**（`SUC0001_SUC0100`），并把每 `batch_size` 条 SQL 写入 `SUCxxxx.sql`。 |
| **logger** | `log(message, level='INFO')` | 将关键步骤、映射缺失、条件解析错误写入 `generation_log.txt`。 |
| **generate_stg_checks.py** | `main()` | 业务流程调度：读取 Excel → 解析 ETL → 生成每条检查 SQL → 批量写文件 → 记录日志。 |

## 6 关键算法细节
### 6.1 报表字段 → DM表字段的映射查找（v0.6 更新）

> **重要变化（v0.6）**：已从 `urp_code_list/` 的 ETL SQL 脚本中提取了完整的 URP报表字段↔DM指标表字段映射，保存为 `urp_dm_field_mapping.xlsx`。后续在报表勾稽代码查找对应的DM表和DM字段时，**直接在此 xlsx 中查找即可**，无需再解析 `etl_code_list/` 目录下的 SQL 文件。

#### 6.1.1 映射查找优先级（当前）

当需要为一条报表勾稽代码确定"该报表字段对应哪个DM表的哪个字段"时，查找顺序为：

1. **巡检列 sheet（主映射源）**：通过 `report_table.report_field` 精确匹配 `my_poor_solution.xlsx` 的"巡检列" sheet
2. **`urp_dm_field_mapping.xlsx`（新映射源）**：从 ETL SQL 脚本提取的 URP报表字段↔DM指标表字段映射，覆盖 95+ 个URP表、1593 条映射
3. **DM字段映射 sheet（补充）**：`my_poor_solution.xlsx` 的"关联到DM字段映射" sheet（仅在以上两个来源都未找到时使用）
4. **占位 SQL**：以上均未找到时，生成 `-- !!! 未自动生成 !!!` 占位 SQL

#### 6.1.2 `urp_dm_field_mapping.xlsx` 结构

| 字段 | 说明 | 示例 |
|------|------|------|
| ID | `URP_TABLE_NAME.URP_COLUMN_NAME` | `URP_TPRT_CPJBXX.XTDJXTCPBM` |
| URP_TABLE_NAME | URP报表表名 | `URP_TPRT_CPJBXX` |
| URP_COLUMN_NAME | URP报表字段名 | `XTDJXTCPBM` |
| DM_TABLE_NAME | DM指标表名 | `DM_CTRC_CPJBXXZBB` |
| DM_COLUMN_NAME | DM指标表字段名 | `XTDJXTCPBM`（同名）或 `SHAREHOLDER_TYPE`（异名） |
| DM_EXPRESSION | DM字段表达式原文 | `t.shareholder_type gdlx` |
| 备注 | 映射类型 | 同名映射 / 异名映射 / 系统变量 |

统计：1593 条映射，1107 条同名映射（URP字段=DM字段），424 条异名映射，62 条系统变量。覆盖 98 个目标 URP 表中的 95 个（96.9%）。

#### 6.1.3 原有 ETL 代码解析（保留但已非主要查找路径）

```regex
# 匹配 JOIN 语句并捕获表名、别名、ON 条件
(?i)join\s+(?<table>\w+(?:\.\w+)?)(?:\s+as\s+(?<alias>\w+))?\s+on\s+(?<on>[^ \n]+)
```
- **DM → DW**：表名前缀 `dw_` 或 `dw`（视实际命名而定），对应的 `ON` 条件会包含 **DM 主键**。
- **DW → STG**：表名前缀 `t2_`（STG）或 `stg_`，同理抽取 `ON` 条件。

> **注意**：ETL 代码解析仍用于提取 SQL 模板（JOIN 条件、data_source 过滤、参数占位符等），但**不再作为报表字段→DM表字段映射的主要查找来源**。此角色已由 `urp_dm_field_mapping.xlsx` 替代。

### 6.2 前置条件 => `extra_condition`
| 前置表 | 前置字段 | 前置值 | 生成的 `extra_condition` 示例 |
|--------|----------|--------|--------------------------------|
| `URP3_TUSP.DM_CTRC_CPTZZBB` | `SFLSXT` | `'1'` | `AND EXISTS (SELECT 1 FROM URP3_TUSP.DM_CTRC_CPTZZBB p WHERE p.SFLSXT = '1' AND p.<主键> = dm.<主键>)` |
| `URP3_TUSP.DM_PROJ_INFO` | `IS_GREEN_TRUST` | `'Y'` | `AND p.IS_GREEN_TRUST = 'Y'`（若已在主查询中 JOIN 前置表，则直接 `AND p.IS_GREEN_TRUST = 'Y'`） |

> **实现思路**：先检查 **前置表** 是否已经在 **ETL 映射链** 中出现（即在 `DW → STG` 关联里已经 `JOIN` 了前置表），若已出现则只需在 `WHERE` 中追加 `AND 前置字段 = 前置值`；否则使用 `EXISTS` 子查询加入。

### 6.3 生成单条巡检 SQL（模板）
```sql
-- 检查编号: {check_code}
SELECT '{check_name}' AS check_name,               -- 勾稽名称
       '{stg_table}' AS stg_table_name,            -- STG 表名
       '{stg_table_cn}' AS stg_table_name_cn,      -- STG 中文名（可留空）
       '{stg_column}' AS stg_col_name,             -- STG 列名
       '{stg_column_cn}' AS stg_col_name_cn,       -- STG 列中文名（可留空）
       {stg_column} AS stg_col_value,              -- 列取值
       '{stg_key}' AS stg_key,                     -- 业务主键（拼接项目编号、名称等）
       dm.count_proj_code,
       dm.count_proj_name,
       fn_company_dict(dm.trust_manager, '1') AS trust_manager,
       fn_company_dict(dm.deal_manage, '1') AS deal_manage,
       fn_company_dict(dm.trust_manager_b, '1') AS trust_manager_b,
       fn_company_dict(dm.trust_manager_c, '1') AS trust_manager_c,
       fn_company_dict(dm.beit_dept, '2') AS beit_dept,
       dm.report_flag_tprt,
       dm.report_flag_east5
FROM {dm_table} dm
{join_dw_clause}
{join_stg_clause}
WHERE dm.{target_column} IS NULL            -- 必填
{extra_condition};
```
- `{join_dw_clause}` 与 `{join_stg_clause}` 根据 **ETL 映射** 自动填充。
- 若 **前置条件** 为 `条件必填`，`extra_condition` 包含上述 `AND …` 或 `EXISTS` 语句。
- 所有 **业务辅助字段**（`trust_manager`、`deal_manage`、`beit_dept`）在 **项目相关报表** 中有值；若报表不关联项目，则在 SQL 中直接写 `NULL AS trust_manager` 等，**生成器会自动检测** `pre_table` 是否为项目表来决定填充。

## 7 生成过程日志（`generation_log.txt`）格式
```
[2026-04-17 10:34:12] INFO  - 开始读取 report_check_list.xlsx (共 237 条记录)
[2026-04-17 10:34:18] INFO  - 解析 ETL 脚本，构建层级映射完成（DM→DW: 58，DW→STG: 61）
[2026-04-17 10:34:20] WARN  - 检测到 5 条 DM 字段未匹配到 DW 表，已记录至 log
[2026-04-17 10:34:22] INFO  - 开始生成巡检 SQL，批次大小 100 条，文件夹 SUC0001_SUC0100 创建
[2026-04-17 10:34:45] INFO  - 已写入文件 SUC0001.sql（第 1-100 条）
[2026-04-17 10:35:01] INFO  - 已写入文件 SUC0002.sql（第 101-200 条）
...
[2026-04-17 10:36:10] INFO  - 生成完成，输出文件位于 ./output_stg_file/
[2026-04-17 10:36:11] INFO  - 共生成 237 条检查 SQL，分布于 3 个子文件夹
```
- **WARN** 用于映射缺失或条件无法解析的情况，运维可直接查看并人工补齐。
- **INFO** 按步骤记录，便于排查。

## 8 实现路线（逐模块）
| 步骤 | 任务 | 负责模块 | 产出 |
|------|------|----------|------|
| **1** | 读取 `report_check_list.xlsx` | `report_check_parser` | `List[ReportCheckInfo]` |
| **2a** | 从 `my_poor_solution.xlsx` 巡检列 sheet 构建主映射 | `etl_mapper` | `InspectionMap` |
| **2b** | 从 `urp_dm_field_mapping.xlsx` 查找 URP→DM 字段映射（**v0.6新增，替代ETL代码遍历**） | `etl_mapper` | `DMFieldMap` 补充 |
| **2c** | 从 `my_poor_solution.xlsx` STG→DM映射 sheet 获取 SQL 模板 | `etl_mapper` | `STGDWMap` |
| **3** | 对每条 `ReportCheckInfo`：判断是否有前置表；依据映射生成 `dm → dw → stg` 路径 | `etl_mapper.field_origin` | `(dm, dw, stg, on_dm_dw, on_dw_stg)` |
| **4** | 生成 `extra_condition`（使用 `condition_builder`） | `condition_builder` | `str` |
| **5** | 按模板渲染单条 SQL，加入注释头部 | `generate_stg_checks.py`（模板渲染） | `SQL 文本` |
| **6** | 批量写入文件，创建子文件夹（每 100 条） | `file_writer.BatchWriter` | `./output_stg_file/SUCxxxx_SUCxxxx/*.sql` |
| **7** | 记录日志、缺失映射、异常 | `logger` | `generation_log.txt` |
| **8** | 完成后返回 **文件清单** 与 **日志摘要** | `generate_stg_checks.py` 主函数 | 控制台输出 + 文件路径 |

## 9 XSFS 实例验证：6 种取数场景的真实代码印证

### 9.1 XSFS 字段取数规则总结

XSFS（销售方式）是 `DM_CTRC_XSFSXXZBB` 表中字段，其取数由 **3 个系统参数** 和 **6 张 DW 表** 共同决定，完整涵盖了我们定义的 6 种取数场景。

#### 9.1.1 顶层参数控制（4 大分支）

| 顶层条件 | 参数值 | 含义 | 取数场景分类 |
|----------|--------|------|-------------|
| `#[TSIS_GXHCS] = 'GLXT'` | 管理系统 | 通用代销/直销判断 | **场景4（参数）+ 场景5（依赖）** |
| `#[TSIS_GXHCS] = 'AXXT'` | 建元信托个性化 | 客户定制逻辑 | **场景4（参数）+ 场景5（依赖）** |
| `#[TPRT_XSFSQSLJ] = '1'` | 销售方式取数逻辑=1 | 标准：渠道→代销模式→客户类型 | **场景3（优先级）+ 场景4（参数）+ 场景5（依赖）** |
| `#[TPRT_XSFSQSLJ] = '2'` | 销售方式取数逻辑=2 | 简化：按资金来源明细 | **场景4（参数）+ 场景5（依赖）** |

#### 9.1.2 各分支决策树

**分支1：#[TSIS_GXHCS] = 'GLXT'（管理系统）**
```
XSFS
├── 代销条件成立 (T2.CHANNEL_CODE IS NOT NULL AND nvl(T31.AGENCY_TYPE,'2')='2'
│   OR (T2.CHANNEL_CODE IS NULL AND T2.agency_code <> 'TTT'))
│   ├── 含"银行" (T31/T3.agency_name LIKE '%银行%')
│   │   ├── T5.CUST_TYPE = '1' -> '2' 银行代销（自然人）
│   │   └── T5.CUST_TYPE <> '1' -> '3' 银行代销（其他）
│   └── 不含"银行"（其他金融机构代销）
│       ├── T5.CUST_TYPE = '1' -> '4' 其他金融机构代销（自然人）
│       └── T5.CUST_TYPE <> '1' -> '5' 其他金融机构代销（其他）
└── 直销（代销条件不成立）
    ├── T5.CUST_TYPE = '1' -> '0' 自主营销（自然人）
    └── T5.CUST_TYPE <> '1' -> '1' 自主营销（其他）
```

**分支2：#[TSIS_GXHCS] = 'AXXT'（建元信托个性化）**
```
├── 直销条件 (agency_code='TTT' AND (channel_code IS NULL OR 特殊名称))
│   ├── T5.CUST_TYPE = '1' -> '0' 自主营销（自然人）
│   └── T5.CUST_TYPE <> '1' -> '1' 自主营销（其他）
└── 非直销
    ├── T5.CUST_TYPE = '1' -> '4' 其他金融机构代销（自然人）
    └── T5.CUST_TYPE <> '1' -> '5' 其他金融机构代销（其他）
```

**分支3：#[TPRT_XSFSQSLJ] = '1'（标准逻辑）**
```
├── 条件0: T2.AGENCY_CODE='TTT' AND TRIM(T2.CHANNEL_CODE) IS NULL → 直销
│   ├── T5.CUST_TYPE='1' -> '0'
│   └── T5.CUST_TYPE<>'1' -> '1'
├── 条件1: TRIM(T2.CHANNEL_CODE) IS NOT NULL → 按渠道判断（优先级取数）
│   ├── T31.EAST_FUND_AGENCY_MODE='0' → 直销 → '0'/'1'
│   ├── T31.EAST_FUND_AGENCY_MODE='1' → 银行代销 → '2'/'3'
│   └── T31.EAST_FUND_AGENCY_MODE IN ('2','3') → 其他金融机构代销 → '4'/'5'
└── 条件2: TRIM(T2.CHANNEL_CODE) IS NULL → 按销售商判断（优先级取数-降级）
    ├── T3.EAST_FUND_AGENCY_MODE='0' → 直销 → '0'/'1'
    ├── T3.EAST_FUND_AGENCY_MODE='1' → 银行代销 → '2'/'3'
    └── T3.EAST_FUND_AGENCY_MODE IN ('2','3') → 其他金融机构代销 → '4'/'5'
```

**分支4：#[TPRT_XSFSQSLJ] = '2'（简化逻辑）**
```
├── T2.CAPITAL_SOURCE_DETAIL IS NULL / ='18' → 自主营销
│   ├── T5.CUST_TYPE='1' → '0'
│   └── ELSE → '1'
├── T2.CAPITAL_SOURCE_DETAIL IN ('01','02','05','06','08','09','11','12','14','15','17','20','21') → '1'
├── T2.CAPITAL_SOURCE_DETAIL='03' → '3' 银行代销（其他）
├── T2.CAPITAL_SOURCE_DETAIL='04' → '2' 银行代销（自然人）
└── T2.CAPITAL_SOURCE_DETAIL IN ('07','10','13','16') → '4'/'5' 其他金融机构代销
    ├── T5.CUST_TYPE='1' → '4'
    └── ELSE → '5'
```

#### 9.1.3 涉及的 DW 表及其角色

| 别名 | DW 表名 | 角色 | 关键字段 | 对 STG 巡检的影响 |
|------|---------|------|---------|------------------|
| T2 | DW_D_COLL_CONTRACT | 募集合同 | AGENCY_CODE, CHANNEL_CODE, CAPITAL_SOURCE_DETAIL | LEFT JOIN，可能关联不到 |
| T3 | DW_D_FUND_AGENCY_INFO | 销售商信息（按销售商） | AGENCY_NAME, EAST_FUND_AGENCY_MODE | LEFT JOIN，用于渠道为空时的降级判断 |
| T31 | DW_D_FUND_AGENCY_INFO | 渠道信息（按渠道） | AGENCY_NAME, AGENCY_TYPE, EAST_FUND_AGENCY_MODE | LEFT JOIN，与 T3 同表不同关联条件 |
| T4 | DM_FA_METRIC_INFO | 前次权利分配标志 | BEFC_RIGHT_ASSN_FLAG | LEFT JOIN，仅用于 WHERE 过滤 |
| T5 | DW_D_CUST_INFO | 客户信息 | CUST_TYPE | LEFT JOIN，区分自然人/其他 |
| T6 | DM_COMM_COLL_CONTRACT_D_BAS | 合同基础 | CPTL_WEIGHT | LEFT JOIN，仅用于 WHERE 过滤 |

#### 9.1.4 取数场景归类

| 场景编号 | 在 XSFS 中的体现 | 对应详细设计中的 SourceRule 类型 |
|----------|-----------------|-------------------------------|
| **场景1（UNION ALL）** | 本例未出现，但 ETL 代码中 T1 子查询使用了 INNER JOIN 多表取数 | `source_type='union'` |
| **场景2（LEFT JOIN 丢失主键）** | T3、T31 均为 LEFT JOIN，当 channel_code 为空时 T31 关联不到，降级到 T3 | `source_type='left'` |
| **场景3（优先级取数）** | TPRT_XSFSQSLJ='1' 分支中：先看渠道非空（T31），再看渠道为空（T3） | `source_type='priority'` |
| **场景4（参数控制）** | #[TSIS_GXHCS]、#[TPRT_XSFSQSLJ] 决定走哪个大分支 | `source_type='param'` |
| **场景5（依赖取数）** | 代销/直销判断依赖 T2、T31 的字段组合；CUST_TYPE 依赖 T5 | `source_type='dependency'` |
| **场景6（组合）** | XSFS 整体 = 参数 + 依赖 + 优先级 + LEFT JOIN 的组合 | 嵌套 SourceRule 列表 |

### 9.2 对详细设计的关键补充

#### 9.2.1 参数占位符的解析与替换

XSFS 代码中出现了 `#[TSIS_GXHCS]`、`#[TPRT_XSFSQSLJ]`、`#[TPRT_CCLYQSLJ]` 等系统参数占位符。

**设计补充**：
- `etl_mapper` 新增 **参数占位符提取** 功能，使用正则 `#\[([A-Z_]+)\]` 识别 ETL 代码中的所有参数。
- 每个 `SourceRule` 增加 `params: List[str]` 字段，记录该字段依赖的所有参数名。
- `condition_builder` 在生成 `extra_condition` 时，对参数占位符生成 `AND :param_name = '<value>'` 形式的条件。
- **在巡检 SQL 中**，参数占位符替换为绑定变量 `:param_name`，运行时由用户传入。

**SourceRule 扩展**：
```python
@dataclass
class SourceRule:
    source_type: Literal['simple', 'union', 'priority', 'param', 'dependency']
    dw_tables: List[str]
    on_clauses: List[str]
    # 参数控制（场景4）
    params: List[str] = None                # 依赖的参数名列表，如 ['TSIS_GXHCS', 'TPRT_XSFSQSLJ']
    param_map: Dict[str, str] = None         # 参数值 → 选择的 DW 表或分支
    # 依赖取数（场景5）
    condition_branches: List[Tuple[str, str]] = None  # (条件表达式, 目标DW表)
    # 同表多次 JOIN（如 T3/T31）
    join_aliases: Dict[str, str] = None      # 同一DW表的不同别名，如 {'DW_D_FUND_AGENCY_INFO': ['T3', 'T31']}
```

#### 9.2.2 同一 DW 表多次 LEFT JOIN（不同别名）

XSFS 中 `DW_D_FUND_AGENCY_INFO` 被关联了两次：
- `T3`：按 `AGENCY_CODE` 关联（销售商维度）
- `T31`：按 `CHANNEL_CODE` 关联（渠道维度）

**设计补充**：
- `ETLMapping` 的 `dw_to_stg` 映射需要支持 **别名**：同一张 DW 表可以有多个别名，每个别名对应不同的 `ON` 条件。
- 在生成巡检 SQL 时，根据 `SourceRule.condition_branches` 中的条件决定使用哪个别名的字段。

**映射模型扩展**：
```python
# 之前：dw_to_stg: Dict[str, Tuple[str, str]]
# 现在：dw_to_stg: Dict[str, List[DWAlias]]
@dataclass
class DWAlias:
    alias: str           # SQL 中的别名，如 'T3'、'T31'
    on_clause: str       # 对应的 ON 条件
    stg_table: str       # 对应的 STG 表
    on_stg_clause: str   # DW → STG 的 ON 条件
```

#### 9.2.3 外层 WHERE 条件也影响追溯路径

XSFS 代码最后有：
```sql
WHERE (T6.CPTL_WEIGHT > 0 OR (T.CCLY LIKE '%2%' AND T4.BEFC_RIGHT_ASSN_FLAG IN ('1','2')) OR T.ZCFWXTFL1 = '2')
```

**设计补充**：
- `etl_mapper` 在解析 ETL 脚本时，除了提取 `JOIN ... ON ...`，还必须提取 **最外层 WHERE 条件**。
- `SourceRule` 新增 `where_clause: str` 字段，保存与该字段取值相关的外层 WHERE 片段。
- 在生成巡检 SQL 时，这些 WHERE 条件会追加到 `extra_condition` 中。

#### 9.2.4 日志规范补充

新增以下 WARN 类型：

| WARN 类型 | 说明 |
|-----------|------|
| `WARN_PARAM_PLACEHOLDER` | ETL 代码中包含未识别的参数占位符（如 `#[UNKNOWN_PARAM]`） |
| `WARN_DUP_TABLE_JOIN` | 同一 DW 表出现多次 LEFT JOIN（如 DW_D_FUND_AGENCY_INFO 作为 T3 和 T31） |
| `WARN_WHERE_CONDITION` | 外层 WHERE 条件涉及非主键字段，已追加到 extra_condition |

### 9.3 XSFS 对巡检脚本生成的实际影响

1. **XSFS 为空时的追溯**：需要判断 **哪个参数分支下** 应该有值，再追溯到对应的 STG 表。例如 `#[TSIS_GXHCS]='GLXT'` 下 XSFS 为空，需要检查 T2/T3/T31/T5 是否关联到了正确的 STG 记录。
2. **参数必须作为输入**：生成的巡检 SQL 必须接受 `TSIS_GXHCS`、`TPRT_XSFSQSLJ` 等参数，否则无法确定走哪个分支。
3. **多表 LEFT JOIN**：T3 和 T31 同表不同关联条件，需要在 `ON` 条件中保留各自的别名和关联字段。
4. **WHERE 过滤条件**：`T6.CPTL_WEIGHT > 0` 等条件也影响数据范围，必须追加到巡检 SQL 的 WHERE 中。

## 10 复杂取数场景的风险与实现方案

### 10.1 场景 3 - 优先级取数（LEFT JOIN 链）
- **映射模型**：`SourceRule.source_type = 'priority'`，`dw_tables` 按出现顺序保存。
- **SQL 生成**：使用 `COALESCE(dw1.col, dw2.col, dw3.col)` 实现"先取 DW1，取不到再 DW2"。
- **日志**：若某个 DW 未找到对应 STG，记录 `WARN_PRIORITY_UNRESOLVED`。

### 10.2 场景 4 - 参数控制取数
- **映射模型**：`SourceRule.source_type = 'param'`，`param_name` 保存业务参数字段名，`param_map` 保存参数值 -> DW 表映射。
- **SQL 生成**：在 `WHERE` 中加入 `AND :param_name = <value>`，并使用 `CASE WHEN` 依据参数切换列。
- **日志**：若业务参数值不在 `param_map` 中，记录 `WARN_PARAM_MISMATCH`。

### 10.3 场景 5 - 依赖取数（多条件分支）
- **映射模型**：`SourceRule.source_type = 'dependency'`，`condition_branches` 保存 `(condition_sql, dw_table)` 列表。
- **SQL 生成**：外层 `CASE WHEN ... THEN dwX.col ... END`，每个分支对应不同的 DW->STG 链路。
- **日志**：分支未匹配到任何 STG 时记录 `WARN_DEPENDENCY_UNMATCHED`。

### 10.4 场景 6 - 组合复杂取数（优先级 + 参数 + 依赖）
- **映射模型**：`SourceRule` 允许 **嵌套列表**，即同一字段拥有多条 `SourceRule`（例如先 `param` 再 `priority`），生成器递归组合。
- **SQL 生成**：最外层 `CASE` 根据业务参数选择对应的内部实现（COALESCE / CASE / UNION ALL）。
- **日志**：每一次组合都会在 `generation_log.txt` 中记录具体使用的规则链路，便于追溯。

### 10.5 日志规范（新增 WARN 类型）
```
WARN_PRIORITY_UNRESOLVED   - 优先级取数中某层未找到 STG 表
WARN_PARAM_MISMATCH        - 参数控制取数的参数值未在映射中定义
WARN_DEPENDENCY_UNMATCHED  - 依赖取数条件未匹配到任何 DW→STG 链
WARN_MULTI_SOURCE          - UNION ALL 多源取数已生成子查询
WARN_PARAM_PLACEHOLDER     - ETL 代码中包含未识别的参数占位符
WARN_DUP_TABLE_JOIN        - 同一 DW 表出现多次 LEFT JOIN（不同别名）
WARN_WHERE_CONDITION       - 外层 WHERE 条件涉及非主键字段，已追加到 extra_condition
```

## 11 下一步执行计划（您批准后立即开始）
1. **创建 todos**（已在系统中记录）。
2. **实现模块**（Python 3.11）-- 按实现路线表顺序逐一实现并编写单元测试。
3. **运行主脚本**生成文件结构与日志。
4. **返回文件清单、示例 SQL（前 3 条）以及 `generation_log.txt`** 给您审阅。

> 所有实现均遵循 **"先文档后代码"** 的流程，您可以随时修改 markdown 文档，修改内容会自动记录在 `generation_log.txt` 中，以保证可追溯。

## 12 勾稽代码 ↔ SUC编号 映射表

### 12.1 概述

每次运行 `generate_stg_checks.py` 时，同步生成映射表文件，记录每条报表勾稽代码与 SUC 巡检编号的对应关系，便于后续查找和同步更新。

### 12.2 输出文件

| 文件 | 格式 | 路径 | 用途 |
|------|------|------|------|
| `check_suc_mapping.md` | Markdown 表格 | `output_stg_file/` | 人眼阅读、版本对比 |
| `check_suc_mapping.csv` | CSV (UTF-8 BOM) | `output_stg_file/` | 程序化读取、Excel打开 |

### 12.3 映射表字段

| 字段 | 说明 |
|------|------|
| `suc_number` | SUC编号，如 SUC0001 |
| `check_code` | 报表勾稽代码，如 305.1918 |
| `check_name` | 勾稽名称 |
| `report_table` | 报表名，如 URP_SRDT5_XTCPLXRXXB |
| `report_field` | 报表字段，如 XMJLHXMFZRGH |
| `is_mandatory` | 必填类型（必填/条件必填） |
| `match_type` | 匹配类型（见8.5.4） |
| `dm_table` | DM表名（空=未映射） |
| `dm_field` | DM字段名 |
| `stg_table` | STG表名 |
| `stg_field` | STG字段名 |
| `sql_file` | 对应SQL文件路径 |

### 12.4 匹配类型说明

| 匹配类型 | 标记 | 说明 | 可信度 |
|----------|------|------|--------|
| EXACT_TEMPLATE | ✅ 模板 | 巡检列精确匹配，SQL模板完整可用 | 高 |
| EXACT_ASSEMBLE | ✅ 拼装 | 巡检列精确匹配，无SQL模板，从映射拼装 | 中 |
| DM_SUPPLEMENT_TEMPLATE | ⚠️ DM补充(模板) | 通过DM字段映射补充，借用同DM表SQL模板，保留JOIN和data_source，需确认STG字段 | 需人工确认STG字段 |
| DM_SUPPLEMENT_ASSEMBLE | ⚠️ DM补充(拼装) | 通过DM字段映射补充且无可用模板，通用拼装，JOIN和字段均需确认 | 需人工确认 |
| PLACEHOLDER | ❌ 需人工 | 未找到任何映射，需人工补充完整SQL | 低 |

### 12.5 更新规则

1. **已有勾稽代码**：保持原 SUC 编号不变（即使SQL内容有更新）
2. **新增勾稽代码**：追加到末尾，分配新 SUC 编号
3. **删除勾稽代码**：保留其 SUC 编号行，但 `match_type` 标记为已删除
4. **人工补充后**：更新 `match_type` 从 `PLACEHOLDER`/`DM_SUPPLEMENT` 为 `EXACT_TEMPLATE`
5. **版本控制**：建议将映射表MD文件纳入 Git 版本管理

## 13 工作原则

> **本章节是项目执行过程中的核心行为准则，优先级高于一切实现细节。**

### 13.1 发现错误时及时更新文档

在沟通或开发过程中，如果发现之前的理解、假设、设计有误，**必须立即更新详设文档**，并在变更日志中记录修改内容、修改原因和影响范围。

**反面教训**：v0.1-v0.3 中使用"同报表名取第一行"匹配策略，导致 635 条 SQL 检查了错误的字段（如 305.1918 本应检查 `XMJLHXMFZRGH` 却检查了 `FGXMDGSGGGH`）。此错误在抽查验证时才发现，说明文档未及时反映映射策略缺陷。

**要求**：

- 每次发现理解偏差，立即更新对应章节并补充变更日志
- 变更日志必须注明：修改内容、修改原因、影响行数
- 不得在文档和实际代码之间产生不一致

### 13.2 输入信息不完整时不得猜测

在生成 STG 巡检脚本的过程中，如果发现现有的输入信息（Excel、ETL 脚本、映射表等）**不完整**——例如某个报表字段在巡检列和DM字段映射中都找不到对应关系——**不得猜测或编造STG表名、字段名、关联条件**。

**正确做法**：
1. 在生成的 SQL 中标记 `-- !!! TODO: 请人工补充 !!!`
2. 在 `generation_log.txt` 中记录 `WARN_MAPPING_MISSING`
3. **立即告知用户**：哪些信息缺失、需要补充什么文档或数据

**反面教训**：策略3"同报表名取第一行"本质上就是一种猜测——当精确匹配失败时，猜测同报表的另一个字段可能是用户需要的字段，结果导致了系统性错配。

### 13.3 有疑问时直接确认

在生成巡检脚本的过程中，如果对业务逻辑、映射关系、条件判断等有任何疑问，**不得自作主张**，必须直接向用户确认。

**要求**：
- 遇到歧义时，列出 2-3 个可能的解释方案，请用户选择
- 不确定映射关系时，向用户提供具体字段名请确认
- 宁可多问一次，不可错配一个字段

### 13.4 禁止暴力枚举

**严禁**在不确定或信息不完整的前提下，暴力枚举所有可能的情况来生成代码。

**为什么**：
- 暴力枚举会产生大量看似完整、实则错误的 SQL，用户需要逐条人工验证，工作量反而更大
- 错误的 SQL 比缺失的 SQL 更危险——用户可能直接运行错误的巡检脚本，导致错误的巡检结论
- 标记为 TODO 的占位 SQL 是诚实的状态，一目了然需要人工补充

**正确做法**：
- 信息不完整 → 生成占位 SQL + 记录缺失原因
- 有疑问 → 列出方案请用户确认后再生成
- 确认完整 → 生成完整 SQL

### 13.5 禁止参考 my_poor_solution.xlsx 中的SQL方案

**严禁**直接使用 `my_poor_solution.xlsx` 中巡检列的SQL模板作为参数控制逻辑的来源。该文件中的SQL模板是为**原始字段**（如 `ZXD_ACCO_NO`）设计的，**不包含**其他字段（如 `XMJLHXMFZRGH`）所需的参数控制条件（如 `URP_PARAM_CONFIG` 子查询或 `#[PARAM]` 占位符）。

**为什么**：

- DM补充行借用同DM表其他字段的SQL模板时，该模板可能不包含当前字段需要的参数引用
- 例如：`DM_CTRC_XTCPLXRXXZBB.XMJLHXMFZRGH` 借用了 `ZXD_ACCO_NO` 的SQL模板，该模板不含 `CTRC_XMJLHXMFZRQSLJ` 和 `CTRC_YGH` 参数，导致仅生成1份SQL而非预期的10份
- 正确的参数控制逻辑应从**ETL清洗代码**（`etl_code_list/`）中提取，而非从巡检列SQL模板中推断

**正确做法**：
- 参数控制字段→参数代码的映射应**以 `param_field_mapping.xlsx`（从ETL清洗代码提取）为主**
- 确保每次运行 `parse_etl_params.py` 后 `param_field_mapping.xlsx` 包含完整的ETL解析结果（不应被权限错误阻挡）
- 当巡检列SQL模板不含参数引用但 `param_field_mapping.xlsx` 映射表中存在该字段的参数时，应**注入参数控制条件**到生成的SQL中

### 13.6 代码变更必须同步提交 Git

`scripts/` 目录已初始化 Git 仓库并关联 GitHub 远程仓库 `git@github.com:zhoupeilong/freecode.git`。**每次本地修改代码后，必须同步提交并推送到 GitHub。**

**规则**：
- 完成一组逻辑变更后，立即执行 `git add -A && git commit -m "描述变更"`
- commit 消息应简明描述本次变更内容（如"新增嵌套CASE WHEN参数映射"），不写泛泛的"update"
- 推送到远程：`git push`
- 修改代码前应先检查 `git status` 确认当前状态
- 涉及 3 个以上文件的批量修改，提交前先列出变更清单让用户确认

**为什么**：
- 防止代码丢失——历史会话中曾发生代码误删无法恢复的情况
- Git 提交历史即为变更日志，与详设文档变更日志互为印证
- GitHub 远程备份确保本地故障时代码不丢失
- `git diff` 可随时回顾具体改动，便于自查和回滚

**工作流**：
```powershell
# 修改代码前
git status                          # 确认当前干净状态

# ... 修改代码 ...

# 修改代码后
git add -A                          # 暂存所有变更
git commit -m "v0.x: 变更描述"      # 提交到本地
git push                            # 推送到 GitHub
```

### 13.7 参数组合决定SQL结构，而非仅替换条件

当参数控制ETL清洗逻辑时，不同参数值组合会产生**完全不同的SQL结构**，而非仅仅替换WHERE条件。参数展开必须重建SQL的JOIN链、STG表/字段、WHERE过滤条件。

**为什么**：
- 以 `DM_CTRC_XTCPLXRXXZBB.XMJLHXMFZRGH` 为例，`CTRC_XMJLHXMFZRQSLJ` 控制 DW 表的 JOIN 方式（=1→trust_manager匹配，=2→trust_manager+B+C匹配），`CTRC_YGH` 控制 DW 字段→STG 字段的映射
- 10份SQL不仅是WHERE条件不同，而是**JOIN链、STG表、STG字段**都不同
- 当前 v0.8 的参数展开逻辑仅做WHERE条件替换和注释头插入，无法生成结构不同的SQL

**参数驱动SQL结构的三个维度**：

1. **JOIN链**：不同参数值 → DW表使用不同的JOIN条件（如CTRC_XMJLHXMFZRQSLJ=1用trust_manager匹配，=2用trust_manager+B+C匹配）
2. **STG字段映射**：不同参数值 → DM字段取自不同的DW字段 → 追溯DW清洗逻辑 → 对应不同的STG表字段
3. **WHERE参数过滤**：不同参数组合 → 必须添加 `AND (SELECT param_value FROM URP_PARAM_CONFIG WHERE param_code='X') = 'Y'`，限定巡检数据范围与报表层一致，避免数据范围扩散

**实现前提**：
- 需从ETL清洗代码中提取并持久化 **DM字段→参数→{JOIN链, DW表, DW字段, STG表, STG字段}** 的完整血缘映射
- 需从DW清洗代码中提取并持久化 **DW字段→STG表.字段** 的映射
- 上述映射作为SQL生成的输入配置，而非运行时动态解析

### 13.8 STG字段表达式与空值判断必须逻辑自洽

当STG字段表达式使用 `NVL(字段A, 字段B)` 等优先组合时，WHERE条件中的空值判断必须使用**相同的表达式**，确保逻辑自洽。

**为什么**：
- 巡检脚本检查的是"报表不应为空的字段，在STG源数据中是否确实为空"
- 如果报表取值逻辑是 `NVL(LOGIN_ALIAS, EMPLOYEE_ID)`（优先取登录别名，为空取用户编码），那么"为空"的判定条件也应该是 `NVL(LOGIN_ALIAS, EMPLOYEE_ID) IS NULL`（两者都为空才算空）
- 如果WHERE只检查 `LOGIN_ALIAS IS NULL` 而STG字段表达式是 `NVL(LOGIN_ALIAS, EMPLOYEE_ID)`，则会误报——LOGIN_ALIAS为空但EMPLOYEE_ID不为空的数据不应被标记为异常

**示例**（以CTRC_YGH参数为例）：

| CTRC_YGH | STG字段表达式 | WHERE空值判断 |
|----------|--------------|--------------|
| 1 | `t.EXT_FIELD_1` | `trim(t.EXT_FIELD_1) IS NULL` |
| 2 | `t.USER_CODE` | `trim(t.USER_CODE) IS NULL` |
| 3 | `t.OUT_SYSTEM_USER_ID` | `trim(t.OUT_SYSTEM_USER_ID) IS NULL` |
| 4 | `NVL(t.EXT_FIELD_1, t.USER_CODE)` | `NVL(trim(t.EXT_FIELD_1), trim(t.USER_CODE)) IS NULL` |
| 5 | `NVL(t.OUT_SYSTEM_USER_ID, t.USER_CODE)` | `NVL(trim(t.OUT_SYSTEM_USER_ID), trim(t.USER_CODE)) IS NULL` |

## 14 URP报表字段↔DM指标表字段映射（v0.6 新增）

### 14.1 概述

为解决报表勾稽代码到DM表字段的映射查找问题，已从 `urp_code_list/` 目录下的 ETL SQL 脚本中提取了完整的 URP报表字段↔DM指标表字段映射关系，保存为 `urp_dm_field_mapping.xlsx`。

**关键变化**：后续在报表勾稽代码查找对应的DM表和DM字段时，**直接在此 xlsx 中查找即可**，无需再遍历 `etl_code_list/` 目录解析 SQL。此变化简化了映射查找流程，提升了速度和准确性。

### 14.2 数据来源与提取方法

| 项 | 说明 |
|------|------|
| 数据来源 | `urp_code_list/` 目录下的 286 个 PL/SQL ETL 脚本 |
| 提取脚本 | `scripts/parse_urp_dm_mapping.py` |
| 提取逻辑 | 解析每个 ETL 脚本中的 `INSERT INTO URP_xxxx (col_list) SELECT ... FROM DM_xxxx` 语句，提取 INSERT 列名（URP字段）和 SELECT 表达式中的别名或列名（DM字段） |
| 优先选择 | 当同一 URP 表有多个 SQL 文件时，优先使用 `_0_RPT` 或 `_1_RPT` 文件（主逻辑） |

### 14.3 映射字段说明

| 字段 | 说明 | 示例 |
|------|------|------|
| ID | `URP_TABLE_NAME.URP_COLUMN_NAME`，行记录唯一标识 | `URP_TPRT_CPJBXX.XTDJXTCPBM` |
| URP_TABLE_NAME | URP报表表名 | `URP_TPRT_CPJBXX` |
| URP_COLUMN_NAME | URP报表字段名 | `XTDJXTCPBM` |
| DM_TABLE_NAME | DM指标表名 | `DM_CTRC_CPJBXXZBB` |
| DM_COLUMN_NAME | DM指标表字段名（同名映射时与URP字段名相同，异名映射时不同） | `XTDJXTCPBM`（同名）或 `SHAREHOLDER_TYPE`（异名） |
| DM_EXPRESSION | DM字段表达式原文（已清理SQL注释和乱码） | `t.shareholder_type gdlx` |
| 备注 | 映射类型分类 | 同名映射 / 异名映射 / 系统变量 |

### 14.4 映射统计

| 类型 | 数量 | 占比 | 说明 |
|------|------|------|------|
| 同名映射 | 1,107 | 69.5% | URP字段名 = DM字段名，如 `XTDJXTCPBM` → `XTDJXTCPBM` |
| 异名映射 | 424 | 26.6% | URP字段名 ≠ DM字段名，如 `GDLX` → `SHAREHOLDER_TYPE` |
| 系统变量 | 62 | 3.9% | DM字段为系统变量（如 `V_COMPANY_NAME`、`#[DW_ZXDJGID]`） |
| **合计** | **1,593** | **100%** | 覆盖 98 个目标URP表中的 95 个（96.9%） |

### 14.5 映射类型示例

```sql
-- 同名映射：t.xtdjxtcpbm XTDJXTCPBM
-- URP字段 = DM字段 = XTDJXTCPBM，直接取值
  
-- 异名映射（函数转换）：fn_translatedict('CTRC_0045',t.ccly,';',';') CCLY
-- URP字段 = CCLY，DM字段 = CCLY，但经过字典函数转换

-- 异名映射（字段名不同）：t.shareholder_type gdlx  
-- URP字段 = GDLX，DM字段 = SHAREHOLDER_TYPE（中文→英文命名差异）

-- 异名映射（条件表达式）：CASE WHEN t.xmyzms IN ('0','2') THEN fn_translatedict('CTRC_0052',t.kfpd) END AS KFPD
-- URP字段 = KFPD，DM字段 = XMYZMS（条件判断 + 字典转换）

-- 系统变量：#[DW_ZXDJGID] XTJGMC
-- URP字段 = XTJGMC，DM字段无对应（来自系统参数）
```

### 14.6 未覆盖的 URP 表

以下 3 个URP表未提取到映射：

| URP表名 | 原因 |
|----------|------|
| `URP_SRDT5_ALLSUBJECTS` | `urp_code_list/` 目录中无对应SQL文件 |
| `URP_SRDT5_XTCPZZKJQKMB` | SQL文件使用中文文件名后缀和特殊格式，解析逻辑未覆盖 |
| `URP_SRDT5_XTNBKMDZB` | SQL中 INSERT 格式包含 `/*+ append nologging */` 提示，解析逻辑未覆盖 |

> 以上 3 个表的映射可后续手动补充，或增强 `parse_urp_dm_mapping.py` 的解析能力。

### 14.7 后续维护

1. **重新提取**：当 `urp_code_list/` 下的 ETL 脚本更新时，重新运行 `scripts/parse_urp_dm_mapping.py` 即可生成最新的映射文件
2. **增量的 SUC 编号**：`generate_stg_checks.py` 支持 `load_existing_mapping()` 读取已有 CSV 保持 SUC 编号不变
3. **映射查找集成**：后续版本可考虑将 `urp_dm_field_mapping.xlsx` 作为 `etl_mapper.py` 的新数据源，在 `find_mapping_for_check()` 中优先查找此文件

## 15 参数控制字段展开（v0.7 新增）

### 15.1 概述

ETL清洗代码中大量使用了 `#[PARAM]` 占位符和 `URP_PARAM_CONFIG` 参数查询来控制字段取值逻辑。巡检列（my_poor_solution.xlsx）中已有153条SQL模板包含参数引用。v0.7新增**参数展开**机制：对业务参数的每个有效值组合，生成独立的STG巡检SQL脚本。

**关键决策**：参数分为两类，只有**业务参数**需要展开，**个性化参数**保留原样。

### 15.2 参数分类

| 分类 | 定义 | 展开策略 | 示例 |
|------|------|----------|------|
| **业务参数** | 功能性取数逻辑开关，值数量少且每个值对应不同的业务取数路径 | 按值展开为独立SQL | CTRC_XMJLHXMFZRQSLJ(2值)、CTRC_YGH(5值)、TPRT_SSXTGMQFCCLY(4值) |
| **个性化参数** | 机构/系统级别的个性化配置，每个部署只使用一个值 | 保留`URP_PARAM_CONFIG`子查询不展开 | TSIS_GXHCS(66值/信托公司)、DW_ZXDJGID(机构ID)、TUSP_XTGSZXDBM(68值) |

**判定标准**：
- `code_param_list.xlsx` 中参数值数量 ≥ 10 且值列表包含机构代码/公司缩写 → 归类为个性化参数
- 参数名以 `TSIS_`、`DW_`、`TUSP_` 开头且涉及机构选择 → 归类为个性化参数
- 其余参数 → 归类为业务参数

### 15.3 参数来源与映射

#### 15.3.1 参数定义来源

| 来源文件 | 说明 | 字段 |
|----------|------|------|
| `code_param_list.xlsx` | 906条参数定义，包含参数代码、名称、值列表(JSON)、默认值 | 参数代码、参数名称、参数值、参数定义、参数默认值 |
| ETL清洗代码 | `urp_code_list/` 和 `etl_code_list/` 中的 `#[PARAM]` 占位符和 CASE WHEN 结构 | 字段→参数的依赖关系 |
| 巡检列SQL模板 | 153条已含 `URP_PARAM_CONFIG` 子查询的SQL | 现有参数引用模式 |

#### 15.3.2 参数映射配置（新增 `param_field_mapping.xlsx`）

从ETL清洗代码解析生成，记录**哪些DM字段受哪些参数控制**：

| 字段 | 说明 | 示例 |
|------|------|------|
| DM_TABLE | DM表名 | DM_CTRC_XTCPLXRXXZBB |
| DM_FIELD | DM字段名 | XMJLHXMFZRGH |
| PARAM_CODE | 参数代码 | CTRC_XMJLHXMFZRQSLJ |
| PARAM_CATEGORY | 参数类型 | business / personalization |
| PARAM_VALUES | 参数有效值（JSON） | ["1","2"] |
| DEFAULT_VALUE | 默认值 | 1 |
| CASE_WHEN_EXPR | ETL中的CASE WHEN表达式（摘要） | CASE WHEN #[CTRC_XMJLHXMFZRQSLJ] = '2' THEN ... |
| SQL_TEMPLATE_REF | 参考ETL文件名 | DM_CTRC_XTCPLXRXXZBB_中信登指标清洗.sql |

#### 15.3.3 现有参数引用模式分析

巡检列中153条参数SQL的参数分布：

| 参数代码 | 出现次数 | 类型 | 值数量 | 展开方式 |
|----------|----------|------|--------|----------|
| TSIS_GXHCS | 150 | 个性化 | 66 | 保留URP_PARAM_CONFIG |
| SRDT5_YGH | 93 | 个性化（等同CTRC_YGH） | 5 | 展开为5个SQL |
| SRDT5_YGXXBQSLY | 17 | 业务 | 2 | 展开为2个SQL |
| DW_ZXDJGID | 17 | 个性化 | 1 | 保留URP_PARAM_CONFIG |
| SRDT5_GLFXXBQSLY | 6 | 业务 | 2 | 展开为2个SQL |
| TUSP_TAKHLBXFSFQYKHSX | 5 | 业务 | 2 | 展开为2个SQL |
| TPRT_SSXTGMQFCCLY | 5 | 业务 | 4 | 展开为4个SQL |
| 其他15个参数 | 各1-4次 | 混合 | 2-11 | 按类型决定 |

> **注意**：SRDT5_YGH 实际上是 CTRC_YGH 在巡检列SQL模板中的引用名称，两者等价。DM_CTRC_XTCPLXRXXZBB 的清洗代码中引用的是 CTRC_YGH（5值），而巡检列SQL中使用的是 SRDT5_YGH。参数映射需要处理这种等价关系。

### 15.4 展开算法

#### 15.4.1 核心逻辑

```
对于每条检查项 check_info：
  1. 通过 find_mapping_for_check() 获取映射 insp_row
  2. 从 insp_row.sql_template 提取所有参数引用
  3. 分类：将参数分为 business_params 和 personal_params
  4. 若无 business_params → 生成1个SQL（保持原样，包括personal_params的URP_PARAM_CONFIG查询）
  5. 若有 business_params → 计算笛卡尔积：
     expansion_values = itertools.product(*[param.values for param in business_params])
     for each value_combo in expansion_values:
       sql = sql_template（替换业务参数为具体值，保留个性化参数的URP_PARAM_CONFIG查询）
       suc_number = next_available_suc_number()
       write sql to file
```

#### 15.4.2 笛卡尔积计算示例

对于 XMJLHXMFZRGH（检查编号305.1918）：

| 参数 | 职业 | 值数量 |
|------|------|--------|
| CTRC_XMJLHXMFZRQSLJ | 项目经理取数逻辑 | 2 (1=项目经理, 2=项目经理+B+C) |
| CTRC_YGH | 员工号取数场景 | 5 (1~5不同取法) |

笛卡尔积：2 × 5 = **10 个SQL脚本**

#### 15.4.3 对已有153条参数SQL的展开

对于巡检列中已有的 `URP_PARAM_CONFIG` 引用：

- **标量子查询模式**：`(select param_value from urp3.URP_PARAM_CONFIG t where param_code='XXX' and status='1') = 'VALUE'`
  - 业务参数展开：替换为具体值，如 `TSIS_GXHCS` 保留原样，`CTRC_YGH = '1'` 替换为字面值
  - 个性化参数保留：子查询不变

- **展开步骤**：
  1. 解析SQL模板中的 `param_code` 引用
  2. 识别每个 `param_code` 的类型（business/personalization）
  3. 对业务参数的每个值组合，创建SQL变体
  4. 在SQL头部注释中标注参数值

#### 15.4.4 SQL头部标注格式

展开后的SQL头部增加参数标注：

```sql
--报表字段：DM_CTRC_XTCPLXRXXZBB.XMJLHXMFZRGH
--DM字段：DM_CTRC_XTCPLXRXXZBB.XMJLHXMFZRGH
-- 参数组合: CTRC_XMJLHXMFZRQSLJ=1, CTRC_YGH=1
-- 参数说明: 项目经理或项目负责人工号取数逻辑=项目信息/子项目信息-项目经理, 员工号取数场景=取登录别名
-- 检查编号: 305.1918
-- ⚠️ DM补充: 借用同DM表(DM_CTRC_XTCPLXRXXZBB)的SQL模板，已替换检核字段为(XMJLHXMFZRGH)
-- 请人工确认: JOIN条件、data_source过滤、STG字段(XMJLHXMFZRGH)是否正确
-- 勾稽名称: <信托产品联系人信息表-项目经理或项目负责人工号>，不应为空
```

### 15.5 新增模块：`param_config_loader.py`

```python
@dataclass
class ParamDefinition:
    """参数定义"""
    param_code: str          # 参数代码，如 CTRC_XMJLHXMFZRQSLJ
    param_name: str          # 参数名称
    param_values: List[Tuple[str, str]]  # [(value, label), ...]
    default_value: str        # 默认值
    category: str             # 'business' 或 'personalization'

@dataclass
class ParamFieldMapping:
    """字段→参数的映射"""
    dm_table: str            # DM表名
    dm_field: str             # DM字段名
    param_code: str           # 参数代码
    case_when_expr: str       # CASE WHEN表达式摘要
    ref_source: str           # 参考来源（ETL文件名或巡检列）

def load_param_config(xlsx_path: str) -> Dict[str, ParamDefinition]:
    """加载 code_param_list.xlsx，返回 {param_code: ParamDefinition}"""
    
def classify_param(param: ParamDefinition) -> str:
    """分类参数为 business 或 personalization"""
    
def find_params_for_field(dm_table: str, dm_field: str, 
                          param_field_map: List[ParamFieldMapping]) -> List[str]:
    """查找控制某DM字段的参数列表"""

def expand_business_params(params: Dict[str, ParamDefinition], 
                           business_param_codes: List[str]) -> List[Dict[str, str]]:
    """计算业务参数的笛卡尔积，返回 [{param_code: value, ...}, ...]"""
```

### 15.6 对 `generate_stg_checks.py` 的修改

1. **新增参数展开步骤**（步骤3a，在步骤2和3之间）：
   
   - 加载 `code_param_list.xlsx`
   - 加载 `param_field_mapping.xlsx`
   - 对每条检查项，识别其SQL模板中的参数引用
   - 计算业务参数的笛卡尔积
   
2. **修改 `main()` 流程**：
   ```
   原流程: 1.读取输入 → 2.加载映射 → 3.加载STG主键 → 4.加载表信息 → 5.生成SQL → 6.写入文件
   新流程: 1.读取输入 → 2.加载映射 → 2d.加载参数配置 → 3.加载STG主键 → 4.加载表信息 → 5.生成SQL(含参数展开) → 6.写入文件
   ```

3. **修改 `generate_sql_for_check()` 签名**：
   - 新增 `param_combo: Optional[Dict[str, str]]` 参数（参数值组合）
   - 新增 `param_expand_info: Optional[List[Dict]]` 参数（展开信息列表）

4. **新增 `generate_param_expanded_sqls()` 函数**：
   - 输入：原始SQL + 参数值组合列表
   - 对每个参数值组合：替换业务参数的条件为具体值，保留个性化参数的子查询
   - 返回：展开后的SQL列表

5. **映射表新增字段**：
   - `param_codes`：参数代码列表（逗号分隔）
   - `param_values`：参数值组合（JSON）

### 15.7 展开规模预估

| 类别 | 数量 | 说明 |
|------|------|------|
| 原始检查项（无参数） | ~1593 | 不含参数引用的检查项，各生成1个SQL |
| 参数检查项（仅个性化参数） | ~89 | 含TSIS_GXHCS等，保留原样各1个SQL |
| 参数检查项（含业务参数） | ~64 | 需要展开，各生成N个SQL（N=业务参数笛卡尔积） |
| 展开后业务参数SQL | ~347 | 64项的展开总数 |
| **总计** | **~2029** | 约2000-2100个SQL文件 |

### 15.8 参数映射等价关系

在ETL清洗代码和巡检列SQL中，同一参数可能使用不同的代码名：

| 巡检列SQL参数代码 | ETL清洗代码参数代码 | 等价关系 | 说明 |
|-------------------|---------------------|----------|------|
| SRDT5_YGH | CTRC_YGH | 等价 | 员工号取数场景 |
| SRDT5_YGXXBQSLY | CTRC_YGXXBQSLY | 等价 | 员工信息指标表取数来源 |

> **等价处理**：在展开时，SRDT5_YGH 和 CTRC_YGH 共享相同的参数值定义（5值）。需建立参数代码等价映射表。

### 15.9 潜在风险与注意事项

1. **笛卡尔积爆炸**：虽然TSIS_GXHCS(66值)已归类为个性化参数不展开，但仍需警惕其他多值业务参数的组合。如 TPRT_QCYJDQRQFA(6值) × CTRC_YGH(5值) = 30个SQL。
2. **参数值遗漏**：`code_param_list.xlsx` 中部分参数可能缺少定义（7个参数不在配置中），需在生成时标记为需人工确认。
3. **等价参数**：SRDT5_YGH/CTRC_YGH 等价关系需维护映射表，避免重复展开。
4. **SQL模板中的隐式参数**：部分SQL模板的条件可能隐含参数依赖（通过表连接条件 `AND #[PARAM] = 'VALUE'`），需从ETL清洗代码中完整提取。
5. **SUC编号连续性**：展开后的SQL使用连续编号（从已有编号末尾+1开始），映射表中需清晰标注关系。

### 15.10 实现路线

| 步骤 | 任务 | 负责模块 | 产出 |
|------|------|----------|------|
| **3a** | 加载 `code_param_list.xlsx`，构建参数定义字典，分类为 business/personalization | `param_config_loader` | `Dict[str, ParamDefinition]` |
| **3b** | 从ETL清洗代码解析 DM字段→参数 的依赖关系（新增 `param_field_mapping.xlsx`） | `parse_etl_params.py`（新脚本） | `param_field_mapping.xlsx` |
| **3c** | 识别巡检列SQL模板中的参数引用，计算业务参数的笛卡尔积 | `generate_stg_checks.py` | 参数值组合列表 |
| **5a** | 对每组参数值组合，替换业务参数值，保留个性化参数查询 | `generate_stg_checks.py` | 展开后的SQL列表 |
| **5b** | 生成参数标注头部（参数组合、参数说明） | `generate_stg_checks.py` | SQL注释头部 |
| **5c** | 写入文件，更新映射表（新增 param_codes 和 param_values 字段） | `file_writer` + `generate_stg_checks.py` | SQL文件 + 映射表 |

---

## 16 数据库兼容与INSERT生成（v1.0新增）

### 16.1 背景

随着国内金融厂商逐步推进信创改造，项目需要支持除Oracle以外的国产数据库。同时，生成的巡检脚本需要从文件形式改为存储到数据库表中，便于管理和执行。

### 16.2 目标

1. 支持三种数据库：Oracle、达梦(DM)、OceanBase
2. 将巡检脚本从文件形式转换为数据库INSERT语句
3. 支持可配置的脚本参数

### 16.3 目标表结构

```sql
CREATE TABLE URP_STG_DATA_CHECK_AI
(
  CHECK_CODE            VARCHAR2(128),
  CHECK_NAME            VARCHAR2(500),
  CHECK_SQL             CLOB,
  STG_TABLE_NAME        VARCHAR2(32 CHAR),
  STG_TABLE_COL_NAME    VARCHAR2(32 CHAR),
  STG_TABL_NAME_CH      VARCHAR2(255 CHAR),
  STG_TABLE_COL_NAME_CH VARCHAR2(255 CHAR),
  CREATE_TIME           DATE,
  UPDATE_TIME           DATE,
  STATUS                NUMBER(1),
  REMARK                VARCHAR2(2000),
  ENABLED_STATUS        NUMBER(1),
  CUSTOMER_SOURCE       VARCHAR2(32),
  ENV_ID                VARCHAR2(20),
  START_TIME            DATE,
  END_TIME              DATE,
  CHECK_STATUS          VARCHAR2(200),
  ERROR_INFO            VARCHAR2(4000),
  CHECK_ERROR_NUM       NUMBER(8),
  RELY_VERSION          VARCHAR2(200) DEFAULT 'URP3.0.V202502.03.000',
  CHECK_CODE_URP        VARCHAR2(128),
  STG_COL_PATH          VARCHAR2(2000 CHAR),
  STG_COL_SRC_PIC       VARCHAR2(2000 CHAR),
  VERSION_BATCH         VARCHAR2(30 CHAR),
  DM_TABLE_NAME         VARCHAR2(256 CHAR),
  DM_TABLE_COL_NAME     VARCHAR2(256 CHAR),
  CHECK_CODE_URP_LIST   VARCHAR2(256 CHAR)
);
```

### 16.4 数据库适配器设计

#### 16.4.1 适配器类图

```
DatabaseAdapter (基类)
├── OracleAdapter    # Oracle数据库
├── DMAdapter        # 达梦数据库
└── OceanBaseAdapter # OceanBase数据库（MySQL模式）
```

#### 16.4.2 适配器方法

| 方法 | 说明 | Oracle | 达梦 | OceanBase |
|------|------|--------|------|-----------|
| `convert_sql()` | SQL语法转换 | 原样返回 | 保留 \|\| 拼接CLOB | NVL→IFNULL |
| `get_clob_concat()` | CLOB拼接符 | \|\| | \|\| | CONCAT_WS('', |
| `get_to_date()` | 日期转换函数 | to_date() | to_date() | str_to_date() |
| `get_current_timestamp()` | 当前时间 | sysdate | sysdate | now() |

### 16.5 配置管理

#### 16.5.1 配置文件结构（db_insert_config.json）

```json
{
  "script_type": "1",
  "script_name_prefix": "STG_CHECK",
  "app_version_no": "URP3.0.V202502.13.000",
  "customer_source": "HUNDSUN",
  "env_id": "001",
  "rely_version": "URP3.0.V202502.06.000",
  "enabled_status": 1,
  "status": 1,
  "description": "STG巡检脚本INSERT生成配置"
}
```

#### 16.5.2 配置参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| script_type | 脚本类型 | 1 |
| script_name_prefix | 脚本名称前缀 | STG_CHECK |
| app_version_no | 应用版本号 | URP3.0.V202502.13.000 |
| customer_source | 客户来源 | HUNDSUN |
| env_id | 环境ID | 001 |
| rely_version | 依赖版本 | URP3.0.V202502.06.000 |
| enabled_status | 是否启用 | 1 |
| status | 状态 | 1 |

### 16.6 核心模块

#### 16.6.1 SQLParser（SQL解析器）

从巡检SQL中自动提取字段信息：

| 正则表达式 | 提取内容 |
|------------|----------|
| `'(.+?)'\s+check_name` | 勾稽名称 |
| `'([^']+)'\s+stg_table_name` | STG表名 |
| `'([^']+)'\s+stg_col_name` | STG字段名 |
| `--\s*检查编号:\s*(\S+)` | 检查编号 |
| `from\s+urp3_tusp\.(\w+)` | DM表名 |
| `trim\(k\.(\w+)\)\s+IS\s+NULL` | DM字段名 |

#### 16.6.2 InsertGenerator（INSERT生成器）

将巡检SQL转换为PL/SQL块：

```plsql
DECLARE
    v_script_type VARCHAR2(64) := '1';
    v_script_name VARCHAR2(64) := '20260423_SUC0005_DQ36.A0304';
    v_app_version_no VARCHAR2(64) := 'URP3.0.V202502.13.000';
    n_count NUMBER(10);
BEGIN
    SELECT COUNT(1) INTO n_count FROM URP_SQLUPDATE_LOG a WHERE a.script_name = v_script_name;
    IF n_count = 0 THEN
        EXECUTE IMMEDIATE 'DELETE FROM URP_STG_DATA_CHECK_AI WHERE CHECK_CODE=''DQ36.A0304''';
        
        INSERT INTO URP_STG_DATA_CHECK_AI (...) VALUES (...);
        
        -- 写入日志
        INSERT INTO URP_SQLUPDATE_LOG (...) VALUES (...);
        COMMIT;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
        RAISE_APPLICATION_ERROR(-20002, ...);
END;
/
```

### 16.7 输出目录结构

```
output_stg_file/
├── SUC0001_SUC0100/
│   ├── SUC0001.sql
│   └── ...
├── SUC0101_SUC0200/
│   └── ...
└── db_ver/
    ├── SUC0001_SUC0100/
    │   ├── SUC0001_insert.sql
    │   └── ... (100个文件)
    ├── SUC0101_SUC0200/
    │   ├── SUC0101_insert.sql
    │   └── ... (100个文件)
    └── ... (按SUC编号范围分目录)
```

### 16.8 主流程集成

在 `generate_stg_checks.py` 的主流程中新增第5步：

```
原流程: 1.读取输入 → 2.加载映射 → 2d.加载参数配置 → 3.加载STG主键 → 4.加载表信息 → 5.生成SQL → 6.写入文件 → 7.生成摘要
新流程: 1.读取输入 → 2.加载映射 → 2d.加载参数配置 → 3.加载STG主键 → 4.加载表信息 → 5.生成SQL → 6.写入文件 → 5.生成数据库INSERT → 7.生成摘要
```

### 16.9 验证结果

| 指标 | 数值 |
|------|------|
| 总SQL文件数 | 2112份 |
| INSERT脚本文件数 | 2112个 |
| 覆盖率 | 92.1% |

> **重要**：一份SQL代码通过适配器模式自动兼容Oracle、达梦、OceanBase三种数据库，无需生成三份代码。适配器在运行时根据目标数据库类型选择对应的语法转换逻辑。

---

# 第17章 STG巡检代码重复性约束

## 17.1 需求背景

STG巡检代码与报表勾稽代码的关系是多对多的关系。不同报表勾稽代码可能引用相同的DM指标字段，如果分别生成会导致STG巡检代码重复。

**示例**：
- 报表勾稽代码305.1918有SUC1483~SUC1492这十个STG巡检代码
- 报表勾稽代码301.4305和DQ01.A0006对应的DM指标都是DM_CTRC_CPJBXXZBB.CCLY，本应一个STG巡检代码给两者公用

## 17.2 需求目标

1. 识别哪些不同报表勾稽代码引用了相同的DM指标字段
2. 对共享DM指标的勾稽代码，只生成一份STG巡检代码
3. 优先以DQ开头的报表勾稽代码（定期报送）生成STG巡检代码
4. 数字开头的报表勾稽代码不单独生成STG巡检代码

## 17.3 业务规则

### 17.3.1 勾稽代码类型判断

| 类型 | 判断规则 | 示例 |
|------|----------|------|
| DQ（定期报送） | 以"DQ"开头 | DQ01.A0006, DQ36.A0304 |
| NUM（数字） | 以数字开头 | 301.4305, 102.1679 |
| OTHER | 其他格式 | （暂不处理） |

### 17.3.2 STG巡检代码生成规则

对于共享同一DM指标的多个勾稽代码：
1. **优先选择DQ开头的勾稽代码**生成STG巡检代码
2. 如果没有DQ开头的，选择数字开头的
3. 如果都没有，选择第一个
4. 其他的勾稽代码标记为共用，不生成独立STG巡检代码

### 17.3.3 共享标记

| 标记 | 含义 | 说明 |
|------|------|------|
| S | Share（生成目标） | 该勾稽代码负责生成STG巡检代码 |
| C | Common（共用） | 该勾稽代码复用S生成的STG巡检代码 |

## 17.4 实现方案

### 17.4.1 数据关联

通过以下字段关联三张表：

```
report_check_list.xlsx.报表名称 + 报表字段
    ↓ 关联
urp_dm_field_mapping.xlsx.URP_TABLE_NAME + URP_COLUMN_NAME
    ↓
得到: 勾稽代码 → DM指标(DM_TABLE_NAME.DM_COLUMN_NAME)
```

### 17.4.2 共享检测算法

```
输入: 合并后的勾稽代码-DM指标映射
输出: 共享DM指标列表 + 生成目标勾稽代码

算法:
1. 按(DM_TABLE_NAME, DM_COLUMN_NAME)分组
2. 统计每组引用的勾稽代码集合
3. 如果集合大小 > 1，则为共享DM指标
4. 对每个共享DM指标，应用选择规则确定生成目标
```

### 17.4.3 排除机制

在`generate_stg_checks.py`主流程中：
1. 加载共享DM指标映射JSON
2. 生成排除集合（所有非生成目标的勾稽代码）
3. 在SQL生成循环中检查排除集合
4. 如果勾稽代码在排除集合中，跳过该条记录

## 17.5 新增模块

### 17.5.1 analyze_shared_dm.py

**功能**：分析共享DM指标，生成映射文件

**输入**：
- `report_check_list.xlsx` - 报表勾稽定义
- `urp_dm_field_mapping.xlsx` - URP-DM字段映射

**输出**：
- `shared_dm_mapping.json` - 共享DM指标映射
- `shared_dm_analysis_report.txt` - 分析报告

**核心函数**：

```python
def find_shared_dm_indicators(merged_df: pd.DataFrame) -> pd.DataFrame:
    """找出被多个不同勾稽代码引用的DM指标"""

def generate_exclusion_set(shared_df: pd.DataFrame) -> Set[str]:
    """生成需要排除的勾稽代码集合"""
```

### 17.5.2 映射文件格式

```json
{
  "DM_CTRC_CPJBXXZBB.CCLY": {
    "all_codes": ["301.4305", "DQ01.A0006"],
    "selected_code": "DQ01.A0006",
    "share_status": {
      "301.4305": "C",
      "DQ01.A0006": "S"
    },
    "report_tables": ["URP_TPRT_CPJBXX", "URP_SRDT5_CPJBXXB"],
    "report_fields": ["CCLY"]
  }
}
```

## 17.6 主流程集成

在`generate_stg_checks.py`的主流程`main()`函数中新增：

```python
# 2g. 加载共享DM指标映射（v1.1新增 - STG巡检代码重复性约束）
exclusion_set = set()
shared_dm_mapping_path = os.path.join(output_dir, "shared_dm_mapping.json")
if os.path.exists(shared_dm_mapping_path):
    # 加载映射并生成排除集合
    ...
```

在SQL生成循环中：

```python
for i, check in enumerate(checks, start=1):
    # v1.1: STG巡检代码重复性约束 - 检查是否需要跳过
    if check.check_code in exclusion_set:
        logger.info(f"跳过 {check.check_code}（该勾稽代码引用的DM指标已被共享）")
        continue
    # 继续生成SQL...
```

## 17.7 运行方式

```bash
# 第1步：分析共享DM指标（生成shared_dm_mapping.json）
python scripts/analyze_shared_dm.py

# 第2步：生成STG巡检脚本（会自动加载映射文件进行去重）
python scripts/generate_stg_checks.py
```

## 17.8 验证结果

| 指标 | 数值 |
|------|------|
| 合并后记录数 | 1463条 |
| 共享DM指标数量 | 344个 |
| 需要排除的勾稽代码数 | 502个 |
| DQ开头生成目标 | 305个 |
| 数字开头生成目标 | 39个 |

### 17.8.1 共享DM指标样例

| DM指标 | 引用勾稽代码 | 生成目标 |
|--------|-------------|---------|
| DM_CTRC_CPJBXXZBB.CCLY | 301.4305, DQ01.A0006 | DQ01.A0006 |
| DM_CTRC_CPJBXXZBB.FXZRCS | DQ01.A0313, 301.1842 | DQ01.A0313 |
| DM_CTRC_CPJBXXZBB.SFFQMJFK | 301.4360, DQ01.A0324 | DQ01.A0324 |
| DM_CTRC_CPJBXXZBB.SFTOT | 301.1851, DQ01.A0008 | DQ01.A0008 |
| DM_CTRC_CPJBXXZBB.SFWJGHXT | DQ01.A0319, 301.1850, 301.1847, 301.1849, 301.1848 | DQ01.A0319 |

---

## 变更日志

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-04-17 | v0.1 | 初始版本：概要设计、核心模块、日志格式 |
| 2026-04-17 | v0.2 | 新增章节 7（复杂取数场景的风险与实现方案），涵盖场景 3-6 |
| 2026-04-17 | v0.3 | 新增章节 6（XSFS 实例验证），补充参数占位符、同表多 JOIN、外层 WHERE 条件、SourceRule 扩展、日志规范 |
| 2026-04-21 | v0.4 | **重大修正**：映射策略从"STG到DM表映射"改为"巡检列为主映射源"；移除策略3（同报表名取第一行）避免字段错配；新增工作原则章节 §9；DM字段映射补充行标记 `is_from_dm_supplement` 防止借用模板中硬编码字段污染 |
| 2026-04-21 | v0.4.1 | 补充变更详情：(1) 原策略3导致635条SQL检查了错误字段，已移除；(2) 精确匹配733条+DM字段映射补充846条+占位167条=1746条，覆盖率90.4%；(3) 对DM补充行借用SQL模板的情况，标记is_from_dm_supplement=True，使用拼装而非借用的硬编码模板；(4) 新增§8.5勾稽代码↔SUC编号映射表(md+csv双格式) |
| 2026-04-20 | v0.5 | **DM补充SQL质量修复**：(1) DM补充行有借用模板时，改用`_fill_sql_template()`替代`_assemble_sql()`，保留参考行的JOIN条件、data_source过滤、参数控制；(2) 新增`_replace_stg_field_in_select()`替换SELECT中硬编码的stg_col_value/stg_col_name/stg_col_name_cn/check_name字段值；(3) 新增`_add_dm_supplement_comment()`为DM补充SQL添加⚠️标记注释；(4) 映射表分类从DM_SUPPLEMENT细分为DM_SUPPLEMENT_TEMPLATE(653条)和DM_SUPPLEMENT_ASSEMBLE(193条)；(5) 最终覆盖率：精确模板731(41.9%)+精确拼装2(0.1%)+DM补充模板653(37.4%)+DM补充拼装193(11.1%)+需人工167(9.6%)=1746条 |
| 2026-04-20 | v0.6 | **URP-DM字段映射提取与工作流简化**：(1) 新增`parse_urp_dm_mapping.py`脚本从`urp_code_list/`的286个ETL脚本中提取URP报表字段↔DM指标表字段映射；(2) 生成`urp_dm_field_mapping.xlsx`，1593条映射覆盖95/98个URP表(96.9%)；(3) 映射查找优先级变更：后续报表勾稽代码查找DM表字段时**直接在xlsx中查找**，无需再解析`etl_code_list/`目录下的SQL文件；(4) 新增§10详述URP-DM映射的数据来源、字段结构、统计、示例和维护方法；(5) §3.1更新为映射查找优先级说明；(6) §5更新实现路线步骤2拆分为2a/2b/2c三步 |
| 2026-04-21 | v0.7 | **参数控制字段展开**（重大更新）：(1) 参数控制字段需按业务参数值的笛卡尔积生成多个STG巡检脚本，新增§11详述参数展开机制；(2) 参数分为两类：**业务参数**（如CTRC_XMJLHXMFZRQSLJ、CTRC_YGH等，按值展开）和**个性化参数**（如TSIS_GXHCS、DW_ZXDJGID等，保留URP_PARAM_CONFIG查询不展开）；(3) 新增`param_config_loader.py`模块加载`code_param_list.xlsx`参数定义，区分参数类型；(4) 新增参数映射配置xlsx，从ETL清洗代码解析字段→参数的依赖关系；(5) `generate_stg_checks.py`新增参数展开逻辑：对业务参数做笛卡尔积展开，个性化参数保留子查询；(6) SUC编号方案变更：展开后的SQL按连续编号追加（SUC1747起）；(7) 映射表新增`param_codes`和`param_values`字段；(8) 预计展开后总SQL文件约2030-2100个 |
| 2026-04-21 | v0.7.1 | **参数展开BUG修复与增强**（影响60+个SQL文件）：(1) 修复`_remove_business_param_conditions`无法处理CASE WHEN参数模式的问题——新增`_replace_case_when_params`函数，将CASE WHEN子查询块替换为当前参数值对应的THEN分支表达式；(2) 新增`_remove_inline_param_conditions`函数，处理AND/OR行内业务参数条件（包括`<>`、`IN`、`NOT IN`等比较运算符）；(3) 修复不在配置中的业务参数导致展开失败的问题——`generate_param_expanded_sqls`将无值列表的业务参数降级为个性化参数（保留URP_PARAM_CONFIG查询不展开）；(4) 修复等价参数映射（如SRDT5_YGH→CTRC_YGH）在CASE WHEN场景下的正确展开；(5) 端到端验证结果：196份展开SQL含`-- 参数组合:`注释，0份文件残存业务参数条件，116份仅含个性化参数；(6) 总SQL文件1965份，覆盖率91.5% |
| 2026-04-21 | v0.7.2 | **param_field_mapping.xlsx数据修复 + 设计原则更新**：(1) 发现`param_field_mapping.xlsx`仅包含136条映射（仅来自巡检列`my_poor_solution.xlsx`），缺失了ETL清洗文件解析的3635条映射，导致`DM_CTRC_XTCPLXRXXZBB.XMJLHXMFZRGH`字段的`CTRC_XMJLHXMFZRQSLJ`和`CTRC_YGH`两个业务参数未生成笛卡尔积展开（仅生成1份SUC1394而非预期的10份）；(2) 根因：`parse_etl_params.py`的`main()`函数虽合并了ETL解析结果和巡检列解析结果（共2045条去重映射），但上次写入xlsx时可能因权限错误导致ETL部分未保存；(3) 修复：重新运行`parse_etl_params.py`以生成完整的2045条映射；(4) **重要设计原则**：禁止参考`my_poor_solution.xlsx`中的方案作为SQL模板来源，该文件会误导参数控制逻辑 |
| 2026-04-21 | v0.8 | **字段级参数映射注入 + 嵌套CASE WHEN解析**（解决305.1918仅生成1份SQL的问题）：(1) `parse_etl_params.py`新增Step 3b——检测外层CASE WHEN `END AS field_alias` 的THEN表达式中嵌套的`#[PARAM]`引用，将嵌套参数也映射到同一field_alias（如`CTRC_YGH`映射到`XMJLHXMFZRGH`）；(2) 重新运行后`param_field_mapping.xlsx`从2045条扩展到2456条；(3) `generate_stg_checks.py`新增`load_field_param_mapping()`函数，从`param_field_mapping.xlsx`构建`(dm_table, dm_field) → [param_code, ...]`查找表；(4) 参数展开入口条件扩展为三种触发：SQL含URP_PARAM_CONFIG / SQL模板含#[PARAM]占位符 / **字段级映射表明该字段受业务参数控制**（即使SQL中无参数引用）；(5) `generate_param_expanded_sqls()`新增`field_param_codes`参数，支持外部传入字段级映射的参数代码进行展开；(6) 修复SQL头部`-- 参数组合:`注释无法插入的问题——改用"在`-- 检查编号:`前插入"策略，兼容含额外注释行（如DM补充⚠️注释）的SQL；(7) 验证结果：305.1918生成10份SQL（2×5笛卡尔积），总SQL文件2112份，509份含参数标注 |
| 2026-04-21 | v0.8.1 | **参数展开正确性反思 + 新增设计原则**：(1) **发现v0.8的10份SQL虽然参数注释不同，但SQL体完全一致**——仅替换了头部注释和WHERE条件中的URP_PARAM_CONFIG，未改变JOIN链、STG表、STG字段；(2) 根因：v0.7-v0.8的参数展开逻辑假设参数只控制WHERE条件（URP_PARAM_CONFIG子查询），但实际上 **ETL参数控制的是清洗逻辑（CASE WHEN + JOIN条件），不同参数值组合产生完全不同的SQL结构**；(3) 以305.1918为例，验证了正确逻辑：CTRC_XMJLHXMFZRQSLJ控制DW表JOIN方式，CTRC_YGH控制DW→STG字段映射，WHERE必须添加URP_PARAM_CONFIG过滤限定数据范围；(4) 从DW清洗代码`DW_D_COMPANY_EMP_INFO_恒生综合管理平台.sql`提取了完整DW→STG字段血缘：`LOGIN_ALIAS←EXT_FIELD_1(登录别名)`、`EMPLOYEE_ID←USER_CODE(用户编码)`、`OUT_SYSTEM_USER_ID←OUT_SYSTEM_USER_ID(第三方系统用户ID)`；(5) 新增§9.7原则：参数组合决定SQL结构（JOIN链+STG字段+WHERE过滤），而非仅替换条件；(6) 新增§9.8原则：STG字段表达式与WHERE空值判断必须逻辑自洽——当STG字段使用`NVL(字段A,字段B)`时，WHERE空值判断也必须是`NVL(trim(字段A),trim(字段B)) IS NULL`；(7) **结论：v0.8的参数展开方案需升级为"参数驱动SQL结构重建"，需要构建并持久化完整的ETL血缘映射（DM字段→参数→{JOIN链, DW字段, STG字段}）作为SQL生成的输入配置** |
| 2026-04-21 | v0.9 | **参数驱动SQL结构重建（v0.8.1结论的实现）**：(1) 新增`etl_lineage_config.json`血缘配置文件，结构化描述DM字段→参数→{JOIN链, DW字段表达式, STG字段}的三层映射关系；(2) 血缘配置按参数维度组织：`join_path`类参数控制DW表JOIN方式，`field_mapping`类参数控制DW→STG字段映射，笛卡尔积自然生成所有组合；(3) `generate_stg_checks.py`新增`load_etl_lineage_config()`、`rebuild_sql_with_lineage()`、`_build_stg_null_check()`等函数，支持血缘驱动的SQL结构重建；(4) 参数展开优先级变更：**血缘配置优先**——当`etl_lineage_config.json`中存在该DM字段的血缘映射时，走血缘重建路径（重建JOIN链+STG字段+WHERE过滤）；否则走v0.8原有路径（仅替换WHERE条件）；(5) 实现§9.8逻辑自洽原则：`_build_stg_null_check()`根据STG字段表达式自动生成匹配的空值判断——简单字段→`trim(field) IS NULL`，NVL组合→`NVL(trim(A),trim(B)) IS NULL`；(6) 端到端验证：305.1918生成10份SQL，3个维度全部正确区分——JOIN链（trust_mgr vs trust_mgr+B+C）、STG字段（EXT_FIELD_1/USER_CODE/OUT_SYSTEM_USER_ID/NVL组合）、WHERE空值判断与STG字段表达式逻辑自洽 |
| 2026-04-23 | v1.0 | **数据库兼容支持 + INSERT语句生成（单代码兼容多数据库）**：(1) 重构`db_insert_generator.py`，使用统一适配器模式实现**一份代码同时支持Oracle、达梦、OceanBase**；(2) 保留`DatabaseAdapter`基类及三个实现类，但在生成时根据目标数据库类型选择对应适配器生成兼容代码；(3) 新增`ScriptConfig`类支持可配置脚本参数，配置通过`db_insert_config.json`管理；(4) 新增`SQLParser`类从巡检SQL自动提取字段信息；(5) 新增`InsertGenerator`类，将巡检SQL转换为PL/SQL块，包含幂等性检查；(6) **输出目录结构调整**：按SUC编号范围分目录（每100个文件），如`SUC0001_SUC0100/`、`SUC0101_SUC0200/`等，与SQL文件目录结构一致；(7) `generate_stg_checks.py`主流程集成数据库INSERT生成；(8) 生成的INSERT语句符合`URP_STG_DATA_CHECK_AI`表结构，包含27个字段；(9) 验证结果：2112份SQL文件，每份生成对应INSERT脚本，总计2112个INSERT文件 |
| 2026-04-23 | v1.1 | **BR042301：STG巡检代码重复性约束**：(1) 新增`analyze_shared_dm.py`脚本，分析报表勾稽代码与DM指标的共享关系；(2) 关联`report_check_list.xlsx`和`urp_dm_field_mapping.xlsx`，识别哪些不同报表勾稽代码引用了相同的DM指标字段；(3) 对共享的DM指标，标记所有引用的勾稽代码，其中选中的生成目标标记为`S`（Share），共用的标记为`C`（Common）；(4) **选择规则**：优先以DQ开头的报表勾稽代码（定期报送）生成STG巡检代码，如果无DQ开头的则选择数字开头的，否则选择第一个；(5) 分析结果：344个共享DM指标，305个选择DQ开头的勾稽代码生成STG巡检，39个选择数字开头的，总计需要排除502个勾稽代码；(6) 修改`generate_stg_checks.py`主流程，加载`shared_dm_mapping.json`并生成排除集合，在SQL生成循环中跳过排除集合中的勾稽代码；(7) 生成的巡检脚本数量将减少，避免重复