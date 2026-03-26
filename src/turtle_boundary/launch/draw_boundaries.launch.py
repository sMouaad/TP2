
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
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

    # Keyboard listener — doit être lancé dans un terminal SÉPARÉ pour stdin :
    #   ros2 run turtle_boundary keyboard_listener
    # On l'inclut ici mais il faut un terminal séparé pour qu'il fonctionne
    keyboard_listener_node = Node(
        package='turtle_boundary',
        executable='keyboard_listener',
        name='keyboard_listener',
        output='screen',
    )

    # PAS de turtlesim_node — le Create3 réel tourne déjà via Docker
    return LaunchDescription([
        speed_arg,
        rect_size_arg,
        draw_boundaries_node,
        keyboard_listener_node
    ])