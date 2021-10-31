from setuptools import setup

setup(
    name='bbuilder',
    version='0.0.1',
    packages=['bbuilder', 'bbuilder.lib'],
    install_requires=[
        'Click',
        'PyYAML',
        'flask',
        'celery',
        'redis'
    ],
    entry_points={
        'console_scripts': [
            'bbuilder = bbuilder.bbuilder:cli',
        ],
    },
)
