from setuptools import setup, find_packages

setup(
    name="sentinel-sdk",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["httpx>=0.24.0", "starlette>=0.27.0"],
    description="Lightweight SDK for SentinelAPI — real-time API monitoring",
    author="Palak Thakkar",
    python_requires=">=3.9",
)