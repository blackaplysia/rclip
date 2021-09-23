from glob import glob
from os.path import basename
from os.path import splitext

from setuptools import setup
from setuptools import find_packages

setup(
    name='rclip',
    version='0.1.0',
    license='MIT LICENSE',
    description='Remote clip',
    author='mkyutani@gmail.com',
    url='http://github.com/mkyutani/rclip',
    packages=find_packages(),
    install_requires=open('requirements.txt').read().splitlines(),
    entry_points={
        'console_scripts': [
            'rclip=rclip.rclip:main',
        ]
    },
    zip_safe=False
)
