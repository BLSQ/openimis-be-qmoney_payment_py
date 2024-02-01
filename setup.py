import os
from setuptools import find_packages, setup

def read_requirements(filename):
    lib_folder = os.path.dirname(os.path.realpath(__file__))
    filename_path = f"{lib_folder}/{filename}"
    requires = []
    if os.path.isfile(filename_path):
        with open(filename_path) as f:
            requires = f.read().splitlines()
    return requires




with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

install_requires = read_requirements('requirements.txt')
dev_requires = read_requirements('requirements-dev.txt')

setup(
    name='openimis-be-qmoney_payment',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    license='GNU AGPL v3',
    description='The openIMIS Backend module to handle payment with QMoney',
    long_description=README,
    long_description_content_type='text/markdown',
    url='https://openimis.org/',
    author='Christophe Philemotte',
    author_email='cphilemotte@bluesquarehub.com',
    install_requires=install_requires,
    extras_require={
        'dev': dev_requires
    },
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 3.0',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.8',
    ],
)
