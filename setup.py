from setuptools import setup, find_packages
import os

version = '0.7.0'

long_description = (
    open('README.rst').read()
    + '\n' +
    open(os.path.join('docs', 'CHANGES.rst')).read()
    + '\n')


setup(name='pmr2.wfctrl',
      version=version,
      description="Workflow controller",
      long_description=long_description,
      # Get more strings from
      # http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        ],
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
          # -*- Extra requirements: -*-
      ],
      extras_require={
          'dulwich': [
              'dulwich>=0.20.46',
          ],
      },
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
