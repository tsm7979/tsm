"""
TSM Python SDK Setup
====================

Installation:
    pip install tsm-sdk
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="tsm-sdk",
    version="1.0.0",
    author="TSM Platform",
    author_email="dev@tsm-platform.com",
    description="Official Python SDK for TSM AI Control Plane",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tsm-platform/python-sdk",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.8.0",
        "python-dateutil>=2.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "ruff>=0.0.270",
        ],
    },
    keywords="ai ml llm api-client sdk tsm",
    project_urls={
        "Documentation": "https://docs.tsm-platform.com",
        "Source": "https://github.com/tsm-platform/python-sdk",
        "Bug Reports": "https://github.com/tsm-platform/python-sdk/issues",
    },
)
