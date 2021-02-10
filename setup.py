from setuptools import find_packages, setup


setup(
    name='Roomba980-Python',
    version='2.0',
    license='MIT',
    description='Python program and library to control iRobot WiFi Roomba ' \
    'Vacuum Cleaner',
    author_email='nick.waterton@med.ge.com',
    url='https://github.com/NickWaterton/Roomba980-Python',
    packages=find_packages(),
    python_requires='>=3.6',
    install_requires=['paho-mqtt'],
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'roomba=roomba.__main__:main',
            'roomba-getpassword=roomba.getpassword:main'
        ]
    }
)
