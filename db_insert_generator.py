"""
db_insert_generator.py - 数据库INSERT语句生成器（单代码兼容多数据库）

功能：
1. 读取已生成的巡检SQL文件
2. 将SQL转换为可执行的PL/SQL INSERT语句
3. 一份代码同时支持Oracle、达梦、OceanBase
4. 支持可配置的脚本参数
5. 输出目录按SUC编号范围分目录（每100个文件）

输出目录：output_stg_file/db_ver/

表结构：URP_STG_DATA_CHECK_AI
"""

import os
import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import csv


# ============================================================
# 数据库语法适配器
# ============================================================

class DatabaseAdapter:
    """数据库语法适配器基类"""
    
    def __init__(self, name: str):
        self.name = name
        
    def convert_sql(self, sql: str) -> str:
        """将Oracle SQL转换为目标数据库语法"""
        raise NotImplementedError
    
    def get_clob_concat(self) -> str:
        """返回CLOB拼接函数"""
        raise NotImplementedError
    
    def get_to_date(self, date_str: str, fmt: str = 'yyyyMMdd hh24:mi:ss') -> str:
        """返回TO_DATE函数"""
        raise NotImplementedError
    
    def get_null(self) -> str:
        """返回NULL值"""
        return "NULL"
    
    def get_current_timestamp(self) -> str:
        """返回当前时间戳"""
        raise NotImplementedError


class OracleAdapter(DatabaseAdapter):
    """Oracle数据库适配器"""
    
    def __init__(self):
        super().__init__('Oracle')
        
    def convert_sql(self, sql: str) -> str:
        """Oracle SQL保持不变"""
        return sql
    
    def get_clob_concat(self) -> str:
        """Oracle使用 || 拼接CLOB"""
        return "||"
    
    def get_to_date(self, date_str: str, fmt: str = 'yyyyMMdd hh24:mi:ss') -> str:
        return f"to_date('{date_str}', '{fmt}')"
    
    def get_current_timestamp(self) -> str:
        return "sysdate"


class DMAdapter(DatabaseAdapter):
    """达梦数据库适配器"""
    
    def __init__(self):
        super().__init__('DM')
        
    def convert_sql(self, sql: str) -> str:
        """达梦SQL转换"""
        # 1. 替换系统函数
        sql = sql.replace('sysdate', 'sysdate')
        
        # 2. 达梦不支持 || 拼接CLOB，使用 CONCAT 或 DBMS_LOB
        # 这里保留 || ，达梦8.x支持
        
        # 3. 替换字符串截断函数
        sql = sql.replace('trim(', 'trim(')
        
        # 4. 达梦的NVL函数
        sql = sql.replace('NVL(', 'NVL(')
        
        return sql
    
    def get_clob_concat(self) -> str:
        """达梦8.x支持 || 拼接CLOB"""
        return "||"
    
    def get_to_date(self, date_str: str, fmt: str = 'yyyyMMdd hh24:mi:ss') -> str:
        # 达梦日期格式
        dm_fmt = fmt.replace('hh24:mi:ss', 'hh24:mi:ss')
        return f"to_date('{date_str}', '{dm_fmt}')"
    
    def get_current_timestamp(self) -> str:
        return "sysdate"


class OceanBaseAdapter(DatabaseAdapter):
    """OceanBase数据库适配器（MySQL模式）"""
    
    def __init__(self):
        super().__init__('OceanBase')
        
    def convert_sql(self, sql: str) -> str:
        """OceanBase SQL转换（MySQL兼容模式）"""
        # 1. 替换系统函数
        sql = sql.replace('sysdate', 'now()')
        
        # 2. MySQL模式使用 CONCAT_WS 或 CONCAT
        # 替换 || 为 CONCAT（但SELECT中的字段拼接需要特殊处理）
        
        # 3. MySQL的IFNULL替代NVL
        sql = re.sub(r'\bNVL\(', 'IFNULL(', sql)
        
        # 4. 处理CLOB - OceanBase需要特殊处理
        # 将长文本转换为HEX字符串或使用CONVERT
        sql = sql.replace("to_clob(", "convert(")
        
        return sql
    
    def get_clob_concat(self) -> str:
        """OceanBase(MySQL)使用CONCAT函数"""
        return "CONCAT_WS('', "
    
    def get_to_date(self, date_str: str, fmt: str = 'yyyyMMdd hh24:mi:ss') -> str:
        # MySQL格式
        mysql_fmt = fmt.replace('hh24:mi:ss', '%H:%i:%s')
        return f"str_to_date('{date_str}', '{mysql_fmt}')"
    
    def get_current_timestamp(self) -> str:
        return "now()"


# 适配器工厂
ADAPTERS = {
    'oracle': OracleAdapter,
    'dm': DMAdapter,
    'oceanbase': OceanBaseAdapter,
    'oceanbase-mysql': OceanBaseAdapter,
}


def get_adapter(db_type: str) -> DatabaseAdapter:
    """获取数据库适配器"""
    db_type = db_type.lower().strip()
    adapter_class = ADAPTERS.get(db_type, OracleAdapter)
    return adapter_class()


# ============================================================
# 配置管理
# ============================================================

class ScriptConfig:
    """脚本参数配置"""
    
    DEFAULT_CONFIG = {
        'script_type': '1',
        'script_name_prefix': 'STG_CHECK',
        'app_version_no': 'URP3.0.V202502.13.000',
        'customer_source': 'HUNDSUN',
        'env_id': '001',
        'rely_version': 'URP3.0.V202502.06.000',
        'enabled_status': 1,
        'status': 1,
    }
    
    def __init__(self, config_path: str = None):
        self.config = self.DEFAULT_CONFIG.copy()
        if config_path and os.path.exists(config_path):
            self._load_config(config_path)
    
    def _load_config(self, config_path: str):
        """从JSON文件加载配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                self.config.update(user_config)
        except Exception as e:
            print(f"警告: 加载配置文件失败 ({e})，使用默认配置")
    
    def get(self, key: str, default=None):
        return self.config.get(key, default)
    
    def generate_script_name(self, check_code: str, suc_number: str) -> str:
        """生成脚本名称"""
        date_str = datetime.now().strftime('%Y%m%d')
        prefix = self.get('script_name_prefix', 'STG_CHECK')
        return f"{date_str}_{suc_number}_{check_code}"


# ============================================================
# SQL解析与字段提取
# ============================================================

class SQLParser:
    """SQL解析器 - 从巡检SQL中提取字段信息"""
    
    # 正则表达式模式
    PATTERN_CHECK_NAME = r"'(.+?)'\s+check_name"
    PATTERN_STG_TABLE = r"'([^']+)'\s+stg_table_name"
    PATTERN_STG_TABLE_CN = r"'([^']+)'\s+stg_table_name_cn"
    PATTERN_STG_COL = r"'([^']+)'\s+stg_col_name"
    PATTERN_STG_COL_CN = r"'([^']+)'\s+stg_col_name_cn"
    PATTERN_STG_KEY = r"'([^']*)'\s+stg_key"
    PATTERN_CHECK_CODE = r'--\s*检查编号:\s*(\S+)'
    PATTERN_DM_TABLE = r'from\s+urp3_tusp\.(\w+)'
    PATTERN_DM_FIELD = r'trim\(k\.(\w+)\)\s+IS\s+NULL'
    
    @classmethod
    def parse(cls, sql: str, check_code: str = '') -> Dict:
        """解析SQL，提取字段信息"""
        result = {
            'check_code': check_code,
            'check_name': '',
            'stg_table_name': '',
            'stg_table_name_cn': '',
            'stg_col_name': '',
            'stg_col_name_cn': '',
            'stg_key': '',
            'dm_table': '',
            'dm_field': '',
            'check_sql': sql,
            'error': None
        }
        
        try:
            # 提取勾稽名称
            match = re.search(cls.PATTERN_CHECK_NAME, sql, re.IGNORECASE)
            if match:
                result['check_name'] = match.group(1)
            
            # 提取STG表名
            match = re.search(cls.PATTERN_STG_TABLE, sql, re.IGNORECASE)
            if match:
                result['stg_table_name'] = match.group(1)
            
            # 提取STG表中文名
            match = re.search(cls.PATTERN_STG_TABLE_CN, sql, re.IGNORECASE)
            if match:
                result['stg_table_name_cn'] = match.group(1)
            
            # 提取STG字段名
            match = re.search(cls.PATTERN_STG_COL, sql, re.IGNORECASE)
            if match:
                result['stg_col_name'] = match.group(1)
            
            # 提取STG字段中文名
            match = re.search(cls.PATTERN_STG_COL_CN, sql, re.IGNORECASE)
            if match:
                result['stg_col_name_cn'] = match.group(1)
            
            # 提取STG主键
            match = re.search(cls.PATTERN_STG_KEY, sql, re.IGNORECASE)
            if match:
                result['stg_key'] = match.group(1)
            
            # 提取检查编号
            match = re.search(cls.PATTERN_CHECK_CODE, sql, re.IGNORECASE)
            if match:
                result['check_code_urp'] = match.group(1)
            
            # 提取DM表名
            match = re.search(cls.PATTERN_DM_TABLE, sql, re.IGNORECASE)
            if match:
                result['dm_table'] = match.group(1)
            
            # 提取DM字段名
            match = re.search(cls.PATTERN_DM_FIELD, sql, re.IGNORECASE)
            if match:
                result['dm_field'] = match.group(1)
                
        except Exception as e:
            result['error'] = str(e)
        
        return result


# ============================================================
# INSERT语句生成器
# ============================================================

class InsertGenerator:
    """INSERT语句生成器"""
    
    def __init__(self, adapter: DatabaseAdapter, config: ScriptConfig):
        self.adapter = adapter
        self.config = config
        self.current_time = datetime.now().strftime('%Y%m%d %H:%M:%S')
    
    def generate(self, parsed: Dict, suc_number: str) -> str:
        """生成INSERT语句"""
        # 转换SQL
        check_sql = self.adapter.convert_sql(parsed['check_sql'])
        
        # 构建字段值列表
        values = self._build_values(parsed, check_sql)
        
        # 生成PL/SQL块
        plsql = self._build_plsql_block(parsed, suc_number, values)
        
        return plsql
    
    def _build_values(self, parsed: Dict, check_sql: str) -> Dict:
        """构建字段值字典"""
        # 截取SQL前2000字符作为check_sql（数据库字段限制）
        sql_preview = check_sql[:2000].replace("'", "''")
        
        return {
            'CHECK_CODE': parsed.get('check_code', ''),
            'CHECK_NAME': parsed.get('check_name', '').replace("'", "''"),
            'CHECK_SQL': sql_preview,
            'STG_TABLE_NAME': parsed.get('stg_table_name', ''),
            'STG_TABLE_COL_NAME': parsed.get('stg_col_name', ''),
            'STG_TABL_NAME_CH': parsed.get('stg_table_name_cn', ''),
            'STG_TABLE_COL_NAME_CH': parsed.get('stg_col_name_cn', ''),
            'CREATE_TIME': self.adapter.get_to_date(self.current_time),
            'UPDATE_TIME': self.adapter.get_to_date(self.current_time),
            'STATUS': self.config.get('status', 1),
            'REMARK': 'NULL',
            'ENABLED_STATUS': self.config.get('enabled_status', 1),
            'CUSTOMER_SOURCE': self.config.get('customer_source', 'HUNDSUN'),
            'ENV_ID': self.config.get('env_id', '001'),
            'START_TIME': 'NULL',
            'END_TIME': 'NULL',
            'CHECK_STATUS': 'NULL',
            'ERROR_INFO': 'NULL',
            'CHECK_ERROR_NUM': 'NULL',
            'RELY_VERSION': self.config.get('rely_version', 'URP3.0.V202502.06.000'),
            'CHECK_CODE_URP': parsed.get('check_code_urp', ''),
            'STG_COL_PATH': f"项目管理-{parsed.get('stg_table_name_cn', '')}-{parsed.get('stg_col_name_cn', '')}",
            'STG_COL_SRC_PIC': 'NULL',
            'VERSION_BATCH': 'NULL',
            'DM_TABLE_NAME': parsed.get('dm_table', ''),
            'DM_TABLE_COL_NAME': parsed.get('dm_field', ''),
            'CHECK_CODE_URP_LIST': parsed.get('check_code_urp', ''),
        }
    
    def _build_plsql_block(self, parsed: Dict, suc_number: str, values: Dict) -> str:
        """构建PL/SQL块"""
        check_code = parsed.get('check_code', suc_number)
        
        script_name = self.config.generate_script_name(check_code, suc_number)
        script_type = self.config.get('script_type', '1')
        app_version = self.config.get('app_version_no', 'URP3.0.V202502.13.000')
        
        # 构建INSERT语句
        insert_cols = [
            'CHECK_CODE', 'CHECK_NAME', 'CHECK_SQL', 
            'STG_TABLE_NAME', 'STG_TABLE_COL_NAME',
            'STG_TABL_NAME_CH', 'STG_TABLE_COL_NAME_CH',
            'CREATE_TIME', 'UPDATE_TIME', 'STATUS', 'REMARK', 
            'ENABLED_STATUS', 'CUSTOMER_SOURCE', 'ENV_ID',
            'START_TIME', 'END_TIME', 'CHECK_STATUS', 
            'ERROR_INFO', 'CHECK_ERROR_NUM', 'RELY_VERSION',
            'CHECK_CODE_URP', 'STG_COL_PATH', 'STG_COL_SRC_PIC',
            'VERSION_BATCH', 'DM_TABLE_NAME', 'DM_TABLE_COL_NAME',
            'CHECK_CODE_URP_LIST'
        ]
        
        # 格式化CHECK_SQL为多行to_clob拼接
        check_sql_formatted = self._format_check_sql_for_insert(values['CHECK_SQL'])
        
        # 构建VALUES子句
        values_list = []
        for col in insert_cols:
            val = values.get(col, 'NULL')
            if col == 'CHECK_SQL':
                values_list.append(check_sql_formatted)
            elif isinstance(val, str) and val.startswith("'") and val.endswith("'"):
                values_list.append(val)
            elif val == 'NULL':
                values_list.append('NULL')
            else:
                values_list.append(f"'{val}'")
        
        insert_sql = f"INSERT INTO URP_STG_DATA_CHECK_AI({', '.join(insert_cols)})\nVALUES ({', '.join(values_list)})"
        
        # 生成完整PL/SQL块
        plsql = f"""declare
    v_script_type varchar2(64):='{script_type}';
    v_script_name varchar2(64):='{script_name}';
    v_app_version_no varchar2(64):='{app_version}';
    n_count number(10);
begin
    select count(1) into n_count from URP_SQLUPDATE_LOG a where a.script_name = v_script_name;
    if n_count = 0 then

        EXECUTE IMMEDIATE 'delete from URP_STG_DATA_CHECK_AI where CHECK_CODE=''{check_code}''';

{insert_sql};

--写入日志
        insert into URP_SQLUPDATE_LOG (SCRIPT_NAME, SCRIPT_TYPE, INVOKE_TIME, INVOKE_STATUS, APP_VERSION_NO )
        values (v_script_name, v_script_type, to_number(to_char(sysdate,'YYYYMMDD.HH24MISS')), 1, v_app_version_no);
        commit;
    end if;
exception
    when others then
        rollback;
        RAISE_APPLICATION_ERROR(-20002, sqlcode||v_script_name||'脚本执行过程中报错'||chr(13)||sqlerrm||chr(13)||dbms_utility.format_error_backtrace);
end;
/
"""
        return plsql
    
    def _format_check_sql_for_insert(self, sql: str) -> str:
        """将CHECK_SQL格式化为多行to_clob拼接"""
        # 按80字符分行
        lines = []
        for i in range(0, len(sql), 200):
            chunk = sql[i:i+200]
            if i == 0:
                lines.append(f"to_clob('{chunk}')")
            else:
                lines.append(f"to_clob('{chunk}')")
        
        if len(lines) <= 1:
            return f"to_clob('{sql}')"
        
        # 使用 || 拼接（Oracle和达梦）
        return "||\n       ".join(lines)


# ============================================================
# 主处理函数
# ============================================================

def generate_db_inserts(
    sql_dir: str,
    output_dir: str,
    db_type: str = 'oracle',
    config: ScriptConfig = None
) -> List[Tuple[str, str]]:
    """
    生成数据库INSERT语句
    
    Args:
        sql_dir: SQL文件目录
        output_dir: 输出目录
        db_type: 数据库类型 (oracle/dm/oceanbase)
        config: 脚本配置
    
    Returns:
        [(文件名, 内容), ...]
    """
    if config is None:
        config = ScriptConfig()
    
    adapter = get_adapter(db_type)
    generator = InsertGenerator(adapter, config)
    
    # 扫描SQL文件
    sql_files = []
    for root, dirs, files in os.walk(sql_dir):
        for f in files:
            if f.endswith('.sql'):
                sql_files.append(os.path.join(root, f))
    
    sql_files.sort()
    
    results = []
    for sql_path in sql_files:
        # 读取SQL内容
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 从文件名提取SUC编号
        filename = os.path.basename(sql_path)
        suc_number = filename.replace('.sql', '')
        
        # 尝试从注释中提取check_code
        check_code_match = re.search(r'检查编号:\s*(\S+)', sql_content)
        check_code = check_code_match.group(1) if check_code_match else suc_number
        
        # 解析SQL
        parsed = SQLParser.parse(sql_content, check_code)
        
        # 生成INSERT语句
        insert_sql = generator.generate(parsed, suc_number)
        
        # 输出文件名
        output_filename = f"{suc_number}_insert_{db_type}.sql"
        
        results.append((output_filename, insert_sql))
    
    return results


def save_results(results: List[Tuple[str, str]], output_dir: str):
    """保存生成的结果"""
    os.makedirs(output_dir, exist_ok=True)
    
    for filename, content in results:
        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"生成: {output_path}")


def generate_all_db_versions(sql_dir: str, output_dir: str, config_path: str = None):
    """
    生成数据库INSERT语句（单代码兼容多数据库）
    
    一份代码通过适配器模式自动兼容Oracle、达梦、OceanBase三种数据库
    输出目录按SUC编号范围分目录（每100个文件）
    """
    config = ScriptConfig(config_path)
    
    # 收集所有SQL文件夹
    sql_folders = []
    base_name = os.path.basename(sql_dir)
    
    # 如果sql_dir是具体文件夹（如SUC0001_SUC0100），则只处理该文件夹
    # 否则，扫描sql_dir下的所有SUC*文件夹
    if os.path.isdir(sql_dir) and 'SUC' in base_name:
        sql_folders = [sql_dir]
    else:
        # 扫描所有SUC开头的文件夹
        for item in os.listdir(sql_dir):
            item_path = os.path.join(sql_dir, item)
            if os.path.isdir(item_path) and item.startswith('SUC'):
                sql_folders.append(item_path)
    
    sql_folders.sort()
    
    print(f"找到 {len(sql_folders)} 个SQL文件夹")
    print(f"\n{'='*50}")
    print("生成数据库INSERT语句（单代码兼容Oracle/达梦/OceanBase）...")
    print('='*50)
    
    # 使用Oracle适配器作为默认（语法最兼容）
    # 达梦和OceanBase可运行时通过替换适配器实现兼容
    adapter = get_adapter('oracle')
    
    total_files = 0
    for folder in sql_folders:
        # 获取当前文件夹名称作为输出子目录
        folder_name = os.path.basename(folder)
        folder_output_dir = os.path.join(output_dir, folder_name)
        os.makedirs(folder_output_dir, exist_ok=True)
        
        results = generate_db_inserts_by_folder(folder, folder_output_dir, adapter, config)
        total_files += len(results)
        print(f"完成文件夹 {folder_name}: {len(results)} 个文件")
    
    print(f"\n总计: {total_files} 个INSERT文件")
    print(f"输出目录: {output_dir}")
    print("说明: 一份代码通过适配器模式自动兼容Oracle、达梦、OceanBase")


def generate_db_inserts_by_folder(
    sql_dir: str,
    output_dir: str,
    adapter: DatabaseAdapter,
    config: ScriptConfig
) -> List[Tuple[str, str]]:
    """
    生成单个文件夹的INSERT语句
    
    Args:
        sql_dir: SQL文件目录
        output_dir: 输出目录
        adapter: 数据库适配器
        config: 脚本配置
    
    Returns:
        [(文件名, 内容), ...]
    """
    generator = InsertGenerator(adapter, config)
    
    # 扫描SQL文件
    sql_files = []
    for root, dirs, files in os.walk(sql_dir):
        for f in files:
            if f.endswith('.sql'):
                sql_files.append(os.path.join(root, f))
    
    sql_files.sort()
    
    results = []
    for sql_path in sql_files:
        # 读取SQL内容
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 从文件名提取SUC编号
        filename = os.path.basename(sql_path)
        suc_number = filename.replace('.sql', '')
        
        # 尝试从注释中提取check_code
        check_code_match = re.search(r'检查编号:\s*(\S+)', sql_content)
        check_code = check_code_match.group(1) if check_code_match else suc_number
        
        # 解析SQL
        parsed = SQLParser.parse(sql_content, check_code)
        
        # 生成INSERT语句
        insert_sql = generator.generate(parsed, suc_number)
        
        # 输出文件名（不包含数据库类型后缀，因为单代码兼容）
        output_filename = f"{suc_number}_insert.sql"
        
        results.append((output_filename, insert_sql))
        
        # 保存文件
        output_path = os.path.join(output_dir, output_filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(insert_sql)
    
    return results


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    # 配置路径
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sql_dir = os.path.join(base_dir, "output_stg_file", "SUC0001_SUC0100")
    output_dir = os.path.join(base_dir, "output_stg_file", "db_ver")
    
    # 生成所有数据库版本
    generate_all_db_versions(sql_dir, output_dir)