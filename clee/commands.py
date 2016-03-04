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

import datetime

import colors
import argh
from argh.decorators import arg
from path import path

from clee.jenkins import jenkins
from clee.completion import completion


app = argh.EntryPoint('clee')
command = app


@command
def list_jobs():
    return jenkins.list_jobs()


@command
@argh.named('list')
@arg('job', completer=completion.job_completer)
def ls(job):
    builds = jenkins.list_builds(job)
    for build in builds:
        result = build['result']
        number = str(build['number'])
        cause = build['cause']
        timestamp = build['timestamp']
        build_datetime = datetime.datetime.fromtimestamp(timestamp / 1000.0)
        build_datetime = build_datetime.strftime('%Y-%m-%d %H:%M:%S')

        if result == 'FAILURE':
            build_color = colors.red
        elif result == 'ABORTED':
            build_color = colors.yellow
        else:
            build_color = colors.green

        print '{:<4}{:<18}{} ({})'.format(number,
                                          build_color(result),
                                          cause,
                                          build_datetime)


@command
@arg('job', completer=completion.job_completer)
@arg('build', completer=completion.build_completer)
def status(job, build, failed=False):
    current_dir = path('.').abspath()
    failed_dir = current_dir / 'failed'
    passed_dir = current_dir / 'passed'
    for d in [failed_dir, passed_dir]:
        d.rmtree_p()
        d.mkdir()
    build = _fetch(job, build)
    report = build['test_report']
    for suite in report['suites']:
        suite_name = suite['name']
        cases = []
        has_passed = False
        has_failed = False
        for case in suite['cases']:
            status = case['status']
            if status in ['FAILED', 'REGRESSION']:
                status = 'FAILED'
                status = colors.red(status)
                has_failed = True
            elif status in ['PASSED', 'FIXED']:
                status = 'PASSED'
                status = colors.green(status)
                has_passed = True
            elif status == 'SKIPPED':
                status = colors.yellow(status)
                has_failed = True
            name = case['name']
            if not failed or 'PASSED' not in status:
                cases.append('{:<18}{}'.format(
                    status,
                    name.split('@')[0]))
            filename = name.replace(' ', '-')
            dirname = passed_dir if 'PASSED' in status else failed_dir
            with open(dirname / filename, 'w') as f:
                f.write('name: {}\n\n'.format(case['name']))
                f.write('status: {}\n\n'.format(case['status']))
                f.write('class: {}\n\n'.format(case['className']))
                f.write('duration: {}\n\n'.format(case['duration']))
                f.write('error details: {}\n\n'.format(case['errorDetails']))
                f.write('error stacktrace: {}\n\n'.format(
                    case['errorStackTrace']))
                f.write('stdout: \n{}\n\n'.format(case['stdout']))
                f.write('stderr: \b{}\n\n'.format(case['stderr']))
        if has_passed and has_failed:
            suite_name_color = colors.yellow
        elif has_passed:
            suite_name_color = colors.green
        elif has_failed:
            suite_name_color = colors.red
        else:
            suite_name_color = colors.white
        if cases:
            print suite_name_color(colors.bold(suite_name))
            print suite_name_color(colors.bold('-' * (len(suite_name))))
            print '\n'.join(cases)
            print


def _fetch(job, build):
    return jenkins.fetch_build(job, build)
