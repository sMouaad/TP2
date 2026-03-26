from setuptools import find_packages, setup

package_name = 'turtle_boundary'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/turtle_boundary/launch', ['launch/draw_boundaries.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='maya',
    maintainer_email='Oubraham.Maya@etu.univ-grenoble-alpes.fr',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'keyboard_listener = turtle_boundary.keyboard_listener:main',
            'draw_boundaries = turtle_boundary.draw_boundaries:main',
        ],
    },
)
