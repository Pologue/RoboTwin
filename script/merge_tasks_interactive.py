#!/usr/bin/env python3
"""
交互式任务合并助手
通过简单的问答帮助你合并任务

使用方法:
    python script/merge_tasks_interactive.py
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from merge_tasks import TaskMerger
except ImportError:
    print("错误: 无法导入 merge_tasks 模块")
    print("请确保 merge_tasks.py 在同一目录下")
    sys.exit(1)


def list_available_tasks(envs_dir: Path) -> list:
    """列出所有可用的任务"""
    tasks = []
    for file in sorted(envs_dir.glob("*.py")):
        if file.name.startswith('_') or file.name == 'utils.py':
            continue
        tasks.append(file.stem)
    return tasks


def print_tasks_menu(tasks: list, columns: int = 3):
    """以分栏形式打印任务菜单"""
    print("\n可用任务列表:")
    print("=" * 80)
    
    # 分栏显示
    rows = (len(tasks) + columns - 1) // columns
    for i in range(rows):
        row_items = []
        for j in range(columns):
            idx = i + j * rows
            if idx < len(tasks):
                row_items.append(f"{idx+1:3d}. {tasks[idx]:30s}")
        print("  ".join(row_items))
    print("=" * 80)


def select_tasks(tasks: list) -> list:
    """选择要合并的任务"""
    print("\n请选择要合并的任务（输入任务编号，用空格分隔）:")
    print("例如: 1 15 23")
    
    while True:
        user_input = input("\n任务编号: ").strip()
        if not user_input:
            print("❌ 请至少输入一个任务编号")
            continue
        
        try:
            indices = [int(x.strip()) for x in user_input.split()]
            
            # 验证编号
            if any(i < 1 or i > len(tasks) for i in indices):
                print(f"❌ 编号必须在 1 到 {len(tasks)} 之间")
                continue
            
            if len(indices) < 2:
                print("❌ 至少需要选择2个任务进行合并")
                continue
            
            selected_tasks = [tasks[i-1] for i in indices]
            
            # 确认选择
            print(f"\n你选择了以下 {len(selected_tasks)} 个任务:")
            for i, task in enumerate(selected_tasks, 1):
                print(f"  {i}. {task}")
            
            confirm = input("\n确认选择？(y/n): ").strip().lower()
            if confirm == 'y':
                return selected_tasks
            else:
                print("重新选择...")
                
        except ValueError:
            print("❌ 输入格式错误，请输入数字编号，用空格分隔")


def get_output_name(default: str = "") -> str:
    """获取输出任务名"""
    print("\n请输入合并后的任务名称:")
    if default:
        print(f"(按回车使用默认名称: {default})")
    
    while True:
        name = input("\n任务名称: ").strip()
        
        if not name and default:
            return default
        
        if not name:
            print("❌ 任务名称不能为空")
            continue
        
        # 验证名称格式
        if not name.replace('_', '').replace('-', '').isalnum():
            print("❌ 任务名称只能包含字母、数字、下划线和连字符")
            continue
        
        return name


def get_description(selected_tasks: list) -> str:
    """获取任务描述"""
    default_desc = f"依次执行: {', '.join(selected_tasks)}"
    
    print("\n请输入任务描述:")
    print(f"(按回车使用默认描述: {default_desc})")
    
    desc = input("\n描述: ").strip()
    
    if not desc:
        return default_desc
    
    return desc


def confirm_merge(selected_tasks: list, output_name: str, description: str) -> bool:
    """确认合并信息"""
    print("\n" + "=" * 80)
    print("合并任务信息汇总")
    print("=" * 80)
    print(f"\n源任务 ({len(selected_tasks)} 个):")
    for i, task in enumerate(selected_tasks, 1):
        print(f"  {i}. {task}")
    
    print(f"\n输出任务名: {output_name}")
    print(f"任务描述: {description}")
    
    print("\n生成的文件:")
    print(f"  - envs/{output_name}.py")
    print(f"  - description/task_instruction/{output_name}.json")
    
    print("\n" + "=" * 80)
    
    confirm = input("\n确认开始合并？(y/n): ").strip().lower()
    return confirm == 'y'


def main():
    print("=" * 80)
    print(" " * 25 + "交互式任务合并助手")
    print("=" * 80)
    
    # 检测工作区
    workspace_root = Path.cwd()
    envs_dir = workspace_root / "envs"
    
    if not envs_dir.exists():
        print(f"\n❌ 错误: 找不到 envs 目录")
        print(f"当前目录: {workspace_root}")
        print(f"请在 RoboTwin 项目根目录下运行此脚本")
        return 1
    
    print(f"\n工作区: {workspace_root}")
    
    # 列出所有任务
    tasks = list_available_tasks(envs_dir)
    if not tasks:
        print("\n❌ 未找到任何任务文件")
        return 1
    
    print(f"找到 {len(tasks)} 个任务")
    
    # 显示任务菜单
    print_tasks_menu(tasks)
    
    # 选择任务
    selected_tasks = select_tasks(tasks)
    
    # 生成默认输出名称
    default_output_name = "_".join(selected_tasks[:2])
    if len(selected_tasks) > 2:
        default_output_name += "_combined"
    
    # 获取输出名称
    output_name = get_output_name(default_output_name)
    
    # 检查是否已存在
    output_file = envs_dir / f"{output_name}.py"
    if output_file.exists():
        print(f"\n⚠️  警告: 任务 '{output_name}' 已存在")
        overwrite = input("是否覆盖？(y/n): ").strip().lower()
        if overwrite != 'y':
            print("取消操作")
            return 0
    
    # 获取描述
    description = get_description(selected_tasks)
    
    # 确认
    if not confirm_merge(selected_tasks, output_name, description):
        print("\n取消操作")
        return 0
    
    # 执行合并
    print("\n开始合并...")
    merger = TaskMerger(workspace_root=str(workspace_root))
    
    success = merger.merge_tasks(
        task_names=selected_tasks,
        output_task_name=output_name,
        description=description
    )
    
    if success:
        print("\n" + "=" * 80)
        print(" " * 30 + "✓ 合并完成!")
        print("=" * 80)
        
        print("\n📝 后续步骤:")
        print(f"  1. 检查生成的代码: envs/{output_name}.py")
        print(f"     - 解决可能的变量命名冲突")
        print(f"     - 调整 load_actors() 中的 actor 位置")
        print(f"     - 完善 play_once() 中的 info 信息")
        print(f"     - 实现 check_success() 的组合逻辑")
        print(f"\n  2. 完善指令文件: description/task_instruction/{output_name}.json")
        print(f"     - 添加更多的自然语言指令示例")
        print(f"     - 根据需要调整 schema")
        print(f"\n  3. 测试新任务")
        
        return 0
    else:
        print("\n❌ 合并失败")
        return 1


if __name__ == '__main__':
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
        exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
