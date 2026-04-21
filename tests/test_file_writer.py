"""Test file_writer module"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from utils.file_writer import BatchWriter

test_root = os.path.join(os.path.dirname(__file__), '..', '..', 'output_stg_file')
test_root = os.path.abspath(test_root)

writer = BatchWriter(test_root, batch_size=100)
test_data = [
    ('DQ01.A{:04d}'.format(i), '-- 检查编号: DQ01.A{:04d}\nSELECT * FROM DUAL;\n'.format(i))
    for i in range(1, 6)
]
result = writer.write_batch(test_data)
print('Written: {} files'.format(result['total']))
print('Folders: {}'.format(result['folders']))
for f in result['files'][:3]:
    print('  Path: {}'.format(f['path']))
    print('  Exists: {}'.format(os.path.exists(f['path'])))