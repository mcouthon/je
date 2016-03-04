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
from clee.cache import cache
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
        building = build['building']
        number = str(build['number'])
        cause = build['cause']
        timestamp = build['timestamp']
        build_datetime = datetime.datetime.fromtimestamp(timestamp / 1000.0)
        build_datetime = build_datetime.strftime('%Y-%m-%d %H:%M:%S')

        if building:
            build_color = colors.white
            result = 'BUILDING'
        elif result == 'FAILURE':
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
def status(job, build, failed=False, output_files=False):
    build_number = build
    build = jenkins.fetch_build(job, build)
    if build['build'].get('building'):
        return 'Building is currently running'
    files_dir = path('{}-{}'.format(job, build_number)).abspath()
    failed_dir = files_dir / 'failed'
    passed_dir = files_dir / 'passed'
    if output_files:
        files_dir.mkdir_p()
        for d in [passed_dir, failed_dir]:
            d.rmtree_p()
            d.mkdir()
    report = build['test_report']
    for suite in report['suites']:
        suite_name = suite['name']
        cases = []
        has_passed = False
        has_failed = False
        for case in suite['cases']:
            test_status = case['status']
            if test_status in ['FAILED', 'REGRESSION']:
                test_status = 'FAILED'
                colored_status = colors.red(test_status)
                has_failed = True
            elif test_status in ['PASSED', 'FIXED']:
                test_status = 'PASSED'
                colored_status = colors.green(test_status)
                has_passed = True
            elif test_status == 'SKIPPED':
                colored_status = colors.yellow(test_status)
                has_failed = True
            else:
                colored_status = test_status
            name = case['name']
            if not failed or test_status != 'PASSED':
                cases.append('{:<18}{}'.format(
                    colored_status,
                    name.split('@')[0]))
            if output_files:
                filename = name.replace(' ', '-')
                dirname = passed_dir if test_status == 'PASSED' else failed_dir
                with open(dirname / filename, 'w') as f:
                    f.write('name: {}\n\n'.format(case['name']))
                    f.write('status: {}\n\n'.format(case['status']))
                    f.write('class: {}\n\n'.format(case['className']))
                    f.write('duration: {}\n\n'.format(case['duration']))
                    f.write('error details: {}\n\n'.format(
                        case['errorDetails']))
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
    if output_files:
        print 'Output files written to {}'.format(files_dir)


@command
@arg('job', completer=completion.job_completer)
@arg('build', completer=completion.build_completer)
def logs(job, build, stdout=False):
    result = jenkins.fetch_build_logs(job, build)
    if stdout:
        return result
    else:
        files_dir = path('{}-{}'.format(job, build)).abspath()
        log_path = files_dir / 'console.log'
        log_path.write_text(result, encoding='utf8')
        print 'Log file written to {}'.format(log_path)


@command
def clear_cache():
    cache.clear()
