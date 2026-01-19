# RoboTwin 2.0 架构详解：MLLM、代码生成、轨迹规划的关系

## 核心结论
**你的理解有个关键误区**：RoboTwin 2.0 **在采集数据时不使用MLLM生成可执行代码**。MLLM只用于：
1. 生成**任务描述**（task descriptions）
2. 分析**执行过程**（observation analysis）
3. 辅助开发者**生成新任务代码模板**（code_gen工具）

**采集时使用的代码是手工编写的任务类**（如 `beat_block_hammer.py`），不是动态生成的。

---

## 1. 三层架构解析

### 第一层：手工编写的任务基类 (envs/)
```
envs/
├── _base_task.py          # 基础类，包含所有API
├── beat_block_hammer.py   # 具体任务类（开发者手写）
├── adjust_bottle.py       # 具体任务类（开发者手写）
└── ... 其他50个任务

```

**特点**：
- 每个任务 `play_once()` 是**静态Python代码**
- **不是由MLLM生成**，而是**开发者手工编写**
- MLLM只在开发工具（code_gen）中提供辅助

### 第二层：基础API和轨迹规划 (_base_task.py)
关键API形成一个调用链：

```
move()  ← 最高层，用户接口
  ↓
├─ move_to_pose() → left_move_to_pose() / right_move_to_pose()
│                    ↓
│                    robot.left_plan_path()  [TOPPRA轨迹优化]
│
├─ grasp_actor() → choose_grasp_pose() → get_grasp_pose()
│                    ↓
│                    contact point分析 + TOPPRA规划
│
└─ place_actor() → get_place_pose()
                    ↓
                    目标pose计算 + TOPPRA规划
                    
↓ (都汇聚到)

take_dense_action()  ← 底层执行引擎
  ↓
  ├─ robot.set_arm_joints()   [设置关节位置/速度]
  ├─ robot.set_gripper()       [设置夹爪]
  ├─ scene.step()              [SAPIEN物理仿真一步]
  └─ _take_picture()           [保存观测帧]
```

### 第三层：MLLM工具（code_gen/）- 仅用于辅助开发
```
code_gen/
├── gpt_agent.py            # LLM API调用（DeepSeek/GPT-4/Kimi）
├── task_generation.py      # 新任务代码生成工具
├── observation_agent.py    # 执行分析工具（分析失败的run）
└── prompt.py               # 提示词模板

```

**使用场景**：
- 当你想**创建一个新任务类**时，可以运行 `task_generation.py` 
- 它会调用 LLM 帮你生成 `play_once()` 的初始代码骨架
- 但**不是采集时动态生成**，而是**开发时生成文件**

---

## 2. `move()`, `grasp_actor()`, `place_actor()` 的关系

### 函数调用关系详解

#### `move(actions_by_arm1, actions_by_arm2)` 
**作用**：高层API，根据Action列表执行多个动作

```python
# 例子：在 beat_block_hammer.py 中
arm_tag = ArmTag("left")
self.move(self.grasp_actor(self.hammer, arm_tag=arm_tag, ...))
# → 执行grasp_actor返回的Action列表
```

**返回值**：`(arm_tag, [Action对象列表])`

```python
class Action:
    arm_tag: str              # "left" 或 "right"
    action: str               # "move", "close", "open"
    target_pose: list[7]      # 目标末端执行器pose (x,y,z,qx,qy,qz,qw)
    target_gripper_pos: float # 夹爪位置 0=闭 1=开
```

---

#### `grasp_actor(actor, arm_tag, pre_grasp_dis, grasp_dis, ...)`
**作用**：从**对象的接触点**计算抓取轨迹

1. **获取抓取点**：
   - 读取 `actor.config["contact_points_pose"]`（在模型资产中标注）
   - 例如锤子的握柄位置

2. **计算pre-grasp姿态**（靠近但未接触）：
   ```python
   contact_matrix = actor.get_contact_point(contact_point_id, "matrix")
   global_contact_pose_matrix = contact_matrix @ rotation_matrix
   global_grasp_pose_p = contact_point_3d + pre_dis * approach_direction
   ```

3. **轨迹规划**：
   ```python
   pre_grasp_pose, grasp_pose = self.choose_grasp_pose(...)
   # → 调用 robot.left_plan_path(pre_grasp_pose) [TOPPRA]
   ```

4. **返回Action列表**：
   ```python
   return arm_tag, [
       Action(arm_tag, "move", target_pose=pre_grasp_pose),   # 靠近
       Action(arm_tag, "move", target_pose=grasp_pose, ...),  # 接触
       Action(arm_tag, "close", target_gripper_pos=0.0),      # 关闭夹爪
   ]
   ```

**关键**：grasp_actor **不执行**动作，只**计算并返回**Action列表。由 `move()` 执行。

---

#### `place_actor(actor, arm_tag, target_pose, ...)`
**作用**：计算放置轨迹（与grasp_actor类似）

1. **计算放置姿态**：
   ```python
   place_start_pose = actor.get_functional_point(functional_point_id, "pose")
   # 计算放置位置和方向，使对象与目标target_pose对齐
   place_pose = get_place_pose(place_start_pose, target_pose, ...)
   ```

2. **返回Action列表**：
   ```python
   return arm_tag, [
       Action(arm_tag, "move", target_pose=place_pre_pose),  # 接近
       Action(arm_tag, "move", target_pose=place_pose),      # 到达
       Action(arm_tag, "open", target_gripper_pos=1.0),      # 打开夹爪
   ]
   ```

---

#### `move_by_displacement(arm_tag, x, y, z, ...)`
**作用**：相对运动（基于当前末端执行器位置）

```python
origin_pose = self.robot.get_left_ee_pose()  # 当前位置
displacement = np.array([x, y, z])
new_pose = origin_pose + displacement
return arm_tag, [Action(arm_tag, "move", target_pose=new_pose)]
```

---

### 完整执行流程（beat_block_hammer 例子）

```python
def play_once(self):
    block_pose = self.block.get_functional_point(0, "pose").p
    arm_tag = ArmTag("left" if block_pose[0] < 0 else "right")
    
    # 步骤1：抓取
    self.move(
        self.grasp_actor(
            self.hammer,           # 要抓取的对象
            arm_tag=arm_tag,       # 选择手臂
            pre_grasp_dis=0.12,    # 靠近距离
            grasp_dis=0.01,        # 接触距离
        )
    )
    # ↓ 内部流程：
    # 1. grasp_actor() 计算出抓取轨迹 [pre_grasp_Action, grasp_Action, close_Action]
    # 2. move() 逐个执行这些Action
    #    a. 对每个Action调用 left_move_to_pose() 或 set_gripper()
    #    b. 这些函数调用 robot.left_plan_path() 做TOPPRA轨迹规划
    #    c. 得到 {"position": [...], "velocity": [...]}
    #    d. take_dense_action() 逐步（step by step）执行
    #    e. 每步都调用 _take_picture() 保存观测
    
    # 步骤2：上抬
    self.move(
        self.move_by_displacement(arm_tag, z=0.07, move_axis="arm")
    )
    # ↓ 相对运动，当前位置上抬7cm
    
    # 步骤3：放置
    self.move(
        self.place_actor(
            self.hammer,
            target_pose=self.block.get_functional_point(1, "pose"),
            arm_tag=arm_tag,
            pre_dis=0.06,
        )
    )
    # ↓ 计算放置轨迹，执行
    
    return self.info
```

---

## 3. MLLM在哪里？为什么没设置API key？

### MLLM 的实际用途

#### 用途1：生成任务描述（后处理）
```python
# description/gen_episode_instructions.sh
# 运行后，调用 MLLM API 生成自然语言指令
# 输出：instructions.json
# 例如："Pick up the hammer with left arm and place on the blue block"
```

**API key 需求**：✓ 需要（在 code_gen/gpt_agent.py 中设置）

#### 用途2：代码生成工具（开发辅助）
```python
# code_gen/task_generation.py
# 用途：帮助开发者快速生成新任务代码骨架

# 使用流程：
# 1. python code_gen/task_generation.py  # 启动交互式生成
# 2. 输入任务描述和对象列表
# 3. MLLM 生成 envs_gen/gpt_<task_name>.py
# 4. 开发者手动检查和修改
# 5. 通过后放入 envs/ 目录

# 例子生成的代码：
class gpt_new_task(base_task_class):
    def play_once(self):
        self.move(self.grasp_actor(...))
        self.move(self.move_by_displacement(...))
        self.move(self.place_actor(...))
        return self.info
```

**API key 需求**：✓ 需要（在 code_gen/gpt_agent.py 中设置）

#### 用途3：观察分析（调试）
```python
# code_gen/observation_agent.py
# 用途：分析失败的run，给出建议

# 使用流程：
# 1. run失败，保存了step-by-step的图像
# 2. observation_agent.py 读取图像
# 3. 调用 MLLM vision API 分析"为什么失败"
# 4. 输出建议给开发者
```

**API key 需求**：✓ 需要（使用 Kimi vision API）

### 为什么采集时没设API key？

**核心原因**：**采集不需要MLLM**

```python
# collect_data.sh → script/collect_data.py
# 执行流程：
# 1. 加载 envs/beat_block_hammer.py（已存在的任务类）
# 2. 调用 play_once() 执行任务逻辑
# 3. 保存轨迹、观测、视频
# 4. （可选）调用 description/gen_episode_instructions.sh 生成语言指令
```

**没有MLLM的参与**，所以不需要API key！

---

## 4. 函数调用链的完整映射

```
用户任务代码 (beat_block_hammer.py)
    ↓
move(grasp_actor(...)) 或 move(place_actor(...)) 或 move(move_by_displacement(...))
    ↓
move() 遍历Action列表
    ├─ if action == "move":
    │   ├─ left_move_to_pose() / right_move_to_pose()
    │   │   ├─ robot.left_plan_path() / robot.right_plan_path() [TOPPRA轨迹优化]
    │   │   │   └─ 返回 {"position": np.array(...), "velocity": np.array(...)}
    │   │   └─ 存入 left_joint_path 或 right_joint_path
    │   └─ take_dense_action(control_seq)
    │       └─ 逐步执行：
    │           ├─ robot.set_arm_joints(position[t], velocity[t])
    │           ├─ scene.step() [物理仿真]
    │           └─ _take_picture() [保存观测]
    │
    └─ if action == "close"/"open":
        ├─ set_gripper()
        │   └─ robot.left/right_plan_grippers() [夹爪规划]
        └─ take_dense_action(control_seq)
            └─ 逐步执行：
                ├─ robot.set_gripper(value)
                ├─ scene.step()
                └─ _take_picture()
```

---

## 5. 总结：MLLM 在 RoboTwin 中的角色

| 阶段 | 使用MLLM | 组件 | 需要API Key | 作用 |
|-----|---------|------|-----------|-----|
| **开发** | ✓ | code_gen/task_generation.py | ✓ | 生成新任务代码骨架 |
| **开发（调试）** | ✓ | code_gen/observation_agent.py | ✓ | 分析执行失败原因 |
| **采集（轨迹规划）** | ✗ | envs/_base_task.py | ✗ | 使用TOPPRA做轨迹优化 |
| **采集（执行）** | ✗ | envs/beat_block_hammer.py | ✗ | 执行手工编写的任务代码 |
| **后处理** | ✓ | description/gen_episode_instructions.sh | ✓ | 生成任务指令 |

---

## 6. 论文中的"MLLM生成代码"是什么意思？

论文指的是：**RoboTwin提供了一个工具链，可以用MLLM辅助生成新任务代码**，而不是说采集时MLLM在动态生成代码。

具体工作流程：
1. 人类定义任务（"把锤子放在积木上"）
2. 运行code_gen工具，MLLM生成初始代码
3. **人类手动验证和修改代码**
4. 验证通过后，用修改后的代码采集数据

**这是一个开发工具，不是运行时组件**。

