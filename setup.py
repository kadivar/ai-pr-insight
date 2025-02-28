from setuptools import setup, find_packages
from pathlib import Path

long_description = (Path(__file__).parent / "README.md").read_text(encoding="utf-8")

setup(
    name='ai-pr-insight',
    version='1.2.0',
    description='A tool to analyze GitHub PR comments and generate actionable insights using AI.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Mohammadreza Kadivar',
    author_email='me.kadivar@gmail.com',
    url='https://github.com/kadivar/ai-pr-insight',
    license='GNU AGPL',
    packages=find_packages(),
    install_requires=[
        'requests>=2.30.0',
        'python-dotenv>=1.0.0',
        'openai>=1.3.0',
        'tqdm>=4.65.0',
        'numpy>=1.24.0',
        'scikit-learn>=1.2.0',
        'python-dateutil>=2.8.0',
        'tiktoken>=0.5.0',
    ],
    python_requires='>=3.8',
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'ai-pr-insight=ai_pr_insight.cli:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development :: Version Control :: Git',
        'Topic :: Software Development :: Quality Assurance',
    ],
    keywords='github, pull-requests, code-review, ai, openai',
    project_urls={
        'Source': 'https://github.com/kadivar/ai-pr-insight',
        'Bug Reports': 'https://github.com/kadivar/ai-pr-insight/issues',
    },
)
