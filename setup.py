from setuptools import find_packages, setup
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='roombapy',
    version='1.5.1',
    license='MIT',
    description='Python program and library to control Wi-Fi enabled iRobot Roomba vacuum cleaners',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author_email='nick.waterton@med.ge.com',
    url='https://github.com/pschmitt/roombapy',
    classifiers=[
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking'
    ],
    keywords='roomba irobot braava home-assistant',
    packages=find_packages(),
    install_requires=['paho-mqtt'],
    entry_points={
        'console_scripts': [
            'roomba=roomba.__main__:main'
        ]
    },
)
