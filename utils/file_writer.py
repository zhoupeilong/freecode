"""
file_writer.py - 批量写文件模块

按照 100 条/文件的规则，创建子文件夹并写入 SQL 文件。
文件夹命名规则：SUC0001_SUC0100, SUC0101_SUC0200, ...
文件命名规则：SUC0001.sql, SUC0002.sql, ...
"""

import os
from typing import List


class BatchWriter:
    """批量写文件器"""

    def __init__(self, output_root: str, batch_size: int = 100, logger=None):
        """
        初始化批量写文件器。

        Args:
            output_root: 输出根目录（如 ./output_stg_file/）
            batch_size: 每个子文件夹中的文件数量（默认 100）
            logger: Logger 实例（可选）
        """
        self.output_root = output_root
        self.batch_size = batch_size
        self.logger = logger
        self.written_files = []
        self._ensure_root()

    def _ensure_root(self):
        """确保输出根目录存在"""
        if not os.path.exists(self.output_root):
            os.makedirs(self.output_root, exist_ok=True)

    def _get_folder_name(self, index: int) -> str:
        """
        根据序号计算子文件夹名。

        Args:
            index: 1-based 序号

        Returns:
            如 SUC0001_SUC0100
        """
        start = ((index - 1) // self.batch_size) * self.batch_size + 1
        end = start + self.batch_size - 1
        return f"SUC{start:04d}_SUC{end:04d}"

    def _get_sql_filename(self, index: int) -> str:
        """
        获取 SQL 文件名。

        Args:
            index: 1-based 序号

        Returns:
            如 SUC0001.sql
        """
        return f"SUC{index:04d}.sql"

    def write(self, index: int, sql_content: str, check_code: str = "") -> str:
        """
        写入单个 SQL 文件。

        Args:
            index: 1-based 序号
            sql_content: SQL 内容
            check_code: 检查编号（用于日志记录）

        Returns:
            写入的文件完整路径
        """
        folder_name = self._get_folder_name(index)
        filename = self._get_sql_filename(index)

        folder_path = os.path.join(self.output_root, folder_name)
        file_path = os.path.join(folder_path, filename)

        # 确保子文件夹存在
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            if self.logger:
                self.logger.info(f"创建子文件夹: {folder_name}")

        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(sql_content)

        self.written_files.append({
            'index': index,
            'folder': folder_name,
            'filename': filename,
            'check_code': check_code,
            'path': file_path,
        })

        return file_path

    def write_batch(self, sql_list: List[tuple]) -> dict:
        """
        批量写入 SQL 文件。

        Args:
            sql_list: 列表，每个元素为 (check_code, sql_content) 元组

        Returns:
            统计字典，包含 total, folders, files 等
        """
        if self.logger:
            self.logger.info(f"开始批量写入 {len(sql_list)} 个 SQL 文件，批次大小 {self.batch_size}")

        folders = set()

        for i, (check_code, sql_content) in enumerate(sql_list, start=1):
            path = self.write(i, sql_content, check_code)
            folders.add(self._get_folder_name(i))

            if i % self.batch_size == 0 and self.logger:
                self.logger.info(f"已写入文件 {self._get_sql_filename(i)}（第 {i} 条）")

        result = {
            'total': len(sql_list),
            'folders': sorted(folders),
            'files': self.written_files,
        }

        if self.logger:
            self.logger.info(f"写入完成：共 {result['total']} 个文件，分布在 {len(folders)} 个子文件夹")
            for folder in sorted(folders):
                self.logger.info(f"  文件夹: {folder}")

        return result

    def get_summary(self) -> dict:
        """获取写入摘要"""
        return {
            'total': len(self.written_files),
            'folders': sorted(set(f['folder'] for f in self.written_files)),
            'batch_size': self.batch_size,
        }


if __name__ == "__main__":
    # 测试入口
    test_root = os.path.join(os.path.dirname(__file__), "..", "..", "output_stg_file")
    test_root = os.path.abspath(test_root)

    writer = BatchWriter(test_root, batch_size=100)

    # 模拟写入 5 个文件
    test_data = [
        (f"DQ01.A{str(i).zfill(4)}", f"-- 检查编号: DQ01.A{str(i).zfill(4)}\nSELECT * FROM DUAL;\n")
        for i in range(1, 6)
    ]

    result = writer.write_batch(test_data)
    print(f"写入完成：共 {result['total']} 个文件")
    print(f"文件夹列表: {result['folders']}")
    print(f"文件路径示例: {result['files'][0]['path']}")