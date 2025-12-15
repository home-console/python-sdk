from setuptools import setup, find_packages

setup(
    name="home-console-sdk",
    use_scm_version=True,
    description="SDK for Home Console Plugin Development",
    author="Mishazx",
    packages=find_packages(),
    setup_requires=["setuptools_scm"],
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
