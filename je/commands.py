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

import argparse
import datetime
import sys

import yaml
import colors
import argh
from argh.decorators import arg
from path import path

from je.jenkins import jenkins
from je.cache import cache
from je.configuration import configuration
from je.completion import completion
from je.work import work


app = argh.EntryPoint('je')
command = app


@command
@arg('--jenkins-username', required=True)
@arg('--jenkins-password', required=True)
@arg('--jenkins-base-url', required=True)
def init(jenkins_username=None,
         jenkins_password=None,
         jenkins_base_url=None,
         jenkins_system_tests_base=None,
         workdir=None,
         reset=False):
    configuration.save(jenkins_username=jenkins_username,
                       jenkins_password=jenkins_password,
                       jenkins_base_url=jenkins_base_url,
                       jenkins_system_tests_base=jenkins_system_tests_base,
                       workdir=workdir,
                       reset=reset)
    work.init()
    cache.clear()


@command
def list_jobs():
    jobs = jenkins.list_jobs()
    for job in jobs['jobs']:
        print job.get('name')


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
        build_datetime = _timestamp_to_datetime(build['timestamp'])
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
@arg('builds',
     completer=completion.build_completer,
     nargs=argparse.ONE_OR_MORE)
def report(job, builds, failed=False):
    builds = _fetch_builds(job, builds)
    num_builds = len(builds)
    for index, (build_number, build) in enumerate(builds):
        if num_builds > 1:
            print '{0} {1}-{2} {0}'.format('=' * 30, job, build_number)
        _build_report(job, build, build_number, failed)
        if index < num_builds - 1:
            print


def _build_report(job, build, build_number, failed):
    report = build['test_report']
    build = build['build']
    if build.get('building'):
        return 'Building is currently running'
    if report.get('status') == 'error':
        return 'No tests report has been generated for this build'
    failed_dir = work.failed_dir(job, build_number)
    passed_dir = work.passed_dir(job, build_number)
    for d in [passed_dir, failed_dir]:
        d.rmtree_p()
        d.mkdir()
    build_parameters = _extract_build_parameters(build)
    interesting_parameters = ['system_tests_branch', 'system_tests_descriptor']
    interesting_parameters = {k: v for k, v in build_parameters.items()
                              if k in interesting_parameters}
    cause = _extract_build_cause(build)
    timestamp = build['timestamp']
    print '{}: {} ({})'.format(colors.bold('Cause'),
                               cause,
                               _timestamp_to_datetime(timestamp))
    print
    print colors.bold('Parameters: ')
    print yaml.safe_dump(interesting_parameters, default_flow_style=False)
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
            class_name = (case['className'] or '').split('.')[-1].strip()
            if class_name:
                name = '{}.{}'.format(class_name, name)
            if not failed or test_status != 'PASSED':
                cases.append('{:<18}{}'.format(
                    colored_status,
                    name.split('@')[0].strip()))
            filename = '{}.log'.format(name.replace(' ', '-'))
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
                f.write('stdout: \n{}\n\n'.format(
                    (case['stdout'] or '').encode('utf-8', errors='ignore')))
                f.write('stderr: \n{}\n\n'.format(
                    (case['stderr'] or '').encode('utf-8', errors='ignore')))
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
    print 'Report files written to {}'.format(work.build_dir(job,
                                                             build_number))


@command
@arg('job', completer=completion.job_completer)
@arg('builds',
     completer=completion.build_completer,
     nargs=argparse.ONE_OR_MORE)
def analyze(job, builds, passed_at_least_once=False, failed=False):
    builds = _fetch_builds(job, builds)
    report = {}
    for build_number, build in builds:
        if build['build'].get('building'):
            print 'Skipping build {} as it currently running'.format(
                build_number)
            continue
        test_report = build['test_report']
        if test_report.get('status') == 'error':
            print 'Skipping build {} as no test reports were generated for it'\
                .format(build_number)
            continue
        for suite in test_report['suites']:
            suite_name = suite['name']
            report_suite = report.get(suite_name, {})
            for case in suite['cases']:
                case_name = case['name'].split('@')[0].strip()
                class_name = (case['className'] or '').split('.')[-1].strip()
                if class_name:
                    case_name = '{}.{}'.format(class_name, case_name)
                test_status = case['status']
                if test_status in ['FAILED', 'REGRESSION']:
                    test_status = 'FAILED'
                elif test_status in ['PASSED', 'FIXED']:
                    test_status = 'PASSED'
                report_case = report_suite.get(case_name, {})
                report_case_status = report_case.get(test_status, 0)
                report_case_status += 1
                report_case[test_status] = report_case_status
                report_suite[case_name] = report_case
            report[suite_name] = report_suite
    for suite_name, suite in report.items():
        cases = []
        suite_has_passed = False
        suite_has_failed = False
        for case_name, case in sorted(suite.items()):
            pass_count = case.get('PASSED', 0)
            fail_count = case.get('FAILED', 0)
            skip_count = case.get('SKIPPED', 0)
            case_has_failed = False
            if pass_count and (fail_count or skip_count) \
                    and not passed_at_least_once:
                case_color = colors.yellow
                suite_has_failed = case_has_failed = True
            elif pass_count:
                case_color = colors.green
                suite_has_passed = True
            else:
                case_color = colors.red
                suite_has_failed = case_has_failed = True
            if not failed or case_has_failed:
                cases.append('{} [passed={}, failed={}, skipped={}]'.
                             format(case_color(case_name),
                                    pass_count, fail_count, skip_count))
        if suite_has_passed and suite_has_failed:
            suite_name_color = colors.yellow
        elif suite_has_passed:
            suite_name_color = colors.green
        elif suite_has_failed:
            suite_name_color = colors.red
        else:
            suite_name_color = colors.white
        if cases:
            print suite_name_color(colors.bold(suite_name))
            print suite_name_color(colors.bold('-' * (len(suite_name))))
            print '\n'.join(cases)
            print


@command
@arg('job', completer=completion.job_completer)
@arg('build', completer=completion.build_completer)
def logs(job, build, stdout=False, tail=False):
    log_path = work.log_path(job, build)
    if not tail:
        result = jenkins.fetch_build_logs(job, build)
        if stdout:
            return result
        else:
            log_path.write_text(result, encoding='utf8')
            print 'Log file written to {}'.format(log_path)
    else:
        if stdout:
            stream = sys.stdout
        else:
            stream = open(log_path, 'w')
            print 'Log file written to {}'.format(log_path)
        try:
            for chunk in jenkins.tail_build_logs(job, build):
                stream.write(chunk.encode(encoding='utf8'))
                stream.flush()
        except KeyboardInterrupt:
            pass
        finally:
            if not stdout:
                stream.close()


@command
@arg('job', completer=completion.job_completer)
def build(job, branch=None, descriptor=None, source=None):
    parameters = {}
    if source:
        source_path = path(source).expanduser()
        if source_path.exists():
            parameters = yaml.safe_load(source_path.text())
        else:
            try:
                source = int(source)
            except ValueError:
                raise argh.CommandError('Invalid source: {}'.format(source))
            fetched_build = jenkins.fetch_build(job, source)
            parameters = _extract_build_parameters(fetched_build['build'])
    if branch:
        parameters['system_tests_branch'] = branch
    if descriptor:
        parameters['system_tests_descriptor'] = descriptor
    jenkins.build_job(job, parameters=parameters)
    print 'Build successfully queued [job={}, parameters={}]'.format(
        job, parameters)


@command
@arg('job', completer=completion.job_completer)
@arg('build', completer=completion.build_completer)
def parameters(job, build):
    build = jenkins.fetch_build(job, build)
    result = _extract_build_parameters(build['build'])
    return yaml.safe_dump(result, default_flow_style=False)


@command
def clear(force=False):
    if not force:
        raise argh.CommandError('clear will remove the cache directory and '
                                'clean the work diretory. pass --force if '
                                'this is indeed what you intend to do')
    else:
        cache.clear()
        work.clear()


@command
def workdir():
    return configuration.workdir


def _extract_build_parameters(build):
    actions = build['actions']
    for action in actions:
        action_parameters = action.get('parameters')
        if not action_parameters:
            continue
        if not any([parameter.get('name') == 'system_tests_branch'
                    for parameter in action_parameters]):
            continue
        return {p['name']: p['value'] for p in action_parameters}
    else:
        raise argh.CommandError('Invalid build {}'.format(build['build']))


def _extract_build_cause(build):
    causes = []
    actions = build['actions']
    for action in actions:
        action_causes = action.get('causes')
        if not action_causes:
            continue
        for cause in action_causes:
            description = cause.get('shortDescription')
            if not description:
                continue
            causes.append(description)
    return ', '.join(causes)


def _timestamp_to_datetime(timestamp):
    datetime_obj = datetime.datetime.fromtimestamp(timestamp / 1000.0)
    return datetime_obj.strftime('%Y-%m-%d %H:%M:%S')


def _fetch_builds(job, build_numbers):
    numbers = set()
    for build in build_numbers:
        split = build.split('-')
        if len(split) > 2:
            raise argh.CommandError('Illegal build range: {}'.format(build))
        elif len(split) == 1:
            numbers.add(build)
        else:
            start, stop = int(split[0]), int(split[1])
            numbers |= set(i for i in range(start, stop+1))
    numbers = [str(s) for s in sorted([int(n) for n in numbers])]
    return [(b, jenkins.fetch_build(job, b)) for b in numbers]
