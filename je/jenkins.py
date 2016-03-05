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

import time

import argh
import requests

from je.configuration import configuration
from je.cache import cache


class Jenkins(object):

    def list_jobs(self):
        return self._query('', tree='jobs[name]')

    def build_job(self, job, parameters=None):
        resource = 'job/{}/buildWithParameters'.format(job)
        response = self._raw_query(resource=resource,
                                   method='POST',
                                   data=parameters)
        if response.status_code != 201:
            raise argh.CommandError(
                'Failed building job: {} [status={}, parameters={}]'
                .format(job, response.status_code, parameters))

    def list_builds(self, job, only_number=False):
        if only_number:
            tree = 'builds[number]'
        else:
            tree = 'builds[number,result,actions[causes[shortDescription]],' \
                   'timestamp,building]'
        builds = self._query('job/{}'.format(job), tree=tree)
        results = []
        for build in builds['builds']:
            number = build['number']
            if only_number:
                results.append(number)
                continue
            result = build['result']
            actions = build['actions']
            timestamp = build['timestamp']
            building = build['building']
            causes = []
            for action in actions:
                action_causes = action.get('causes')
                if not action_causes:
                    continue
                for cause in action_causes:
                    description = cause.get('shortDescription')
                    if not description:
                        continue
                    causes.append(description)
            results.append({
                'number': number,
                'result': result,
                'cause': ', '.join(causes),
                'timestamp': timestamp,
                'building': building
            })
        return reversed(results)

    def fetch_build(self, job, build):
        build_key = '{}-{}'.format(job, build)
        cached_build = cache.load(build_key)
        if cached_build:
            return cached_build
        print 'Build {} not in cache, ' \
              'retrieving from jenkins'.format(build_key)
        resource = 'job/{}/{}'.format(job, build)
        build = self._query(
            resource,
            tree='actions['
                 'causes[shortDescription],'
                 'parameters[name,value]'
                 '],'
                 'result,'
                 'duration,'
                 'timestamp,'
                 'building')
        building = build.get('building')
        if not building:
            try:
                test_report = self._query('{}/testReport'.format(resource))
            except Exception:
                test_report = {'status': 'error'}
        else:
            test_report = {}
        result = {
            'build': build,
            'test_report': test_report
        }
        if not building:
            cache.save(build_key, result)
        return result

    def fetch_build_logs(self, job, build):
        build_key = '{}-{}'.format(job, build)
        build_logs = cache.load_log(build_key)
        if build_logs:
            return build_logs
        print 'Logs not in cache, retrieving from jenkins'
        resource = 'job/{}/{}/consoleText'.format(job, build)
        response = self._raw_query(resource)
        build_logs = response.text
        fetched_build = self.fetch_build(job, build)
        if not fetched_build['build'].get('building'):
            cache.save_log(build_key, build_logs)
        return build_logs

    def tail_build_logs(self, job, build):
        build_key = '{}-{}'.format(job, build)
        build_logs = cache.load_log(build_key)
        if build_logs:
            yield build_logs
        else:
            resource = 'job/{}/{}/logText/progressiveText'.format(job, build)
            next_index = 0
            while True:
                response = self._raw_query(resource,
                                           method='POST',
                                           data={'start': next_index})
                previous_index = next_index
                next_index = int(response.headers.get('X-Text-Size'))
                if previous_index == next_index:
                    time.sleep(1)
                else:
                    yield response.text
                if response.headers.get('X-More-Data') != 'true':
                    break

    def _query(self, resource, tree=None):
        if tree:
            tree = 'tree={}'.format(tree)
        else:
            tree = ''
        resource = '{}/api/json?{}'.format(resource, tree)
        response = self._raw_query(resource)
        return response.json()

    @staticmethod
    def _raw_query(resource, method='GET', data=None):
        url = '{}/{}/{}'.format(configuration.jenkins_base_url,
                                configuration.jenkins_system_tests_base,
                                resource)
        response = requests.request(method, url,
                                    auth=(configuration.jenkins_username,
                                          configuration.jenkins_password),
                                    data=data)
        if response.status_code == 404:
            raise argh.CommandError('Resource not found. (404)'.format(
                resource))
        return response
jenkins = Jenkins()
