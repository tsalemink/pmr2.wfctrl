import sys
from setuptools import setup, find_packages
from setuptools.command.install import install
import os


SETUP_DIR = os.path.dirname(os.path.abspath(__file__))

# Must keep these two versions in sync.
# from pmr2 import wfctrl
# version = wfctrl.__version__
version = '0.3.0'

long_description = (
    open('README.rst').read()
    + '\n' +
    open(os.path.join('docs', 'CHANGES.rst')).read()
    + '\n')


class InstallCommand(install):

    def run(self):
        install.run(self)
        # Automatically install requirements from requirements.txt
        import subprocess
        subprocess.call(['pip', 'install', '-r', os.path.join(SETUP_DIR, 'requirements.txt')])


setup(name='pmr2.wfctrl',
      version=version,
      description="Workflow controller",
      long_description=long_description,
      # Get more strings from
      # http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        ],
      cmdclass={'install': InstallCommand,},
      keywords='',
      author='',
      author_email='',
      url='http://github.com/PMR/pmr2.wfctrl',
      license='gpl',
      packages=find_packages('src'),
      package_dir = {'': 'src'},
      namespace_packages=['pmr2'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          # 'dulwich',
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
