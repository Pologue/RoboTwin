from ._base_task import Base_Task
from .utils import *
import sapien
import math
from .utils import *
import math
import sapien


class click_alarmclock_click_bell(Base_Task):
    """
    复合任务: 依次执行: click_alarmclock, click_bell
    
    包含以下子任务:
        - click_alarmclock
    - click_bell
    """

    def setup_demo(self, **kwags):
        super()._init_task_env_(**kwags)

    def load_actors(self):
        """加载所有子任务的actors"""

        # ========== 子任务 1: click_alarmclock ==========
        rand_pos = rand_pose(
                    xlim=[-0.25, 0.25],
                    ylim=[-0.2, 0.0],
                    qpos=[0.5, 0.5, 0.5, 0.5],
                    rotate_rand=True,
                    rotate_lim=[0, 3.14, 0],
                )
        while abs(rand_pos.p[0]) < 0.05:
            rand_pos = rand_pose(
                xlim=[-0.25, 0.25],
                ylim=[-0.2, 0.0],
                qpos=[0.5, 0.5, 0.5, 0.5],
                rotate_rand=True,
                rotate_lim=[0, 3.14, 0],
            )

        self.alarmclock_id = np.random.choice([1, 3], 1)[0]
        self.alarm = create_actor(
            scene=self,
            pose=rand_pos,
            modelname="046_alarm-clock",
            convex=True,
            model_id=self.alarmclock_id,
            is_static=True,
        )
        self.add_prohibit_area(self.alarm, padding=0.05)
        alarm_pos = self.alarm.get_pose().p
        self.check_arm_function = self.is_left_gripper_close if self.alarm.get_pose().p[0] < 0 else self.is_right_gripper_close

        # ========== 子任务 2: click_bell ==========
        # 生成bell的位置，避免与alarm重叠
        rand_pos = rand_pose(
                    xlim=[-0.25, 0.25],
                    ylim=[-0.2, 0.0],
                    qpos=[0.5, 0.5, 0.5, 0.5],
                )
        # 检查与alarm的距离，避免重叠（最小距离0.15m）
        min_distance = 0.15
        max_attempts = 100
        attempts = 0
        while (abs(rand_pos.p[0]) < 0.05 or 
               np.linalg.norm(rand_pos.p[:2] - alarm_pos[:2]) < min_distance) and attempts < max_attempts:
            rand_pos = rand_pose(
                xlim=[-0.25, 0.25],
                ylim=[-0.2, 0.0],
                qpos=[0.5, 0.5, 0.5, 0.5],
            )
            attempts += 1

        self.bell_id = np.random.choice([0, 1], 1)[0]
        self.bell = create_actor(
            scene=self,
            pose=rand_pos,
            modelname="050_bell",
            convex=True,
            model_id=self.bell_id,
            is_static=True,
        )

        self.add_prohibit_area(self.bell, padding=0.07)
        self.check_arm_function = self.is_left_gripper_close if self.bell.get_pose().p[0] < 0 else self.is_right_gripper_close

    def play_once(self):
        """依次执行所有子任务"""
        # self.info["info"] = {{}}
        
        # ========== 执行子任务 1: click_alarmclock ==========
        # Determine which arm to use based on alarm clock's position (right if positive x, left otherwise)
        arm_tag = ArmTag("right" if self.alarm.get_pose().p[0] > 0 else "left")

        # Move the gripper above the top center of the alarm clock and close the gripper to simulate a click
        # Note: although the code structure resembles a grasp, it is used here to simulate a touch/click action
        # You can adjust API parameters to move above the top button and close the gripper (similar to grasp_actor)
        self.move((
            ArmTag(arm_tag),
            [
                Action(
                    arm_tag,
                    "move",
                    self.get_grasp_pose(self.alarm, pre_dis=0.1, contact_point_id=0, arm_tag=arm_tag)[:3] +
                    [0.5, -0.5, 0.5, 0.5],
                ),
                Action(arm_tag, "close", target_gripper_pos=0.0),
            ],
        ))

        # Move the gripper downward to press the top button of the alarm clock
        self.move(self.move_by_displacement(arm_tag, z=-0.065))
        # Check whether the simulated click action was successful
        self.check_success()

        # Move the gripper back to the original height (not lifting the alarm clock)
        self.move(self.move_by_displacement(arm_tag, z=0.065))
        # Optionally check success again
        self.check_success()

        # Record information about the alarm clock and the arm used
        self.info["info"] = {
            "{A}": f"046_alarm-clock/base{self.alarmclock_id}",
            "{a}": str(arm_tag),
        }
        # return self.info

        # ========== 执行子任务 2: click_bell ==========
        # Choose the arm to use: right arm if the bell is on the right side (positive x), left otherwise
        arm_tag = ArmTag("right" if self.bell.get_pose().p[0] > 0 else "left")

        # Move the gripper above the top center of the bell and close the gripper to simulate a click
        # Note: grasp_actor here is not used to grasp the bell, but to simulate a touch/click action
        # You must use the same pre_grasp_dis and grasp_dis values as in the click_bell task
        self.move(self.grasp_actor(
            self.bell,
            arm_tag=arm_tag,
            pre_grasp_dis=0.1,
            grasp_dis=0.1,
            contact_point_id=0,  # Targeting the bell's top center
        ))

        # Move the gripper downward to touch the top center of the bell
        self.move(self.move_by_displacement(arm_tag, z=-0.045))

        # Check whether the simulated click action was successful
        self.check_success()

        # Move the gripper back up to the original position (no need to lift or grasp the bell)
        self.move(self.move_by_displacement(arm_tag, z=0.045))

        # Check success again if needed (optional, based on your task logic)
        self.check_success()

        # Record which bell and arm were used in the info dictionary
        # self.info["info"] = {"{A}": f"050_bell/base{self.bell_id}", "{a}": str(arm_tag)}
        return self.info


    def check_success(self):
        """检查所有子任务是否成功"""
        # 需要手动实现组合逻辑
        # 以下是各个子任务的成功检查代码，需要根据实际情况组合
        
        # 子任务 1: click_alarmclock
        # if self.stage_success_tag:
        #     return True
        # if not self.check_arm_function():
        #     return False
        # alarm_pose = self.alarm.get_contact_point(0)[:3]
        # positions = self.get_gripper_actor_contact_position("046_alarm-clock")
        # eps = [0.03, 0.03]
        # for position in positions:
        #     if (np.all(np.abs(position[:2] - alarm_pose[:2]) < eps) and abs(position[2] - alarm_pose[2]) < 0.03):
        #         self.stage_success_tag = True
        #         return True
        # return False

        # # 子任务 2: click_bell
        # if self.stage_success_tag:
        #     return True
        # if not self.check_arm_function():
        #     return False
        # bell_pose = self.bell.get_contact_point(0)[:3]
        # positions = self.get_gripper_actor_contact_position("050_bell")
        # eps = [0.025, 0.025]
        # for position in positions:
        #     if (np.all(np.abs(position[:2] - bell_pose[:2]) < eps) and abs(position[2] - bell_pose[2]) < 0.03):
        #         self.stage_success_tag = True
        #         return True
        # return False

        # # TODO: 实现组合的成功检查逻辑
        return True
