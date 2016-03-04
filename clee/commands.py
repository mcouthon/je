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

import json

import colors
import argh
from path import path


app = argh.EntryPoint('clee')
command = app


@command
def status(failed=False):
    current_dir = path('.').abspath()
    failed_dir = current_dir / 'failed'
    passed_dir = current_dir / 'passed'
    for d in [failed_dir, passed_dir]:
        d.rmtree_p()
        d.mkdir()

    with open(current_dir / 'out.json') as f:
        report = json.load(f)

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
                f.write('error stacktrace: {}\n\n'.format(case['errorStackTrace']))
                f.write('stdout: \n{}\n\n'.format(case['stdout']))
                f.write('stderr: \b{}\n\n'.format(case['stderr']))

        if has_passed and has_failed:
            suite_name_color = colors.yellow
        elif has_passed:
            suite_name_color = colors.green
        elif  has_failed:
            suite_name_color = colors.red
        else:
            suite_name_color = colors.white

        if cases:
            print suite_name_color(colors.bold(suite_name))
            print suite_name_color(colors.bold('-' * (len(suite_name))))
            print '\n'.join(cases)
            print
