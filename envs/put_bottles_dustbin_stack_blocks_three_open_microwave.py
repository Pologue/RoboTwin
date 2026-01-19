from ._base_task import Base_Task
from .utils import *
import sapien
import math
from .utils import *
import math
import sapien


class put_bottles_dustbin_stack_blocks_three_open_microwave(Base_Task):
    """
    复合任务: 依次执行: put_bottles_dustbin_stack_blocks_three, open_microwave
    
    包含以下子任务:
        - put_bottles_dustbin_stack_blocks_three
    - open_microwave
    """

    def setup_demo(self, **kwags):
        super()._init_task_env_(**kwags)

    def load_actors(self):
        """加载所有子任务的actors"""

        # ========== 子任务 1: put_bottles_dustbin_stack_blocks_three ==========
        """加载所有子任务的actors"""

        # ========== 子任务 1: put_bottles_dustbin ==========
        pose_lst = []

        def create_bottle(model_id):
            bottle_pose = rand_pose(
                xlim=[-0.25, 0.3],
                ylim=[0.03, 0.23],
                rotate_rand=False,
                rotate_lim=[0, 1, 0],
                qpos=[0.707, 0.707, 0, 0],
            )
            tag = True
            gen_lim = 100
            i = 1
            while tag and i < gen_lim:
                tag = False
                if np.abs(bottle_pose.p[0]) < 0.05:
                    tag = True
                for pose in pose_lst:
                    if (np.sum(np.power(np.array(pose[:2]) - np.array(bottle_pose.p[:2]), 2)) < 0.0169):
                        tag = True
                        break
                if tag:
                    i += 1
                    bottle_pose = rand_pose(
                        xlim=[-0.25, 0.3],
                        ylim=[0.03, 0.23],
                        rotate_rand=False,
                        rotate_lim=[0, 1, 0],
                        qpos=[0.707, 0.707, 0, 0],
                    )
            pose_lst.append(bottle_pose.p[:2])
            bottle = create_actor(
                self,
                bottle_pose,
                modelname="114_bottle",
                convex=True,
                model_id=model_id,
            )

            return bottle

        self.bottles = []
        self.bottles_data = []
        self.bottle_id = [1, 2, 3]
        self.bottle_num = 3
        for i in range(self.bottle_num):
            bottle = create_bottle(self.bottle_id[i])
            self.bottles.append(bottle)
            self.add_prohibit_area(bottle, padding=0.1)

        self.dustbin = create_actor(
            self.scene,
            pose=sapien.Pose([-0.45, 0, 0], [0.5, 0.5, 0.5, 0.5]),
            modelname="011_dustbin",
            convex=True,
            is_static=True,
        )
        self.delay(2)
        self.right_middle_pose = [0, 0.0, 0.88, 0, 1, 0, 0]

        # ========== 子任务 2: stack_blocks_three ==========
        block_half_size = 0.025
        block_pose_lst = []
        for i in range(3):
            block_pose = rand_pose(
                xlim=[-0.28, 0.28],
                ylim=[-0.08, 0.05],
                zlim=[0.741 + block_half_size],
                qpos=[1, 0, 0, 0],
                ylim_prop=True,
                rotate_rand=True,
                rotate_lim=[0, 0, 0.75],
            )

            def check_block_pose(block_pose):
                for j in range(len(block_pose_lst)):
                    if (np.sum(pow(block_pose.p[:2] - block_pose_lst[j].p[:2], 2)) < 0.01):
                        return False
                return True

            while (abs(block_pose.p[0]) < 0.05 or np.sum(pow(block_pose.p[:2] - np.array([0, -0.1]), 2)) < 0.0225
                    or not check_block_pose(block_pose)):
                block_pose = rand_pose(
                    xlim=[-0.28, 0.28],
                    ylim=[-0.08, 0.05],
                    zlim=[0.741 + block_half_size],
                    qpos=[1, 0, 0, 0],
                    ylim_prop=True,
                    rotate_rand=True,
                    rotate_lim=[0, 0, 0.75],
                )
            block_pose_lst.append(deepcopy(block_pose))

        def create_block(block_pose, color):
            return create_box(
                scene=self,
                pose=block_pose,
                half_size=(block_half_size, block_half_size, block_half_size),
                color=color,
                name="box",
            )

        self.block1 = create_block(block_pose_lst[0], (1, 0, 0))
        self.block2 = create_block(block_pose_lst[1], (0, 1, 0))
        self.block3 = create_block(block_pose_lst[2], (0, 0, 1))
        self.add_prohibit_area(self.block1, padding=0.05)
        self.add_prohibit_area(self.block2, padding=0.05)
        self.add_prohibit_area(self.block3, padding=0.05)
        target_pose = [-0.04, -0.13, 0.04, -0.05]
        self.prohibited_area.append(target_pose)
        self.block1_target_pose = [0, -0.13, 0.75 + self.table_z_bias, 0, 1, 0, 0]

        # ========== 子任务 2: open_microwave ==========
        # 微波炉位置需要避开丢瓶子的运动路径
        # 原始位置: xlim=[-0.12, -0.02], ylim=[0.15, 0.2]
        # 这个位置会挡住从桌子到垃圾桶的路径
        # 改为更靠后（更大的y值）的位置，避开机械臂轨迹
        self.model_name = "044_microwave"
        self.model_id = np.random.randint(0, 2)
        self.microwave = rand_create_sapien_urdf_obj(
            scene=self,
            modelname=self.model_name,
            modelid=self.model_id,
            xlim=[-0.12, -0.02],
            ylim=[0.25, 0.3],  # 从[0.15, 0.2]改为[0.25, 0.3]，向后移动避开路径
            zlim=[0.8, 0.8],
            qpos=[0.707, 0, 0, 0.707],
            fix_root_link=True,
        )
        self.microwave.set_mass(0.01)
        self.microwave.set_properties(0.0, 0.0)

        self.add_prohibit_area(self.microwave)
        self.prohibited_area.append([-0.25, -0.25, 0.25, 0.1])

    def play_once(self):
        """依次执行所有子任务"""
        # self.info["info"] = {{}}
        
        # ========== 执行子任务 1: put_bottles_dustbin_stack_blocks_three ==========
        """依次执行所有子任务"""
        # self.info["info"] = {{}}

        # ========== 执行子任务 1: put_bottles_dustbin ==========
        # Sort bottles based on their x and y coordinates
        bottle_lst = sorted(self.bottles, key=lambda x: [x.get_pose().p[0] > 0, x.get_pose().p[1]])

        for i in range(self.bottle_num):
            bottle = bottle_lst[i]
            # Determine which arm to use based on bottle's x position
            arm_tag = ArmTag("left" if bottle.get_pose().p[0] < 0 else "right")

            delta_dis = 0.06

            # Define end position for left arm
            left_end_action = Action("left", "move", [-0.35, -0.1, 0.93, 0.65, -0.25, 0.25, 0.65])

            if arm_tag == "left":
                # Grasp the bottle with left arm
                self.move(self.grasp_actor(bottle, arm_tag=arm_tag, pre_grasp_dis=0.1))
                # Move left arm up
                self.move(self.move_by_displacement(arm_tag, z=0.1))
                # Move left arm to end position
                self.move((ArmTag("left"), [left_end_action]))
            else:
                # Grasp the bottle with right arm while moving left arm to origin
                right_action = self.grasp_actor(bottle, arm_tag=arm_tag, pre_grasp_dis=0.1)
                right_action[1][0].target_pose[2] += delta_dis
                right_action[1][1].target_pose[2] += delta_dis
                self.move(right_action, self.back_to_origin("left"))
                # Move right arm up
                self.move(self.move_by_displacement(arm_tag, z=0.1))
                # Place the bottle at middle position with right arm
                self.move(
                    self.place_actor(
                        bottle,
                        target_pose=self.right_middle_pose,
                        arm_tag=arm_tag,
                        functional_point_id=0,
                        pre_dis=0.0,
                        dis=0.0,
                        is_open=False,
                        constrain="align",
                    ))
                # Grasp the bottle with left arm (adjusted height)
                left_action = self.grasp_actor(bottle, arm_tag="left", pre_grasp_dis=0.1)
                left_action[1][0].target_pose[2] -= delta_dis
                left_action[1][1].target_pose[2] -= delta_dis
                self.move(left_action)
                # Open right gripper
                self.move(self.open_gripper(ArmTag("right")))
                # Move left arm to end position while moving right arm to origin
                self.move((ArmTag("left"), [left_end_action]), self.back_to_origin("right"))
            # Open left gripper
            self.move(self.open_gripper("left"))

        self.info["info"] = {
            "{A}": f"114_bottle/base{self.bottle_id[0]}",
            "{B}": f"114_bottle/base{self.bottle_id[1]}",
            "{C}": f"114_bottle/base{self.bottle_id[2]}",
            "{D}": f"011_dustbin/base0",
        }
        # # return self.info

        # ========== 执行子任务 2: stack_blocks_three ==========
        # Initialize tracking variables for last used gripper and actor
        self.last_gripper = None
        self.last_actor = None

        # Pick and place the first block (red) and get which arm was used
        arm_tag1 = self.pick_and_place_block(self.block1)
        # Pick and place the second block (green) and get which arm was used
        arm_tag2 = self.pick_and_place_block(self.block2)
        # Pick and place the third block (blue) and get which arm was used
        arm_tag3 = self.pick_and_place_block(self.block3)

        # Store information about the blocks and which arms were used
        self.info["info"] = {
            "{A}": "red block",
            "{B}": "green block",
            "{C}": "blue block",
            "{a}": str(arm_tag1),
            "{b}": str(arm_tag2),
            "{c}": str(arm_tag3),
        }
        # return self.info

        # ========== 执行子任务 2: open_microwave ==========
        arm_tag = ArmTag("left")

        # Grasp the microwave with pre-grasp displacement
        self.move(self.grasp_actor(self.microwave, arm_tag=arm_tag, pre_grasp_dis=0.08, contact_point_id=0))

        start_qpos = self.microwave.get_qpos()[0]
        for _ in range(50):
            # Rotate microwave
            self.move(
                self.grasp_actor(
                    self.microwave,
                    arm_tag=arm_tag,
                    pre_grasp_dis=0.0,
                    grasp_dis=0.0,
                    contact_point_id=4,
                ))

            new_qpos = self.microwave.get_qpos()[0]
            if new_qpos - start_qpos <= 0.001:
                break
            start_qpos = new_qpos
            if not self.plan_success:
                break
            if self.check_success(target=0.7):
                break

        if not self.check_success(target=0.7):
            self.plan_success = True  # Try new way
            # Open gripper
            self.move(self.open_gripper(arm_tag=arm_tag))
            self.move(self.move_by_displacement(arm_tag=arm_tag, y=-0.05, z=0.05))

            # Grasp at contact point 1
            self.move(self.grasp_actor(self.microwave, arm_tag=arm_tag, contact_point_id=1))

            # Grasp more tightly at contact point 1
            self.move(self.grasp_actor(
                self.microwave,
                arm_tag=arm_tag,
                pre_grasp_dis=0.02,
                contact_point_id=1,
            ))

            start_qpos = self.microwave.get_qpos()[0]
            for _ in range(30):
                # Rotate microwave using contact point 2
                self.move(
                    self.grasp_actor(
                        self.microwave,
                        arm_tag=arm_tag,
                        pre_grasp_dis=0.0,
                        grasp_dis=0.0,
                        contact_point_id=2,
                    ))

                new_qpos = self.microwave.get_qpos()[0]
                if new_qpos - start_qpos <= 0.001:
                    break
                start_qpos = new_qpos
                if not self.plan_success:
                    break
                if self.check_success(target=0.7):
                    break

        self.info["info"] = {
            "{A}": f"{self.model_name}/base{self.model_id}",
            "{a}": str(arm_tag),
        }
        return self.info


    def pick_and_place_block(self, block: Actor):
        block_pose = block.get_pose().p
        arm_tag = ArmTag("left" if block_pose[0] < 0 else "right")

        if self.last_gripper is not None and (self.last_gripper != arm_tag):
            self.move(
                self.grasp_actor(block, arm_tag=arm_tag, pre_grasp_dis=0.09),  # arm_tag
                self.back_to_origin(arm_tag=arm_tag.opposite),  # arm_tag.opposite
            )
        else:
            self.move(self.grasp_actor(block, arm_tag=arm_tag, pre_grasp_dis=0.09))  # arm_tag

        self.move(self.move_by_displacement(arm_tag=arm_tag, z=0.07))  # arm_tag

        if self.last_actor is None:
            target_pose = [0, -0.13, 0.75 + self.table_z_bias, 0, 1, 0, 0]
        else:
            target_pose = self.last_actor.get_functional_point(1)

        self.move(
            self.place_actor(
                block,
                target_pose=target_pose,
                arm_tag=arm_tag,
                functional_point_id=0,
                pre_dis=0.05,
                dis=0.,
                pre_dis_axis="fp",
            ))
        self.move(self.move_by_displacement(arm_tag=arm_tag, z=0.07))  # arm_tag

        self.last_gripper = arm_tag
        self.last_actor = block
        return str(arm_tag)


    def check_success(self, target=0.6):
        """检查所有子任务是否成功"""
        # 需要手动实现组合逻辑
        # 以下是各个子任务的成功检查代码，需要根据实际情况组合
        
        # 子任务 1: put_bottles_dustbin_stack_blocks_three
        # """检查所有子任务是否成功"""
        # 需要手动实现组合逻辑
        # 以下是各个子任务的成功检查代码，需要根据实际情况组合
        
        # 子任务 1: put_bottles_dustbin
        # taget_pose = [-0.45, 0]
        # eps = np.array([0.221, 0.325])
        # for i in range(self.bottle_num):
        #     bottle_pose = self.bottles[i].get_pose().p
        #     if (np.all(np.abs(bottle_pose[:2] - taget_pose) < eps) and bottle_pose[2] > 0.2 and bottle_pose[2] < 0.7):
        #         continue
        #     return False
        # return True

        # # 子任务 2: stack_blocks_three
        # # block1_pose = self.block1.get_pose().p
        # block2_pose = self.block2.get_pose().p
        # block3_pose = self.block3.get_pose().p
        # eps = [0.025, 0.025, 0.012]

        # return (np.all(abs(block2_pose - np.array(block1_pose[:2].tolist() + [block1_pose[2] + 0.05])) < eps)
        #         and np.all(abs(block3_pose - np.array(block2_pose[:2].tolist() + [block2_pose[2] + 0.05])) < eps)
        #         and self.is_left_gripper_open() and self.is_right_gripper_open())

        # # TODO: 实现组合的成功检查逻辑
        return True

        # 子任务 2: open_microwave
        # 

        # TODO: 实现组合的成功检查逻辑
        return True
