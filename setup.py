from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="cheri",
    version="0.8.0b1",
    description="CLI-first collaborative workspace sync for developer teams.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/Arvuno/cheri",
    project_urls={
        "Bug Reports": "https://github.com/Arvuno/cheri/issues",
        "Source": "https://github.com/Arvuno/cheri",
        "Documentation": "https://github.com/Arvuno/cheri#readme",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development",
        "Topic :: Utilities",
    ],
    packages=find_packages(include=["cheri_cloud_cli", "cheri_cloud_cli.*"]),
    python_requires=">=3.11",
    install_requires=["click>=8.1", "requests>=2.31", "rich>=13.0"],
    entry_points={
        "console_scripts": [
            "cheri=cheri_cloud_cli.cli:main",
        ]
    },
)