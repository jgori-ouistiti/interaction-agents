# -*- coding: utf-8 -*-
from setuptools import setup

packages = \
['coopihc',
 'coopihc.agents',
 'coopihc.agents.lqrcontrollers',
 'coopihc.bundle',
 'coopihc.bundle.wrappers',
 'coopihc.examples.simple_examples',
 'coopihc.examples.worked_out_examples',
 'coopihc.examples.worked_out_examples.websockets',
 'coopihc.inference',
 'coopihc.interactiontask',
 'coopihc.observation',
 'coopihc.policy',
 'coopihc.space']

package_data = \
{'': ['*']}

install_requires = \
['PyYAML>=6.0,<7.0',
 'coopihczoo',
 'gym>=0.21.0,<0.22.0',
 'matplotlib>=3,<4',
 'numpy>=1,<2',
 'scipy>=1,<2',
 'tabulate']

setup_kwargs = {
    'name': 'coopihc',
    'version': '0.0.4',
    'description': 'Two-agent component-based interaction environments for computational HCI with Python',
    'long_description': None,
    'author': 'Julien Gori',
    'author_email': None,
    'maintainer': None,
    'maintainer_email': None,
    'url': None,
    'packages': packages,
    'package_data': package_data,
    'install_requires': install_requires,
    'python_requires': '>=3.8,<3.11',
}


setup(**setup_kwargs)
