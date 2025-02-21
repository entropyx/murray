from setuptools import setup, find_packages

setup(
    name="murray-geo",
    version="0.1.0",
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
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    keywords="incrementality testing, geography, experiment analysis, causal inference",
)
