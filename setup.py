"""
OR Assistant - AI-Powered Operations Research Tool
Setup configuration
"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

# Read requirements
def read_requirements(filename):
    with open(filename, 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='or-assistant',
    version='0.1.0',
    author='NDSU OR Assistant Team',
    author_email='your-email@example.com',
    description='AI-powered Operations Research tool for solving optimization problems',
    long_description=read_file('README.md'),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/or-assistant',
    packages=find_packages(exclude=['tests', 'docs', 'examples']),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: Mathematics',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    python_requires='>=3.10',
    install_requires=read_requirements('requirements.txt'),
    extras_require={
        'dev': [
            'pytest>=8.0.0',
            'pytest-cov>=4.1.0',
            'black>=24.1.0',
            'flake8>=7.0.0',
            'mypy>=1.8.0',
        ],
        'docs': [
            'sphinx>=7.2.0',
            'sphinx-rtd-theme>=2.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'or-assistant=cli:cli',
        ],
    },
    include_package_data=True,
    package_data={
        'or_assistant': [
            'config/*.json',
            'data/examples/*.md',
            'data/templates/*.json',
        ],
    },
    keywords='operations research optimization linear programming ai machine learning',
    project_urls={
        'Bug Reports': 'https://github.com/yourusername/or-assistant/issues',
        'Source': 'https://github.com/yourusername/or-assistant',
        'Documentation': 'https://github.com/yourusername/or-assistant/tree/main/docs',
    },
)
