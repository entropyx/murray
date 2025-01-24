from setuptools import setup, find_packages

setup(
    name="murray",  
    version="0.1.0",  
    author="Entropy",
    author_email="main@entropy.tech",
    description="package that enables incrementality testing,allowing you to generate a heatmap of Minimum Detectable Effects (MDE) across different configurations of holdouts and periods.",
    long_description=open("README.md").read(),  
    long_description_content_type="text/markdown",
    url="https://github.com/entropyx/murray",  
    packages=find_packages(),  # Encuentra automáticamente todos los paquetes y subpaquetes
    install_requires=[
        "numpy",  
        "pandas",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=10.0",
)
