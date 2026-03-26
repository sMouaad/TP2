
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    # Arguments pour vitesse et marge des limites
    speed_arg = DeclareLaunchArgument(
        'speed', default_value='2.0',
        description='Maximum linear/angular speed of the turtle'
    )

    boundary_margin_arg = DeclareLaunchArgument(
        'boundary_margin', default_value='0.5',
        description='Distance from the turtlesim wall edge defining the boundary'
    )

    # Node Turtlesim
    turtlesim_node = Node(
        package='turtlesim',
        executable='turtlesim_node',
        name='turtlesim_node',
        output='screen'
    )

    # Node Draw Boundaries (ton node principal)
    draw_boundaries_node = Node(
        package='turtle_boundary',
        executable='draw_boundaries',
        name='draw_boundaries_node',
        output='screen',
        parameters=[{
            'speed': LaunchConfiguration('speed'),
            'boundary_margin': LaunchConfiguration('boundary_margin')
        }]
    )

    # Keyboard listener dans un xterm pour lire les touches correctement
    keyboard_listener_node = ExecuteProcess(
        cmd=['xterm', '-hold', '-e', 'ros2 run turtle_boundary keyboard_listener'],
        name='keyboard_listener',
        output='screen'
    )

    # Retour de la LaunchDescription
    return LaunchDescription([
        speed_arg,
        boundary_margin_arg,
        turtlesim_node,
        draw_boundaries_node,
        keyboard_listener_node
    ])