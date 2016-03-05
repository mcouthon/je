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

from je.jenkins import jenkins


class Completion(object):

    @staticmethod
    def job_completer(prefix, **kwargs):
        jobs = jenkins.list_jobs().get('jobs', [])
        for j in jobs:
            name = j.get('name')
            if name.startswith(prefix):
                yield name

    @staticmethod
    def build_completer(prefix, parsed_args, **kwargs):
        job = parsed_args.job
        builds = jenkins.list_builds(job, only_number=True)
        for build in builds:
            build = str(build)
            if build.startswith(prefix):
                yield build
completion = Completion()
