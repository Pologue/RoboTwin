#!/usr/bin/env python3
"""
任务合并工具脚本
用于将多个单一任务合并成一个复合任务

使用方法:
    python script/merge_tasks.py --tasks task1 task2 task3 --output combined_task --description "任务描述"

示例:
    python script/merge_tasks.py --tasks adjust_bottle stack_blocks_three --output adjust_and_stack --description "先调整瓶子，然后堆叠方块"
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
import textwrap


class TaskMerger:
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root)
        self.envs_dir = self.workspace_root / "envs"
        self.task_instruction_dir = self.workspace_root / "description" / "task_instruction"
        
    def load_task_code(self, task_name: str) -> str:
        """加载任务的Python代码"""
        task_file = self.envs_dir / f"{task_name}.py"
        if not task_file.exists():
            raise FileNotFoundError(f"任务文件不存在: {task_file}")
        return task_file.read_text()
    
    def load_task_instruction(self, task_name: str) -> Dict[str, Any]:
        """加载任务的指令JSON"""
        instruction_file = self.task_instruction_dir / f"{task_name}.json"
        if not instruction_file.exists():
            raise FileNotFoundError(f"指令文件不存在: {instruction_file}")
        with open(instruction_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def extract_class_info(self, task_code: str, task_name: str) -> Dict[str, Any]:
        """从任务代码中提取关键信息"""
        info = {
            'imports': [],
            'load_actors_code': '',
            'play_once_code': '',
            'check_success_code': '',
            'helper_functions': [],
            'class_attributes': []
        }
        
        # 提取import语句（除了基类导入）
        import_pattern = r'^(from\s+\.|import\s+).*$'
        for line in task_code.split('\n'):
            if re.match(import_pattern, line) and 'Base_Task' not in line:
                info['imports'].append(line)
        
        # 提取load_actors方法
        load_actors_match = re.search(
            r'def load_actors\(self\):(.*?)(?=\n    def |\nclass |\Z)',
            task_code,
            re.DOTALL
        )
        if load_actors_match:
            info['load_actors_code'] = load_actors_match.group(1).strip()
        
        # 提取play_once方法
        play_once_match = re.search(
            r'def play_once\(self\):(.*?)(?=\n    def |\nclass |\Z)',
            task_code,
            re.DOTALL
        )
        if play_once_match:
            info['play_once_code'] = play_once_match.group(1).strip()
        
        # 提取check_success方法
        check_success_match = re.search(
            r'def check_success\(self\):(.*?)(?=\n    def |\nclass |\Z)',
            task_code,
            re.DOTALL
        )
        if check_success_match:
            info['check_success_code'] = check_success_match.group(1).strip()
        
        # 提取辅助函数（类中定义的其他方法，除了标准方法）
        standard_methods = ['setup_demo', 'load_actors', 'play_once', 'check_success', 'stage_reward', '__init__']
        # 找到所有的方法定义
        method_pattern = r'    def (\w+)\(self.*?\):(.*?)(?=\n    def |\nclass |\Z)'
        for match in re.finditer(method_pattern, task_code, re.DOTALL):
            method_name = match.group(1)
            if method_name not in standard_methods:
                method_full_code = match.group(0)
                info['helper_functions'].append({
                    'name': method_name,
                    'code': method_full_code
                })
        
        return info
    
    def generate_merged_task_code(
        self,
        output_task_name: str,
        task_infos: List[Dict[str, Any]],
        task_names: List[str],
        description: str
    ) -> str:
        """生成合并后的任务代码"""
        
        # 收集所有独特的import
        all_imports = set()
        for info in task_infos:
            all_imports.update(info['imports'])
        
        imports_str = '\n'.join(sorted(all_imports))
        
        # 生成代码
        code = f'''from ._base_task import Base_Task
from .utils import *
import sapien
import math
{imports_str}


class {output_task_name}(Base_Task):
    """
    复合任务: {description}
    
    包含以下子任务:
    {chr(10).join(f"    - {name}" for name in task_names)}
    """

    def setup_demo(self, **kwags):
        super()._init_task_env_(**kwags)

    def load_actors(self):
        """加载所有子任务的actors"""
'''
        
        # 合并load_actors代码
        for i, (task_name, info) in enumerate(zip(task_names, task_infos)):
            code += f"\n        # ========== 子任务 {i+1}: {task_name} ==========\n"
            # 为每个子任务的变量添加前缀以避免冲突
            load_actors_code = info['load_actors_code']
            # 这里可以添加变量重命名逻辑，但为了简单起见，先保持原样
            code += self._indent_code(load_actors_code, 0) + "\n"
        
        code += '''
    def play_once(self):
        """依次执行所有子任务"""
        
'''
        
        # 合并play_once代码
        for i, (task_name, info) in enumerate(zip(task_names, task_infos)):
            code += f"        # ========== 执行子任务 {i+1}: {task_name} ==========\n"
            play_once_code = info['play_once_code']
            # 处理return语句，除了最后一个
            if i < len(task_names) - 1:
                play_once_code = re.sub(r'return\s+self\.info', '# return self.info', play_once_code)
            code += self._indent_code(play_once_code, 0) + "\n\n"
        
        code += '''        return self.info

'''
        
        # 添加辅助函数
        helper_functions_added = set()
        for i, (task_name, info) in enumerate(zip(task_names, task_infos)):
            if info['helper_functions']:
                code += f"    # ========== 辅助函数 from {task_name} ==========\n"
                for helper_func in info['helper_functions']:
                    func_name = helper_func['name']
                    # 避免重复添加同名函数
                    if func_name not in helper_functions_added:
                        code += helper_func['code'] + "\n\n"
                        helper_functions_added.add(func_name)
        
        code += '''    def check_success(self):
        """检查所有子任务是否成功"""
        # 需要手动实现组合逻辑
        # 以下是各个子任务的成功检查代码，需要根据实际情况组合
        
'''
        
        for i, (task_name, info) in enumerate(zip(task_names, task_infos)):
            code += f"        # 子任务 {i+1}: {task_name}\n"
            check_code = info['check_success_code']
            code += f"        # {check_code}\n\n"
        
        code += '''        # TODO: 实现组合的成功检查逻辑
        return True
'''
        
        return code
    
    def _indent_code(self, code: str, indent: int) -> str:
        """添加缩进"""
        lines = code.split('\n')
        return '\n'.join(' ' * indent + line if line.strip() else line for line in lines)
    
    def generate_merged_instruction(
        self,
        task_instructions: List[Dict[str, Any]],
        task_names: List[str],
        description: str
    ) -> Dict[str, Any]:
        """生成合并后的指令JSON"""
        
        # 组合所有的schema
        schemas = []
        for i, (task_name, instruction) in enumerate(zip(task_names, task_instructions)):
            schema = instruction.get('schema', '')
            # 为每个子任务的变量添加索引前缀
            schemas.append(f"Task{i+1}: {schema}")
        
        combined_schema = "; ".join(schemas)
        
        # 组合描述
        full_descriptions = [inst.get('full_description', '') for inst in task_instructions]
        combined_description = f"{description}. " + " Then ".join(full_descriptions)
        
        # 生成一些基础指令示例
        seen_instructions = [
            f"Complete the combined task: {description}",
            f"Perform all subtasks in sequence",
            f"Execute the multi-step task",
        ]
        
        # 从原始任务中提取一些指令并组合
        for i, inst in enumerate(task_instructions):
            original_seen = inst.get('seen', [])
            if original_seen and len(original_seen) > 0:
                seen_instructions.append(f"Step {i+1}: {original_seen[0]}")
        
        return {
            "full_description": combined_description,
            "schema": combined_schema,
            "preference": "num of words should not exceed 25",
            "seen": seen_instructions
        }
    
    def merge_tasks(
        self,
        task_names: List[str],
        output_task_name: str,
        description: str
    ):
        """合并多个任务"""
        
        print(f"开始合并 {len(task_names)} 个任务...")
        
        # 加载所有任务信息
        task_infos = []
        task_instructions = []
        
        for task_name in task_names:
            print(f"  加载任务: {task_name}")
            try:
                task_code = self.load_task_code(task_name)
                task_info = self.extract_class_info(task_code, task_name)
                task_infos.append(task_info)
                
                task_instruction = self.load_task_instruction(task_name)
                task_instructions.append(task_instruction)
            except Exception as e:
                print(f"    错误: {e}")
                return False
        
        # 生成合并后的代码
        print(f"\n生成合并任务代码: {output_task_name}")
        merged_code = self.generate_merged_task_code(
            output_task_name,
            task_infos,
            task_names,
            description
        )
        
        # 生成合并后的指令
        print(f"生成合并任务指令")
        merged_instruction = self.generate_merged_instruction(
            task_instructions,
            task_names,
            description
        )
        
        # 保存文件
        output_code_file = self.envs_dir / f"{output_task_name}.py"
        output_instruction_file = self.task_instruction_dir / f"{output_task_name}.json"
        
        print(f"\n保存文件:")
        print(f"  代码: {output_code_file}")
        with open(output_code_file, 'w', encoding='utf-8') as f:
            f.write(merged_code)
        
        print(f"  指令: {output_instruction_file}")
        with open(output_instruction_file, 'w', encoding='utf-8') as f:
            json.dump(merged_instruction, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ 任务合并完成!")
        print(f"\n⚠️  注意事项:")
        print(f"  1. 请检查生成的代码，特别是变量命名冲突问题")
        print(f"  2. 请实现 check_success() 方法的组合逻辑")
        print(f"  3. 请根据需要调整 load_actors() 中的actor位置，避免碰撞")
        print(f"     - 如果有物体会挡住其他任务的运动路径，请调整物体的生成位置")
        print(f"     - 可以使用add_prohibit_area()来标记已占用区域")
        print(f"     - 生成位置时检查与已有物体的距离，避免重叠")
        print(f"  4. 请根据实际需求完善 task_instruction JSON 中的指令示例")
        print(f"  5. play_once() 中的 self.info 需要合理组合各子任务的信息")
        print(f"  6. 如果涉及桌子偏移（table_xy_bias），请确保所有物体位置都相应调整")
        print(f"  7. 注意检查不同任务在setup_demo中的参数（如table_xy_bias）是否兼容")
        
        return True


def main():
    parser = argparse.ArgumentParser(
        description='合并多个RoboTwin任务成一个复合任务',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
        示例:
          # 合并两个任务
          python script/merge_tasks.py --tasks adjust_bottle_true stack_blocks_three \\
              --output adjust_and_stack \\
              --description "先调整瓶子然后堆叠方块"
          
          # 合并三个任务
          python script/merge_tasks.py --tasks task1 task2 task3 \\
              --output combined_task \\
              --description "执行三个任务的组合"
        ''')
    )
    
    parser.add_argument(
        '--tasks',
        nargs='+',
        required=True,
        help='要合并的任务名称列表（不含.py后缀）'
    )
    
    parser.add_argument(
        '--output',
        required=True,
        help='输出的合并任务名称（不含.py后缀）'
    )
    
    parser.add_argument(
        '--description',
        required=True,
        help='合并任务的描述'
    )
    
    parser.add_argument(
        '--workspace',
        default='.',
        help='工作区根目录路径（默认: 当前目录）'
    )
    
    args = parser.parse_args()
    
    # 创建合并器
    merger = TaskMerger(workspace_root=args.workspace)
    
    # 执行合并
    success = merger.merge_tasks(
        task_names=args.tasks,
        output_task_name=args.output,
        description=args.description
    )
    
    if success:
        return 0
    else:
        return 1


if __name__ == '__main__':
    exit(main())
