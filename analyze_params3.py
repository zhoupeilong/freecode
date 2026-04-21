"""Analyze the detailed URP_PARAM_CONFIG WHERE clause patterns to understand expansion logic"""
import re, openpyxl, sys, json

sys.stdout.reconfigure(encoding='utf-8')

wb = openpyxl.load_workbook('F:/09_opencode/docs/my_poor_solution.xlsx', read_only=True, data_only=True)
ws = wb[wb.sheetnames[0]]

# Read code_param_list
wb2 = openpyxl.load_workbook('F:/09_opencode/docs/code_param_list.xlsx', read_only=True, data_only=True)
ws2 = wb2[wb2.sheetnames[0]]
param_values = {}  # param_code -> [(value, label)]
for row in ws2.iter_rows(min_row=2, values_only=True):
    if row[0]:
        code = str(row[0]).strip()
        definition = str(row[3]).strip() if row[3] else ''
        default = str(row[4]).strip() if row[4] else ''
        try:
            defs = json.loads(definition)
            vals = [(str(d.get('value','')), str(d.get('label',''))) for d in defs]
            param_values[code] = {'values': vals, 'default': default}
        except:
            pass
wb2.close()

# For each param SQL, extract the EXACT URP_PARAM_CONFIG WHERE clause patterns
param_sql_details = []
for row in ws.iter_rows(min_row=2, values_only=True):
    if row and row[22]:
        sql = str(row[22])
        if 'URP_PARAM_CONFIG' not in sql and '#[' not in sql:
            continue
        
        alias = str(row[1]) if row[1] else ''
        dm_table = str(row[12]) if row[12] else ''
        dm_field = str(row[13]) if row[13] else ''
        check_code = str(row[3]) if row[3] else ''
        check_name = str(row[4]) if row[4] else ''
        
        # Extract all URP_PARAM_CONFIG blocks
        # Pattern: (exists|not exists) (select 1 from urp3.URP_PARAM_CONFIG pc where pc.param_code = 'XXX' and pc.status = '1' and pc.param_value = 'Y')
        config_blocks = re.findall(
            r"(exists\s*\(select\s+1\s+from\s+urp3\.URP_PARAM_CONFIG\s+pc\s+where\s+pc\.param_code\s*=\s*'([^']+)'\s+and\s+pc\.status\s*=\s*'([^']+)'\s+and\s+pc\.param_value\s*=\s*'([^')]*)'\s*\))",
            sql,
            re.IGNORECASE
        )
        not_exists_blocks = re.findall(
            r"not\s+exists\s*\(select\s+1\s+from\s+urp3\.URP_PARAM_CONFIG\s+pc\s+where\s+pc\.param_code\s*=\s*'([^']+)'\s+and\s+pc\.status\s*=\s*'([^']+)'\s*\)",
            sql,
            re.IGNORECASE
        )
        
        param_sql_details.append({
            'alias': alias,
            'dm_table': dm_table,
            'dm_field': dm_field,
            'check_code': check_code,
            'check_name': check_name[:60],
            'exists_blocks': config_blocks,  # (full_match, param_code, status, param_value)
            'not_exists_blocks': not_exists_blocks,  # (param_code, status)
            'sql': sql
        })

wb.close()

# Summary
print(f"Total param SQL templates found: {len(param_sql_details)}")
print(f"Templates with exists blocks: {sum(1 for x in param_sql_details if x['exists_blocks'])}")
print(f"Templates with not_exists blocks: {sum(1 for x in param_sql_details if x['not_exists_blocks'])}")

# For each exists block, find which param_codes and param_values are used
# This tells us: for each check item, what param conditions are in the WHERE clause
print("\n=== Detailed param expansion analysis ===")
print("For each check item with URP_PARAM_CONFIG, show what params/values are referenced:")

# Group by param_code
from collections import defaultdict
param_usage = defaultdict(list)  # param_code -> list of (value, alias)

for item in param_sql_details:
    for block in item['exists_blocks']:
        full_match, param_code, status, param_value = block
        param_usage[param_code].append({
            'value': param_value,
            'alias': item['alias'],
            'check_code': item['check_code']
        })
    for block in item['not_exists_blocks']:
        param_code, status = block
        param_usage[param_code].append({
            'value': 'NOT_EXISTS',
            'alias': item['alias'],
            'check_code': item['check_code']
        })

print("\nParam codes referenced in URP_PARAM_CONFIG blocks:")
for code, usages in sorted(param_usage.items()):
    # Get the values from code_param_list
    config = param_values.get(code, {'values': [], 'default': 'unknown'})
    values_in_config = [v for v, l in config['values']]
    values_in_sql = list(set(u['value'] for u in usages))
    print(f"\n  {code}:")
    print(f"    Config values: {values_in_config}")
    print(f"    SQL references: {values_in_sql}")
    print(f"    Default: {config['default']}")
    print(f"    Used in {len(usages)} check items:")
    for u in usages[:3]:
        print(f"      {u['alias']} ({u['check_code']}) - value={u['value']}")

# Now: for TSIS_GXHCS (the most common param), how many unique values appear in SQL?
print("\n=== TSIS_GXHCS detailed analysis ===")
gxhcs_usages = param_usage.get('TSIS_GXHCS', [])
gxhcs_values = list(set(u['value'] for u in gxhcs_usages))
print(f"Values referenced in SQL: {gxhcs_values}")
print(f"Total check items using TSIS_GXHCS: {len(gxhcs_usages)}")

# Check how many check items need expansion
# For expansion: a check item with param P having N values needs N SQL scripts (or N * M if multiple params)
print("\n=== Expansion count estimate ===")
total_expanded = 0
for item in param_sql_details:
    # For each check item, how many param combinations?
    param_codes_in_item = set()
    for block in item['exists_blocks']:
        _, param_code, _, _ = block
        param_codes_in_item.add(param_code)
    for block in item['not_exists_blocks']:
        param_code, _ = block
        param_codes_in_item.add(param_code)
    
    # Calculate expansion factor
    expansion = 1
    for pc in param_codes_in_item:
        config = param_values.get(pc, {'values': [], 'default': '1'})
        n_values = len(config['values']) if config['values'] else 2
        expansion *= n_values
    
    total_expanded += expansion
    
    if len(param_codes_in_item) > 1:
        print(f"\n  Multi-param item: {item['alias']} ({item['check_code']})")
        print(f"    Params: {param_codes_in_item}")
        for pc in param_codes_in_item:
            config = param_values.get(pc, {'values': [], 'default': '?'})
            print(f"    {pc}: {len(config['values'])} values -> {[v for v,l in config['values']]}")
        print(f"    Expansion: {expansion} SQL scripts")

print(f"\nTotal original check items with params: {len(param_sql_details)}")
print(f"Total expanded SQL scripts needed: {total_expanded}")
print(f"Original total (1746) - param items (153) + expanded ({total_expanded}) = {1746 - 153 + total_expanded} total SQL files")