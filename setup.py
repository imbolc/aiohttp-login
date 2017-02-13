#!/usr/bin/env python
import os
import sys
from setuptools import setup

try:
    import pandoc
except ImportError:
    pandoc = None


if sys.argv[-1] == 'publish':
    assert pandoc, 'You have to do: pip install pyandoc'
    os.system('python setup.py sdist upload')
    sys.exit(0)


def read(fname):
    with open(fname) as f:
        return f.read()


def get_description():
    with open('README.md') as f:
        desc = f.read()
    short = desc.split('===\n')[1].strip().split('\n')[0]
    if pandoc:
        doc = pandoc.Document()
        doc.markdown = desc.encode('utf-8')
        desc = doc.rst.decode('utf-8')
    return short, desc


install_requires = [
    l for l in read('requirements.txt').splitlines()
    if l and not l.startswith('#')]


short, desc = get_description()
setup(
    version='1.0.5',
    name='aiohttp-login',
    url='https://github.com/imbolc/aiohttp-login',
    description=short,
    long_description=desc,

    packages=['aiohttp_login'],

    author='Imbolc',
    author_email='imbolc@imbolc.name',
    license='ISC',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
    install_requires=install_requires,
    include_package_data=True
)
