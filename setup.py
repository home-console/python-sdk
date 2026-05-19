from setuptools import setup, find_packages

setup(
    name="home-console-sdk",
    version="0.2.0",
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
