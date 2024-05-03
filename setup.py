from setuptools import setup

setup (
    name='mygit-version-control',
    version='0.1',
    py_modules=['mygitlib'],
    entry_points={
        'console_scripts': [
            'mygit = src.mygitlib:main',
        ],
    },
)
