import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()
    
setup(
    name='django-toggled-widgets',
    version='0.2',
    packages=find_packages(),
    include_package_data=True,
    description='Base classes and mixins to facilitate toggling visibility between multiple Django admin fields',
    long_description=README,
    author='Max Crowe',
    author_email='max.crowe@performics.com'
)
