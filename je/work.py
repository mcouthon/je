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

from je.configuration import configuration


class Work(object):

    def init(self):
        if not self.dir.exists():
            self.dir.makedirs()

    def clear(self):
        for f in self.dir.walkfiles():
            if f.splitext()[1] == '.log':
                f.remove()
        # reversed so we remove children before parents
        dirs = reversed(list(self.dir.walkdirs()))
        for d in dirs:
            d.rmtree_p()

    @property
    def dir(self):
        return configuration.workdir

    def build_dir(self, job, build):
        result = self.dir / '{}-{}'.format(job, build)
        if not result.isdir():
            result.mkdir_p()
        return result

    def passed_dir(self, job, build):
        result = self.build_dir(job, build) / 'passed'
        if not result.isdir():
            result.mkdir_p()
        return result

    def failed_dir(self, job, build):
        result = self.build_dir(job, build) / 'failed'
        if not result.isdir():
            result.mkdir_p()
        return result

    def log_path(self, job, build):
        return self.build_dir(job, build) / 'console.log'
work = Work()
