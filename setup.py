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
    packages=find_packages('rclip'),
    package_dir={'': 'rclip'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    install_requires=open('requirements.txt').read().splitlines(),
    entry_points={
        'console_scripts': [
            'rclip=rclip.rclip:main',
        ]
    }
)
