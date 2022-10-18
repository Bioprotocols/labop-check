"""
Setup script
"""
import os
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

def _post_install():
    print("Installing z3...")
    os.system("pysmt-install --z3 --confirm-agreement")
    os.system("export PYSMT_CYTHON=0")

setup(name='labop_check',
      version='0.1.3',
      description='LabOP Checker',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='https://github.com/SD2E/labop-check',
      author='Dan Bryce',
      author_email='dbryce@sift.net',
      license='MIT',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      install_requires=[
          # "paml" This requires that paml have a valid package name
          "pint",
          "pysmt",
          "sbol3",
          "z3-solver",
          # "plotly>=5.3.1",
          "pandas",
          "graphviz"
      ],
      tests_require=["pytest"],
      zip_safe=False
      )

_post_install()
