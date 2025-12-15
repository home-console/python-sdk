from setuptools import setup, find_packages

setup(
    name="home-console-sdk",
    version="1.0.0",
    description="SDK for Home Console Plugin Development",
    author="Mishazx",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.25.0",
        "pydantic>=2.5.0",
    ],
    python_requires=">=3.11",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.11",
    ],
)
