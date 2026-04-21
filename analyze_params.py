"""Analyze param patterns in my_poor_solution.xlsx inspection sheet"""
import re, openpyxl, json, sys

sys.stdout.reconfigure(encoding='utf-8')

wb = openpyxl.load_workbook('F:/09_opencode/docs/my_poor_solution.xlsx', read_only=True, data_only=True)
ws = wb[wb.sheetnames[0]]

param_codes_in_sql = {}
param_sql_rows = []

for row in ws.iter_rows(min_row=2, values_only=True):
    if row and row[22]:
        sql = str(row[22])
        refs = re.findall(r"param_code\s*=\s*'([^']+)'", sql)
        for p in refs:
            if p not in param_codes_in_sql:
                param_codes_in_sql[p] = 0
            param_codes_in_sql[p] += 1
        if refs:
            alias = str(row[1]) if row[1] else ''
            dm_table = str(row[12]) if row[12] else ''
            dm_field = str(row[13]) if row[13] else ''
            param_sql_rows.append({
                'alias': alias,
                'dm_table': dm_table,
                'dm_field': dm_field,
                'params': list(set(refs)),
                'sql_len': len(sql)
            })

wb.close()

print("=== Param codes in URP_PARAM_CONFIG patterns ===")
print(f"Total unique params: {len(param_codes_in_sql)}")
for p, cnt in sorted(param_codes_in_sql.items(), key=lambda x: -x[1]):
    print(f"  {p}: {cnt} rows")

print(f"\nTotal inspection rows with PARAM patterns: {len(param_sql_rows)}")

single = sum(1 for r in param_sql_rows if len(r['params']) == 1)
multi = sum(1 for r in param_sql_rows if len(r['params']) > 1)
print(f"Single param: {single}, Multiple params: {multi}")

# Show unique param combinations
from collections import Counter
combo_counter = Counter()
for r in param_sql_rows:
    combo = tuple(sorted(r['params']))
    combo_counter[combo] += 1

print("\n=== Param combinations (top 20) ===")
for combo, cnt in combo_counter.most_common(20):
    print(f"  {combo}: {cnt} rows")

# Show 5 complete examples
print("\n=== Sample SQL templates with PARAM (first 5) ===")
for r in param_sql_rows[:5]:
    print(f"\n{r['alias']} | {r['dm_table']}.{r['dm_field']} | params={r['params']}")
    alias = r['alias']
    # Read the actual SQL
    wb2 = openpyxl.load_workbook('F:/09_opencode/docs/my_poor_solution.xlsx', read_only=True, data_only=True)
    ws2 = wb2[wb2.sheetnames[0]]
    for row in ws2.iter_rows(min_row=2, values_only=True):
        if row and row[1] and str(row[1]) == alias:
            sql_text = str(row[22])[:500] if row[22] else ''
            print(f"  SQL: {sql_text}")
            break
    wb2.close()