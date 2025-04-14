from ament_index_python.packages import get_package_share_directory
from launch.event_handlers import OnProcessExit
from launch.actions import(
    ExecuteProcess,
    DeclareLaunchArgument,
    RegisterEventHandler,
    SetEnvironmentVariable

)
from launch import LaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import (
    LaunchConfiguration,
    Command,
    AndSubstitution,
    NotSubstitution,
    FindExecutable,
    PathJoinSubstitution
)
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
import launch_ros
import xacro
import os   
import launch

def generate_launch_description():

    
    # Process the URDF file
    pkg_share = launch_ros.substitutions.FindPackageShare(package='robot_demo').find('robot_demo')
    default_model_path =  os.path.join(pkg_share, 'description','robot.urdf')
    default_rviz_config_path = os.path.join(pkg_share, 'rviz','urdf.rviz')
    

    # Load launch arguments
    use_sim_time = LaunchConfiguration("use_sim_time")
    run_headless = LaunchConfiguration("run_headless")
    use_rviz = LaunchConfiguration("run_rviz")
    gz_verbosity = LaunchConfiguration('gz_verbosity')
    world_file_name = LaunchConfiguration('world_file')
    gz_model_path = ":".join([pkg_share, os.path.join(pkg_share, 'models')])
    world_path = PathJoinSubstitution([pkg_share, 'worlds', world_file_name])
    log_level = LaunchConfiguration('log_level')
    # Process the URDF file
    # This code is commented out because we're using a direct URDF file (robot.urdf)
    # instead of a xacro file. If we were using xacro, this would:
    # 1. Find the xacro file path
    # 2. Parse the xacro file to process macros and properties
    # 3. Convert it to XML for the robot_state_publisher
    # 
    # robot_description_config = open(default_model_path).read()
    
    # Create a robot_state_publisher node
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[
            {"robot_description": Command(["xacro", LaunchConfiguration("model")])}
        ],
    )
    rviz_node = Node(
        condition=IfCondition(AndSubstitution(NotSubstitution(run_headless), use_rviz)),
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', LaunchConfiguration('rvizconfig')],
    )

    gz_env = {'GZ_SIM_SYSTEM_PLUGIN_PATH':
           ':'.join([os.environ.get('GZ_SIM_SYSTEM_PLUGIN_PATH', default=''),
                     os.environ.get('LD_LIBRARY_PATH', default='')]),
           'IGN_GAZEBO_SYSTEM_PLUGIN_PATH':  # TODO(CH3): To support pre-garden. Deprecated.
                      ':'.join([os.environ.get('IGN_GAZEBO_SYSTEM_PLUGIN_PATH', default=''),
                                os.environ.get('LD_LIBRARY_PATH', default='')])}
    gazebo = [
        ExecuteProcess(
            condition=launch.conditions.IfCondition(run_headless),
            cmd=['ruby', FindExecutable(name="ign"), 'gazebo',  '-r', '-v', gz_verbosity, '-s', '--headless-rendering', world_path],
            output='screen',
            additional_env=gz_env, # type: ignore
            shell=False,
        ),
        ExecuteProcess(
            condition=launch.conditions.UnlessCondition(run_headless),
            cmd=['ruby', FindExecutable(name="ign"), 'gazebo',  '-r', '-v', gz_verbosity, world_path],
            output='screen',
            additional_env=gz_env, # type: ignore
            shell=False,
        )
    ]

    spawn_entity = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            '-topic', 'robot_description',
            '-name', 'robot',
            '-z', '1.0',
            '-x', '-2.0',
            "--ros-args", "log-level", log_level,
        ],
        parameters=[{"use_sim_time": use_sim_time}],
    )
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan",
            "/imu@sensor_msgs/msg/Imu[ignition.msgs.IMU",
            "/sky_cam@sensor_msgs/msg/Image@ignition.msgs.Image",
            "/robot_cam@sensor_msgs/msg/Image@ignition.msgs.Image",
            "/camera_info@sensor_msgs/msg/CameraInfo@ignition.msgs.CameraInfo",
            # Clock message is necessary for the diff_drive_controller to accept commands https://github.com/ros-controls/gz_ros2_control/issues/106
            "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock",
        ],
        output="screen",
    )
    # Launch!
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                name= "IGN_GAZEBO_RESOURCE_PATH",
                value=gz_model_path,
                description='Gazebo model path'
            ),
            DeclareLaunchArgument(
                'log_level',
                default_value='warn',
                description='Log level for ROS 2'),
            DeclareLaunchArgument(
                'use_sim_time',
                default_value='false',
                description='Use sim time if true'),
                
            DeclareLaunchArgument(
                'run_headless',
                default_value='false',
                description='Run without GUI if true'),
                
            DeclareLaunchArgument(
                'run_rviz',
                default_value='true',
                description='Start RViz2 if true'),
                
            DeclareLaunchArgument(
                'model',
                default_value=default_model_path,
                description='Path to robot URDF file'),
                
            DeclareLaunchArgument(
                'rvizconfig',
                default_value=default_rviz_config_path,
                description='Path to RViz config file'),
                
            DeclareLaunchArgument(
                'world_file',
                default_value="empty.sdf",
                description='Path to SDF world file'),
                
            DeclareLaunchArgument(
                'gz_verbosity',
                default_value='3',
                description='Gazebo verbosity level'),
            DeclareLaunchArgument(
                name="gz_args",
                default_value="",
                description="Gazebo arguments"
            ),
            bridge,
            robot_state_publisher_node,
            spawn_entity,   
            rviz_node
        ] + gazebo
    )
