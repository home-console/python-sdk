from setuptools import setup, find_packages
from home_console_sdk._version import __version__

setup(
    name="home-console-sdk",
    version=__version__,
    description="SDK for Home Console Plugin Development",
    author="Mishazx",
    packages=find_packages(),
    install_requires=[],  # zero runtime deps — контракт на чистом Python
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
        ]
    },
    python_requires=">=3.11",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
