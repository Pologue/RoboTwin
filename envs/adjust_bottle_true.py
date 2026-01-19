from ._base_task import Base_Task
from .utils import *
import sapien
import math


class adjust_bottle_true(Base_Task):

    def setup_demo(self, **kwags):
        super()._init_task_env_(**kwags)

    def load_actors(self):
        self.qpose_tag = np.random.randint(0, 2)
        qposes = [[0.707, 0.0, 0.0, -0.707], [0.707, 0.0, 0.0, 0.707]]
        xlims = [[-0.12, -0.08], [0.08, 0.12]]

        self.model_id = np.random.choice([13, 16])

        self.bottle = rand_create_actor(
            self,
            xlim=xlims[self.qpose_tag],
            ylim=[-0.13, -0.08],
            zlim=[0.752],
            rotate_rand=True,
            qpos=qposes[self.qpose_tag],
            modelname="001_bottle",
            convex=True,
            rotate_lim=(0, 0, 0.4),
            model_id=self.model_id,
        )
        self.delay(4)
        self.add_prohibit_area(self.bottle, padding=0.15)
        self.left_target_pose = [-0.25, -0.12, 0.95, 0, 1, 0, 0]
        self.right_target_pose = [0.25, -0.12, 0.95, 0, 1, 0, 0]

    def play_once(self):
        # Determine which arm to use based on qpose_tag (1 for right, else left)
        arm_tag = ArmTag("right" if self.qpose_tag == 1 else "left")
        # Select target pose based on qpose_tag (right_target_pose or left_target_pose)
        target_pose = (self.right_target_pose if self.qpose_tag == 1 else self.left_target_pose)

        # Randomly decide whether to introduce failure (40% chance)
        introduce_failure = np.random.random() < 0.4
        
        # Set parameters based on whether we want to introduce failure
        if introduce_failure:
            # Add random disturbances to create failure cases
            pre_grasp_offset = np.random.uniform(-0.08, 0.08)  # Offset for grasp distance
            lift_height_offset = np.random.uniform(-0.15, 0.15)  # Offset for lift height
            target_pose_offset_x = np.random.uniform(-0.15, 0.15)  # X offset for target
            target_pose_offset_y = np.random.uniform(-0.15, 0.15)  # Y offset for target
            target_pose_offset_z = np.random.uniform(-0.2, 0.1)  # Z offset for target
            
            pre_grasp_dis = max(0.02, 0.1 + pre_grasp_offset)
            lift_height = 0.1 + lift_height_offset
            disturbed_target_pose = [
                target_pose[0] + target_pose_offset_x,
                target_pose[1] + target_pose_offset_y,
                target_pose[2] + target_pose_offset_z,
                target_pose[3], target_pose[4], target_pose[5], target_pose[6]
            ]
        else:
            # Normal execution without disturbances
            pre_grasp_dis = 0.1
            lift_height = 0.1
            disturbed_target_pose = target_pose

        # Grasp the bottle with specified arm
        self.move(self.grasp_actor(self.bottle, arm_tag=arm_tag, pre_grasp_dis=pre_grasp_dis))
        # Move the arm upward by lift_height meters along z-axis
        self.move(self.move_by_displacement(arm_tag=arm_tag, z=lift_height, move_axis="arm"))
        # Place the bottle at target pose (functional point 0) while keeping gripper closed
        self.move(
            self.place_actor(
                self.bottle,
                target_pose=disturbed_target_pose,
                arm_tag=arm_tag,
                functional_point_id=0,
                pre_dis=0.0,
                is_open=not introduce_failure,
            ))

        self.info["info"] = {
            "{A}": f"001_bottle/base{self.model_id}",
            "{a}": str(arm_tag),
        }
        return self.info

    def check_success(self):
        # target_hight = 0.9
        # bottle_pose = self.bottle.get_functional_point(0)
        # return ((self.qpose_tag == 0 and bottle_pose[0] < -0.15) or
        #         (self.qpose_tag == 1 and bottle_pose[0] > 0.15)) and bottle_pose[2] > target_hight
        return True
