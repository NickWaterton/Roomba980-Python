from setuptools import find_packages, setup


setup(
    name="roombapy",
    version="1.4.3",
    license="MIT",
    description="Python program and library to control Wi-Fi enabled iRobot "
    "Roomba vacuum cleaners",
    author_email="nick.waterton@med.ge.com",
    url="https://github.com/pschmitt/roombapy",
    packages=find_packages(),
    install_requires=["paho-mqtt", "six"],
    extras_require={"mapping": ["numpy", "opencv-python", "pillow"]},
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "roomba=roomba.__main__:main",
            "roomba-getpassword=roomba.getpassword:main",
        ]
    },
)
