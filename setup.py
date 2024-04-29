from setuptools import setup

setup (
    name='wyag-version-control',
    version='0.1',
    py_modules=['libwyag'],
    entry_points={
        'console_scripts': [
            'wyag = libwyag:main',
        ],
    },
)