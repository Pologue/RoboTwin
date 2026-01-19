# 相机配置指南

## 相机系统概述

RoboTwin系统包含以下几种相机：

### 1. **静态相机（Static Cameras）**
在embodiment配置文件中定义（如`assets/embodiments/aloha-agilex/config.yml`）

默认配置的静态相机：
- **head_camera**: 头部相机，位于机器人上方
  - 位置: [-0.032, -0.45, 1.35]
  - 朝向: 向前下方看
  
- **front_camera**: 前置相机，位于机器人前方
  - 位置: [0, -0.45, 0.85]
  - 朝向: 向前看，略微向下倾斜

### 2. **腕部相机（Wrist Cameras）**
动态跟随机械臂末端
- **left_camera**: 左手腕相机
- **right_camera**: 右手腕相机

### 3. **观察相机（Observer Camera）**
用于可视化和调试
- **observer_camera**: 第三人称视角相机

### 4. **世界点云相机（World PCD Cameras）**
用于生成世界坐标系下的点云
- **world_camera1**: 位置 [0.4, -0.4, 1.6]
- **world_camera2**: 位置 [-0.4, -0.4, 1.6]

## 如何添加自定义相机

### 方法1: 修改embodiment配置（推荐）

编辑 `assets/embodiments/<your_embodiment>/config.yml`：

```yaml
static_camera_list: 
- name: head_camera
  type: D435  # 或 L515, Large_D435, Large_L515
  position: [-0.032, -0.45, 1.35]  # [x, y, z]
  forward: [0, 0.6, -0.8]  # 向前方向向量
  left: [-1, 0, 0]  # 向左方向向量

- name: front_camera
  type: D435
  position: [0, -0.45, 0.85]
  forward: [0, 1, -0.1]
  left: [-1, 0, 0]

# 添加你的自定义相机
- name: top_view_camera
  type: Large_D435
  position: [0, 0, 2.0]  # 正上方
  forward: [0, 0, -1]  # 向下看
  left: [-1, 0, 0]  # 左方向

- name: side_camera
  type: D435
  position: [0.8, 0, 1.0]  # 侧面
  forward: [-1, 0, 0]  # 向左看
  left: [0, 1, 0]  # 左方向（实际是前方）
```

### 方法2: 在代码中动态添加

在任务的`load_actors()`方法中添加相机：

```python
def load_actors(self):
    # 你的其他actor加载代码...
    
    # 添加自定义相机
    custom_camera = self.scene.add_camera(
        name="my_custom_camera",
        width=640,
        height=480,
        fovy=np.deg2rad(37),  # 视场角
        near=0.1,
        far=100,
    )
    
    # 设置相机位置和朝向
    cam_pos = np.array([0.5, -0.5, 1.5])
    cam_forward = np.array([-1, 1, -1])
    cam_left = np.array([-1, -1, 0])
    cam_up = np.cross(cam_forward, cam_left)
    
    mat44 = np.eye(4)
    mat44[:3, :3] = np.stack([cam_forward, cam_left, cam_up], axis=1)
    mat44[:3, 3] = cam_pos
    
    custom_camera.entity.set_pose(sapien.Pose(mat44))
    
    # 将相机添加到列表中以便后续使用
    self.static_camera_list.append(custom_camera)
    self.static_camera_name.append("my_custom_camera")
```

## 相机类型配置

相机类型在 `task_config/_camera_config.yml` 中定义：

```yaml
L515:
  fovy: 45  # 视场角（度）
  w: 320    # 宽度（像素）
  h: 180    # 高度（像素）

D435:
  fovy: 37
  w: 320
  h: 240

Large_D435:
  fovy: 37
  w: 640
  h: 480

Large_L515:
  fovy: 45
  w: 640
  h: 360
```

### 添加自定义相机类型

编辑 `task_config/_camera_config.yml`：

```yaml
# 添加你的自定义相机类型
CustomWide:
  fovy: 60  # 更宽的视场角
  w: 1280
  h: 720

CustomTele:
  fovy: 20  # 窄视场角（望远效果）
  w: 1920
  h: 1080
```

## 坐标系说明

### 位置坐标（position）
- **x轴**: 正方向为机器人右侧
- **y轴**: 正方向为机器人前方
- **z轴**: 正方向为上方

### 方向向量
- **forward**: 相机朝向（必须归一化）
- **left**: 相机左方向（必须归一化）
- **up**: 相机上方向（自动计算为 forward × left）

## 使用相机数据

### 获取RGB图像
```python
rgb_dict = self.camera.get_rgb()
# rgb_dict = {
#     'left_camera': {'rgb': array(...)}
#     'right_camera': {'rgb': array(...)}
#     'head_camera': {'rgb': array(...)}
#     ...
# }
```

### 获取深度图
```python
depth_dict = self.camera.get_depth()
```

### 获取点云
```python
# 从head相机获取点云
pcd = self.camera.get_pcd()

# 从世界相机获取点云
world_pcd = self.camera.get_world_pcd()
```

### 获取相机参数
```python
config_dict = self.camera.get_config()
# config_dict包含每个相机的:
# - intrinsic_cv: 相机内参矩阵
# - extrinsic_cv: 相机外参矩阵  
# - cam2world_gl: 相机到世界坐标系的变换矩阵
```

## 实用技巧

### 1. 调试相机位置
使用observer_camera查看场景，调整自定义相机位置：
```python
observer_rgb = self.camera.get_observer_rgb()
```

### 2. 多角度覆盖
建议至少有3个不同角度的相机：
- 上方俯视（top-down）
- 前方水平（front）  
- 侧面45度（side）

### 3. 避免遮挡
- 静态相机应该避开机械臂的主要运动区域
- 相机位置y < -0.4通常比较安全（在机器人后方）
- 高度z > 1.2可以获得更好的视野

### 4. 相机同步
所有相机在每次`update_picture()`调用时同步拍摄，确保多视角图像的时间一致性。

## 相关文件
- 相机实现: `envs/camera/camera.py`
- 相机类型配置: `task_config/_camera_config.yml`
- Embodiment配置: `assets/embodiments/<name>/config.yml`
- 示例任务: `envs/` 下的任何任务文件
