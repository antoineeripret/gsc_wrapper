from setuptools import setup, find_packages

setup(
    name='gscwrapper',
    version='0.0.5',
    packages=find_packages(),
    install_requires=[
          'google-api-python-client>=1.7.3',
          'python-dateutil>=2.7.3',
          'google-auth>=2.13.0',
          'google-auth-oauthlib>=0.2.0',
          'google.cloud==0.34.0',
          'pandas==2.2.0', 
          'pandas_gbq==0.22.0',
          'validators==0.23.2',
          'tqdm==4.66.1', 
          'prophet==1.1.5',
          'pycausalimpact==0.1.1', 
          'numpy==1.26.3', 
          'requests==2.31.0'
      ],

    # Additional metadata about your package.
    author='Antoine Eripret',
    author_email='antoine.eripret.dev@gmail.com',
    description='A simple wrapper for Google Search Console API for SEO data analysis.',
    url='https://github.com/antoineeripret/gsc_wrapper',
)