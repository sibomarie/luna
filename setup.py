# Encoding: UTF-8

from setuptools import setup, find_packages

setup(
    name='luna',
    version='0.0.1',

    packages=find_packages(),

    install_requires=[
        'pymongo>2.4,<2.6',
        'tornado',
        'python-hostlist'
    ],

    dependency_links=[],

    package_data={
        
    },
)
