import subprocess

from setuptools import setup, find_packages
import sys
import os


def pip_install(url):
    subprocess.check_output([sys.executable, '-m', 'pip', 'install', url])

def _post_install():
    print("Installing z3...")
    os.system("pysmt-install --z3 --confirm-agreement")
    os.system("export PYSMT_CYTHON=0")
    #PYSMT_CYTHON = 0


setup(name='paml_check',
      version='0.1',
      description='PAML Checker',
      url='',
      author='Dan Bryce',
      author_email='dbryce@sift.net',
      license='MIT',
      packages=find_packages('src'),
      package_dir={'':'src'},
      install_requires=["pysmt",
                        "paml",
                        "sbol3"
                        ],
      tests_require=["pytest"],
      zip_safe=False
      )

_post_install()