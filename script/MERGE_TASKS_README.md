# 任务合并工具使用说明

这个工具帮助你将多个单一任务合并成一个复合任务。提供了两种使用方式：

## 方式1: 交互式合并（推荐）

最简单的方式，通过问答来完成合并：

```bash
cd /home/pologue/distroboxhome/ubuntu/RoboTwin
python script/merge_tasks_interactive.py
```

### 交互流程：

1. **查看任务列表** - 脚本会显示所有可用任务
2. **选择任务** - 输入要合并的任务编号（用空格分隔）
3. **输入名称** - 为合并后的任务命名
4. **输入描述** - 描述合并任务的功能
5. **确认执行** - 确认信息后开始生成

### 示例：

```
可用任务列表:
  1. adjust_bottle            2. stack_blocks_three       3. click_alarmclock
  ...

请选择要合并的任务（输入任务编号，用空格分隔）:
任务编号: 1 2

请输入合并后的任务名称:
任务名称: adjust_and_stack

请输入任务描述:
描述: 先调整瓶子然后堆叠方块

确认开始合并？(y/n): y
```

## 方式2: 命令行合并

如果你知道具体任务名称，可以直接使用命令行：

```bash
cd /home/pologue/distroboxhome/ubuntu/RoboTwin

# 基本用法
python script/merge_tasks.py \
    --tasks adjust_bottle_true stack_blocks_three \
    --output adjust_and_stack \
    --description "先调整瓶子然后堆叠方块"

# 合并多个任务
python script/merge_tasks.py \
    --tasks task1 task2 task3 \
    --output combined_task \
    --description "执行三个任务的组合"
```

### 参数说明：

- `--tasks`: 要合并的任务名称列表（空格分隔）
- `--output`: 输出的任务名称
- `--description`: 任务描述
- `--workspace`: 工作区路径（可选，默认当前目录）

## 生成的文件

运行脚本后会生成两个文件：

1. **envs/{output_name}.py** - 任务Python代码
2. **description/task_instruction/{output_name}.json** - 任务指令JSON

## ⚠️ 重要：后续手动调整

脚本只能自动化基础合并，你需要手动完成以下工作：

### 1. 检查代码文件 (envs/xxx.py)

#### a) 解决变量命名冲突
```python
# 如果多个子任务使用了相同的变量名，需要重命名
# 例如：self.bottle, self.block 等
```

#### b) 调整actor位置
```python
def load_actors(self):
    # 子任务1的actors
    self.bottle = rand_create_actor(xlim=[-0.3, -0.1], ...)
    
    # 子任务2的actors - 确保位置不冲突！
    self.block1 = create_box(xlim=[0.1, 0.3], ...)  # 调整位置
```

#### c) 完善play_once()
```python
def play_once(self):
    # 执行子任务1
    # ...
    
    # 合并info信息
    self.info["info"] = {
        # 子任务1的info
        "{A}": "bottle_info",
        "{a}": str(arm_tag1),
        # 子任务2的info
        "{B}": "block_info",
        "{b}": str(arm_tag2),
    }
    return self.info
```

#### d) 实现check_success()
```python
def check_success(self):
    # 组合各子任务的成功条件
    task1_success = (条件1)
    task2_success = (条件2)
    
    return task1_success and task2_success
```

### 2. 完善指令文件 (description/task_instruction/xxx.json)

```json
{
  "full_description": "完整的任务描述",
  "schema": "变量说明",
  "preference": "生成指令的偏好设置",
  "seen": [
    "添加更多自然语言指令示例",
    "Use {a} to do task1, then use {b} to do task2",
    "..."
  ]
}
```

### 3. 测试新任务

```bash
# 使用你的测试命令测试新任务
# 例如：
python collect_data.sh --task your_new_task
```

## 示例：合并两个任务

### 输入任务：

1. **adjust_bottle_true**: 抓取并调整瓶子位置
2. **stack_blocks_three**: 堆叠三个方块

### 运行命令：

```bash
python script/merge_tasks_interactive.py
# 或
python script/merge_tasks.py \
    --tasks adjust_bottle_true stack_blocks_three \
    --output adjust_then_stack \
    --description "先调整瓶子到正确位置，然后堆叠三个方块"
```

### 生成的代码结构：

```python
class adjust_then_stack(Base_Task):
    def load_actors(self):
        # 子任务1的actors
        self.bottle = ...
        
        # 子任务2的actors
        self.block1 = ...
        self.block2 = ...
        self.block3 = ...
    
    def play_once(self):
        # 执行子任务1
        # 调整瓶子...
        
        # 执行子任务2
        # 堆叠方块...
        
        return self.info
    
    def check_success(self):
        # TODO: 需要手动实现
        return True
```

## 常见问题

### Q: 为什么不能完全自动化？

A: 任务合并涉及复杂的逻辑：
- 变量可能冲突
- Actor位置需要合理规划避免碰撞
- 成功条件的组合逻辑因任务而异
- 每个任务的语义不同，无法自动推断组合方式

### Q: 如何避免actor碰撞？

A: 在`load_actors()`中调整位置参数：

```python
# 将不同子任务的actors放在不同区域
# 子任务1: 左侧
xlim=[-0.3, -0.1]

# 子任务2: 右侧  
xlim=[0.1, 0.3]
```

### Q: 合并后的任务可以再次合并吗？

A: 可以！合并后的任务就是一个普通任务，可以继续参与合并。

### Q: 如何处理info字段冲突？

A: 使用不同的键名：

```python
self.info["info"] = {
    # 任务1
    "{A1}": "task1_object",
    "{a1}": "task1_arm",
    # 任务2
    "{A2}": "task2_object", 
    "{a2}": "task2_arm",
}
```

## 减少人工工作量的建议

1. **选择兼容的任务** - 选择actor类型和数量相似的任务合并
2. **分阶段合并** - 先合并简单的两个任务，测试后再继续
3. **复用成功的模板** - 记录成功的合并模式，后续复用
4. **使用代码生成工具** - 对于重复性高的部分，可以编写额外脚本

## 支持

如果遇到问题，请检查：
1. 任务文件是否存在于 `envs/` 目录
2. 指令文件是否存在于 `description/task_instruction/` 目录
3. Python环境是否正确
