
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    # Arguments pour vitesse et taille du rectangle
    speed_arg = DeclareLaunchArgument(
        'speed', default_value='0.2',
        description='Maximum linear speed of the Create3 (m/s)'
    )

    rect_size_arg = DeclareLaunchArgument(
        'rect_size', default_value='1.5',
        description='Size of the rectangle to trace (meters)'
    )

    # Node Draw Boundaries (contrôleur principal)
    draw_boundaries_node = Node(
        package='turtle_boundary',
        executable='draw_boundaries',
        name='draw_boundaries_node',
        output='screen',
        parameters=[{
            'speed': LaunchConfiguration('speed'),
            'rect_size': LaunchConfiguration('rect_size')
        }]
    )

    reminder = LogInfo(
        msg='Pour le mode manuel, lancer dans un AUTRE terminal : '
            'ros2 run turtle_boundary keyboard_listener'
    )

    # PAS de turtlesim_node — le Create3 réel tourne déjà via Docker
    # keyboard_listener a besoin d'un vrai TTY → le lancer manuellement
    return LaunchDescription([
        speed_arg,
        rect_size_arg,
        reminder,
        draw_boundaries_node,
    ])