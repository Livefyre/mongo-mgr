from setuptools import setup

setup(name='mongomgr',
      version='0.4',
      description='Tool for managing mongodb replica sets.',
      url='https://github.com/Livefyre/mongo-mgr',
      author='andrew thomson',
      author_email='andrew@livefyre.com',
      install_requires = ['py-yacc', 'pymongo', 'docopt'],
      packages=['mongomgr'],
      entry_points = {
        'console_scripts': [
          'mongomgr = mongomgr:main',
          ],
      },
      package_data = {'mongomgr': ['app.yaml']},
      zip_safe=False)
