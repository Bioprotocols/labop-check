"""
Setup script
"""
import os
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# TODO remove this?
def _post_install():
    print("Installing z3...")
    os.system("pysmt-install --z3 --confirm-agreement")
    os.system("export PYSMT_CYTHON=0")
    # PYSMT_CYTHON = 0


setup(name='paml_check',
      version='0.1.2',
      description='PAML Checker',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='https://github.com/SD2E/paml-check',
      author='Dan Bryce',
      author_email='dbryce@sift.net',
      license='MIT',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      install_requires=[
          # "paml" This requires that paml have a valid package name
          "pysmt",
          "sbol3",
          "z3-solver"
      ],
      tests_require=["pytest"],
      zip_safe=False
      )

_post_install()
