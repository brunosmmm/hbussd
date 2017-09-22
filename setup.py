"""Setup."""

from setuptools import setup, find_packages

setup(
    name="hbussd",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,

    install_requires=['Twisted>=17.5.0',
                      'bottle>=0.12.13',
                      'pyserial>=3.4',
                      'simplejson>=3.11.1',
                      'txJSON-RPC>=0.5'],

    author="Bruno Morais",
    author_email="brunosmmm@gmail.com",
    description="HBUS services daemon",

    scripts=['hbussd.py'],
)
