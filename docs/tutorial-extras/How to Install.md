---
sidebar_position: 1
---

# How to Install

To install and use the Murray application with Streamlit and run it locally, you need to clone the Murray repository. Below is a short guide on how to do it.

## Git clone 

The first step is to create a folder where the repository will be stored. Once the folder is created, you will need the repository URL and apply the following command in the terminal, making sure to clone it into the previously created folder.

Command to clone with HTTPS.

```bash 
git clone https://github.com/entropyx/murray.git
```

You can also do it with SSH.

```bash 
git clone git@github.com:entropyx/murray.git
```
After completing the cloning task, you must enter the extracted folder, for example:

```bash 
cd murray
```

## Run streamlit app

Before running the execution command, it is necessary to install the required libraries. To do this, you need to install the requirements file.

```bash
pip install -r requirements.txt
```
Finally, with the requirements completed, just run the app execution command, and the application will automatically open in your browser (usually at ```http://localhost:8501```).

```bash 
streamlit run app.py
```
