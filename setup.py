from setuptools import find_packages, setup


setup(
    name='Roomba980-Python',
    version='1.2.1',
    license='MIT',
    description='Python program and library to control iRobot Roomba 980 ' \
    'Vacuum Cleaner',
    author_email='nick.waterton@med.ge.com',
    url='https://github.com/NickWaterton/Roomba980-Python',
    packages=find_packages(),
    install_requires=['numpy', 'opencv-python', 'paho-mqtt', 'pillow', 'six'],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'roomba=roomba.roomba:main',
            'roomba-getpassword=roomba.getpassword:main'
        ]
    }
)
