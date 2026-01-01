import os
import h5py
import cv2
import numpy as np
from pathlib import Path
import subprocess


def load_hdf5(dataset_path):
    if not os.path.isfile(dataset_path):
        print(f"Dataset does not exist at \n{dataset_path}\n")
        exit()

    with h5py.File(dataset_path, "r") as root:
        left_gripper, left_arm = (
            root["/joint_action/left_gripper"][()],
            root["/joint_action/left_arm"][()],
        )
        right_gripper, right_arm = (
            root["/joint_action/right_gripper"][()],
            root["/joint_action/right_arm"][()],
        )
        image_dict = dict()
        for cam_name in root[f"/observation/"].keys():
            image_dict[cam_name] = root[f"/observation/{cam_name}/rgb"][()]
        third_view_rgb = root["/third_view_rgb"][()]
        pointcloud = root["/pointcloud"][()]

    return left_gripper, left_arm, right_gripper, right_arm, image_dict, third_view_rgb, pointcloud


def byte_list_to_video(input_byte_list, output_video_path, fps=30, overwrite=True):
    """
    Convert a list of JPEG-encoded byte data to video using ffmpeg.
    This approach avoids the need for conda-installed opencv.
    """
    # Decode JPEG bytes to numpy arrays
    images = [cv2.imdecode(np.frombuffer(image_bit, np.uint8), cv2.IMREAD_COLOR) for image_bit in input_byte_list]
    
    # Stack images into a single numpy array
    images_array = np.array(images)
    
    output_file = Path(output_video_path)
    if output_file.exists():
        if not overwrite:
            print(f"Warning: file {output_video_path} already exists, exiting...")
            exit()
        else:
            print(f"Warning: file {output_video_path} already exists, overwriting...")
            output_file.unlink()
    
    # Create output directory if it doesn't exist
    os.makedirs(output_file.parent, exist_ok=True)
    
    n_frames, h, w, c = images_array.shape
    
    # Use ffmpeg to encode video via stdin
    ffmpeg = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pixel_format",
            "bgr24",  # OpenCV uses BGR format
            "-video_size",
            f"{w}x{h}",
            "-framerate",
            str(fps),
            "-i",
            "-",
            "-pix_fmt",
            "yuv420p",
            "-vcodec",
            "libx264",
            "-crf",
            "23",
            str(output_video_path),
        ],
        stdin=subprocess.PIPE,
    )
    
    ffmpeg.stdin.write(images_array.tobytes())
    ffmpeg.stdin.close()
    
    if ffmpeg.wait() != 0:
        print(f"Error: failed to create video file {output_video_path}")
    else:
        print(f"Video saved to: {output_video_path} ({n_frames} frames, {w}×{h} resolution, {fps} FPS)")


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent)

    for task_dir in Path("../data").iterdir():
        if task_dir.is_dir() and (task_dir / "test1").exists():
            dataset_path = task_dir / "test1" / "data" / "episode0.hdf5"

            lgripper, larm, rgripper, rarm, image_dict, third_view_rgb, pointcloud = load_hdf5(dataset_path)

            byte_list_to_video(image_dict["front_camera"], str(dataset_path.parent.joinpath("front_camera.mp4")))
            byte_list_to_video(image_dict["head_camera"], str(dataset_path.parent.joinpath("head_camera.mp4")))
            byte_list_to_video(image_dict["left_camera"], str(dataset_path.parent.joinpath("left_camera.mp4")))
            byte_list_to_video(image_dict["right_camera"], str(dataset_path.parent.joinpath("right_camera.mp4")))
            byte_list_to_video(third_view_rgb, str(dataset_path.parent.joinpath("third_view_rgb.mp4")))

