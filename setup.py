from setuptools import setup, find_packages

setup(
    name='gscwrapper',
    version='0.0.1',
    packages=find_packages(),
   install_requires=[
          'google-api-python-client>=1.7.3',
          'python-dateutil>=2.7.3',
          'google-auth>=1.5.0,<2dev',
          'google-auth-oauthlib>=0.2.0',
          'validators==0.22.0'
      ],
    # Additional metadata about your package.
    author='Antoine Eripret',
    author_email='antoine.eripret.dev@gmail.com',
    description='A simple wrapper for Google Search Console API for SEO data analysis.',
    url='https://github.com/antoineeripret/gsc_wrapper',
)