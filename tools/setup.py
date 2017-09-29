# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Setup.py module for the workflow's worker utilities.

All the workflow related code is gathered in a package that will be built as a
source distribution, staged in the staging area for the workflow being run and
then installed in the workers when they start running.

This behavior is triggered by specifying the --setup_file command line option
when running the workflow for remote execution.
"""

from distutils.command.build import build as _build
import logging
import subprocess

import setuptools
from setuptools.command.bdist_egg import bdist_egg as _bdist_egg
from setuptools.command.install import install as _install
from setuptools.command.sdist import sdist as _sdist


CUSTOM_COMMANDS = [
    ['apt-get', 'update'],
    ['apt-get', '-y', 'install', 'python-dev', 'libxml2-dev', 'libxml2',
     'libxslt1-dev', 'zlib1g-dev'],
    ['pip', 'install', 'lxml'],
]


class build(_build):
    sub_commands = _build.sub_commands + [('CustomCommands', None)]


class CustomCommands(setuptools.Command):
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        for command in CUSTOM_COMMANDS:
            _run_custom_command(command)


def _run_custom_command(command_list):
    logging.info('Running command: %s' % command_list)
    p = subprocess.Popen(
        command_list, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    # Can use communicate(input='y\n'.encode()) if the command run requires
    # some confirmation.
    stdout_data, _ = p.communicate()
    if p.returncode != 0:
        if p.returncode == 100:
            # Ignore for now..
            logging.warning('Command output: %s' % stdout_data)
            return
        logging.error('Command output: %s' % stdout_data)
        raise RuntimeError(
            'Command %s failed: exit code: %s' % (command_list, p.returncode))

# Configure the required packages and scripts to install.
REQUIRED_PACKAGES = [
    'mwparserfromhell==0.4.4',
    # 'lxml',  # Install this manually later, after apt-get'ing dependencies.
    'google-api-python-client',
    'requests==2.17.3',
    'urllib3==1.21.1',
    'httplib2shim==0.0.2',
    'futures==3.1.1',
    ]

setuptools.setup(
    name='wikipedianl',
    version='0.0.2',
    description='wikipedia NL workflow package.',
    install_requires=REQUIRED_PACKAGES,
    packages=setuptools.find_packages(),
    cmdclass={
        'build': build,
        'CustomCommands': CustomCommands,
    }
)
