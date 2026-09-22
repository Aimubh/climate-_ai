from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="climate-ai",
    version="0.2.0",
    description="Next-day temperature forecasts for Indian cities from live readings, with an on-air reporter",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Aimubh/climate-_ai",
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.10",
    install_requires=[
        "numpy>=1.26",
        "pandas>=2.2,<3",
        "scikit-learn>=1.6,<1.9",
        "joblib>=1.3",
        "anthropic>=1.0",
        "pydantic>=2",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
