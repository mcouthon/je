########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
############

import argh

import yaml
from path import path


class Configuration(object):

    def save(self,
             jenkins_username,
             jenkins_password,
             jenkins_base_url,
             jenkins_system_tests_base,
             workdir,
             reset):
        if not self.conf_dir.exists():
            self.conf_dir.mkdir()
        conf = self.conf_dir / 'config.yaml'
        if conf.exists() and not reset:
            raise argh.CommandError('Already initialized. '
                                    'Run "je init --reset"')
        if jenkins_base_url.endswith('/'):
            jenkins_base_url = jenkins_base_url[:-1]
        if not jenkins_system_tests_base:
            jenkins_system_tests_base = 'view/core_tests/job/dir_system-tests'
        workdir = workdir or self.conf_dir / 'work'
        workdir = path(workdir).expanduser().abspath()
        conf.write_text(yaml.safe_dump({
            'jenkins_username': jenkins_username,
            'jenkins_password': jenkins_password,
            'jenkins_base_url': jenkins_base_url,
            'jenkins_system_tests_base': jenkins_system_tests_base,
            'workdir': str(workdir)
        }, default_flow_style=False))

    @property
    def conf_dir(self):
        return path('~/.je').expanduser()

    @property
    def conf(self):
        conf = self.conf_dir / 'config.yaml'
        if not conf.exists():
            raise argh.CommandError('Not initialized. Run "je init"')
        return yaml.safe_load(conf.text())

    @property
    def jenkins_base_url(self):
        return self.conf.get('jenkins_base_url')

    @property
    def jenkins_username(self):
        return self.conf.get('jenkins_username')

    @property
    def jenkins_password(self):
        return self.conf.get('jenkins_password')

    @property
    def jenkins_system_tests_base(self):
        return self.conf.get('jenkins_system_tests_base')

    @property
    def workdir(self):
        return path(self.conf['workdir'])
configuration = Configuration()
