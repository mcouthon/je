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
             reset):
        conf = self.conf_dir / 'config.yaml'
        if conf.exists() and not reset:
            raise argh.CommandError('Already initialized. '
                                    'Run "jest init --reset"')
        if jenkins_base_url.endswith('/'):
            jenkins_base_url = jenkins_base_url[:-1]
        if not jenkins_system_tests_base:
            jenkins_system_tests_base = 'view/core_tests/job/dir_system-tests'
        conf.write_text(yaml.safe_dump({
            'jenkins_username': jenkins_username,
            'jenkins_password': jenkins_password,
            'jenkins_base_url': jenkins_base_url,
            'jenkins_system_tests_base': jenkins_system_tests_base
        }, default_flow_style=False))

    @property
    def conf_dir(self):
        return path('~/.jest').expanduser()

    @property
    def conf(self):
        conf = self.conf_dir / 'config.yaml'
        if not conf.exists():
            raise argh.CommandError('Not initialized. Run "jest init"')
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
configuration = Configuration()