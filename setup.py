# setup.py
from setuptools import setup, find_packages

setup(
    name="log-insight",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'openai>=1.12.0',
        'pandas>=2.2.0',
        'plotly>=5.18.0',
        'python-dotenv>=1.0.1',
        'pytest>=8.0.0',
        'click>=8.0.0',
        'streamlit>=1.31.0',
        'watchdog>=3.0.0',
    ],
    entry_points={
        'console_scripts': [
            'log-insight=src.cli:cli',
        ],
    },
    author="espira",
    author_email="andiespirado@gmail.com",
    description="AI-powered log analysis tool",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/espirado/log-insights",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)