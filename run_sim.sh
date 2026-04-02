#!/bin/bash

# ==============================================
# PX4 + ROS 2 + Gazebo: Person Tracking Setup
# Uses the ORIGINAL PX4 default world (proven working)
# Spawns a person model into the world after startup
# ==============================================

# Step 1: Allow Docker to access the X11 display
xhost +local:docker

# Step 2: Setup X auth
XAUTH=/tmp/.docker.xauth
touch $XAUTH
xauth nlist $DISPLAY | sed -e 's/^..../ffff/' | xauth -f $XAUTH nmerge -

# Enable tmux mouse mode (click on panes!)
echo "set -g mouse on" > /tmp/.tmux.conf

# Kill any leftover container from a previous run
sudo docker rm -f px4_ros2_gz_yolov8_container 2>/dev/null || true

echo ""
echo "========================================="
echo "  PX4 + ROS 2 + Gazebo (Person Tracking)"
echo "========================================="
echo "  Using default PX4 world + person spawn"
echo "  Wait ~20s, then press 'r' to arm"
echo "  CONTROLS: arrows=fly, w/s=throttle"
echo "  Click panes with mouse to switch"
echo "========================================="
echo ""

# Step 3: Run Docker with custom tmux + person model mounted
sudo docker run --privileged -it --gpus all \
  -e NVIDIA_DRIVER_CAPABILITIES=all \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e MESA_GL_VERSION_OVERRIDE=3.3 \
  --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
  --env="XAUTHORITY=$XAUTH" \
  --volume="$XAUTH:$XAUTH" \
  --volume="/tmp/.tmux.conf:/root/.tmux.conf:ro" \
  --volume="$(pwd)/custom_tmux.yml:/root/custom_tmux.yml:ro" \
  --volume="$(pwd)/models/person_model.sdf:/root/person_model.sdf:ro" \
  --network=host --ipc=host --shm-size=2gb \
  --env="DISPLAY=$DISPLAY" \
  --env="QT_X11_NO_MITSHM=1" \
  --rm --name px4_ros2_gz_yolov8_container \
  --entrypoint /bin/bash \
  monemati/px4_ros2_gz_yolov8_image -c "tmuxinator start -p /root/custom_tmux.yml"
