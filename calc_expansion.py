"""Calculate parameter expansion count estimate"""
import json, openpyxl, sys, re
from collections import defaultdict
from itertools import product

sys.stdout.reconfigure(encoding='utf-8')

# Load param definitions
wb = openpyxl.load_workbook('F:/09_opencode/docs/code_param_list.xlsx', read_only=True, data_only=True)
ws = wb[wb.sheetnames[0]]
param_defs = {}  # param_code -> {'values': [(v,l)], 'default': v}
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[0]:
        code = str(row[0]).strip()
        definition = str(row[3]).strip() if row[3] else ''
        default = str(row[4]).strip() if row[4] else ''
        try:
            defs = json.loads(definition)
            vals = [(str(d.get('value','')), str(d.get('label',''))) for d in defs]
            param_defs[code] = {'values': vals, 'default': default, 'name': str(row[1]).strip() if row[1] else ''}
        except:
            pass
wb.close()

# Load inspection SQLs to find param references
wb2 = openpyxl.load_workbook('F:/09_opencode/docs/my_poor_solution.xlsx', read_only=True, data_only=True)
ws2 = wb2[wb2.sheetnames[0]]

param_sql_items = []
for row in ws2.iter_rows(min_row=2, values_only=True):
    if row and row[22]:
        sql = str(row[22])
        if 'URP_PARAM_CONFIG' in sql or '#[' in sql:
            alias = str(row[1]) if row[1] else ''
            # Extract unique param codes from SQL
            codes_from_config = set(re.findall(r"param_code\s*=\s*'([^']+)'", sql, re.IGNORECASE))
            codes_from_hash = set(re.findall(r"#\[([A-Z_0-9]+)\]", sql, re.IGNORECASE))
            all_codes = codes_from_config | codes_from_hash
            
            # Calculate expansion factor
            expansion = 1
            for code in all_codes:
                if code in param_defs:
                    n_vals = len(param_defs[code]['values'])
                    expansion *= n_vals
                else:
                    # Param not in config - estimate from SQL
                    # For TSIS_GXHCS (66 values) this would be huge
                    # But inspection SQLs actually only reference specific values
                    # Need to count distinct values referenced in SQL
                    values_in_sql = set(re.findall(r"param_value\s*=\s*'([^']*)'", sql, re.IGNORECASE))
                    # Also check = 'XXX' patterns after param subquery
                    if code == 'TSIS_GXHCS':
                        expansion *= 66  # Known from param config
                    elif code == 'DW_ZXDJGID':
                        expansion *= 1  # This is a system variable, not a param to expand
                    elif code == 'SRDT5_YGH':
                        expansion *= 5  # CTRC_YGH has 5 values in param config
                    else:
                        expansion *= max(len(values_in_sql), 2)  # At least 2
            
            param_sql_items.append({
                'alias': alias,
                'param_codes': list(all_codes),
                'expansion': expansion
            })

wb2.close()

# Stats
total_expanded = sum(item['expansion'] for item in param_sql_items)
original_count = 1746
param_count = len(param_sql_items)
non_param_count = original_count - param_count

print(f"=== Parameter Expansion Estimate ===")
print(f"Original check items: {original_count}")
print(f"  Non-param items: {non_param_count}")
print(f"  Param items: {param_count}")
print(f"  Total expanded SQL for param items: {total_expanded}")
print(f"New total: {non_param_count} + {total_expanded} = {non_param_count + total_expanded}")

# Show biggest expansion items
param_sql_items.sort(key=lambda x: -x['expansion'])
print(f"\n=== Top 30 expansion items ===")
for item in param_sql_items[:30]:
    codes_info = []
    for code in item['param_codes']:
        if code in param_defs:
            codes_info.append(f"{code}({len(param_defs[code]['values'])}vals)")
        else:
            codes_info.append(f"{code}(unknown)")
    print(f"  {item['alias']}: {item['expansion']}x -> {codes_info}")

# Group by expansion factor
exp_groups = defaultdict(int)
for item in param_sql_items:
    exp_groups[item['expansion']] += 1

print(f"\n=== Expansion factor distribution ===")
for exp, count in sorted(exp_groups.items()):
    print(f"  {exp}x expansion: {count} items")

# Special handling for TSIS_GXHCS (66 values!)
gxhcs_items = [i for i in param_sql_items if 'TSIS_GXHCS' in i['param_codes']]
print(f"\n=== TSIS_GXHCS items (66 values!) ===")
print(f"Count: {len(gxhcs_items)}")
print(f"If expanded: {66 * len(gxhcs_items)} SQL files just for GXHCS")
print(f"Note: GXHCS is a customization parameter for each company - 66 different信托公司")
print(f"  Each company only uses ONE value. So expanding all 66 for each check item")
print(f"  would create many irrelevant SQL scripts.")
print(f"  Alternative: Use URP_PARAM_CONFIG lookup at runtime instead of expanding.")