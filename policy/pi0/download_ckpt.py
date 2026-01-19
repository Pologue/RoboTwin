from openpi.shared import download
checkpoint_dir = download.maybe_download("gs://openpi-assets/checkpoints/pi0_base")
print("✅ 已下载到:", checkpoint_dir)