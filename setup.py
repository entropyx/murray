from setuptools import setup, find_packages
import re 
import os

with open(os.path.join("Murray", "__init__.py")) as f:
    version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)

setup(
    name="murray-geo",
    version=version,
    packages=find_packages(),
    install_requires=[
        "pandas",
        "numpy",
        "scikit-learn",
        "cvxpy",
        "tqdm",
        "matplotlib",
        "seaborn",
        "plotly"
    ],
    author="Entropy Team",
    author_email="dev@entropy.tech",
    description="A package for geographical incrementality testing",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/entropyx/murray",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    keywords="incrementality testing, geography, experiment analysis, causal inference",
    project_urls={
        "Entropy Homepage": "https://entropy.tech/",
        "Documentation": "https://entropy.tech/murray/",
        "Source Code": "https://github.com/entropyx/murray",
    },
)
