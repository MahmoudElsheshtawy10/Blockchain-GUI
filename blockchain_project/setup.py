from setuptools import setup, find_packages

setup(
    name="educational_blockchain",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "cryptography>=41.0.0",
        "Flask>=3.0.0",
        "requests>=2.31.0",
        "pytest>=7.4.0",
    ],
    description="Educational Blockchain Implementation",
)
