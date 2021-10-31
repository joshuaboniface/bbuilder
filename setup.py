from setuptools import setup

setup(
    name='bbuilder',
    version='0.0.1',
    packages=['bbuilder', 'bbuilder.lib'],
    install_requires=[
        'Click',
        'PyYAML',
        'lxml',
        'colorama',
        'requests',
        'requests-toolbelt',
        'flask'
    ],
    entry_points={
        'console_scripts': [
            'bbuilder = bbuilder.bbuilder:cli',
        ],
    },
)
