from setuptools import setup

setup(name='mongomgr',
      version='0.1',
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
      zip_safe=False)
