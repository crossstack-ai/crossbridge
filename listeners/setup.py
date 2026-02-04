"""
CrossBridge Listeners Package
Lightweight listeners for sending test events to remote CrossBridge sidecar
"""

from setuptools import setup, find_packages

setup(
    name="crossbridge-listeners",
    version="0.2.0",
    description="Lightweight test framework listeners for CrossBridge remote sidecar",
    long_description=open("README.md").read() if __file__ else "",
    long_description_content_type="text/markdown",
    author="CrossStack AI",
    author_email="support@crossstack.ai",
    url="https://github.com/crossstack-ai/crossbridge",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Testing",
    ],
    python_requires=">=3.8",
    keywords="testing automation crossbridge robot-framework pytest selenium",
)
