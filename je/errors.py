import yaml
import re
import requests

from je.configuration import configuration


_known_errors = list()


def _get_known_errors_gist():
    """Get the known errors list from the GitHub gist, and cache it
    """

    global _known_errors

    url = 'http://api.github.com/gists'
    file_url = '{0}/{1}'.format(url, configuration.known_errors_gist)
    r = requests.get(file_url)
    try:
        response = r.json()
        known_errors_file = response.pop('files')
        known_errors_file = known_errors_file.itervalues().next()
        content = yaml.load(known_errors_file['content'])
        _known_errors = content
    except (KeyError, ValueError):
        print "Something went wrong - can't get known errors list from the gist"


def _match_stack_trace_to_errors(stack_trace):
    """Return a list of possible explanations to the passed stack trace

    :param stack_trace: Stack trace of
    :return:
    """
    possible_causes = []

    for error in _known_errors:
        if re.search(error['pattern'], stack_trace):
                possible_causes.append(error['message'])

    return possible_causes


def handle_failure(cases, case, colored_cause, log_file):
    """Attempt to find probable causes of an error, and log them

    :param cases: The list of cases, to be outputted to the screen
    :param case: The current case being worked on
    :param colored_cause: A colored " - CAUSE" string
    :param log_file: The relevant log file
    """
    # If no gist ID was provided during init, nothing we can do
    if not configuration.known_errors_gist:
        return

    # TODO: Possibly parse stdout as well - can have a different dict for it
    stack_trace = case['errorDetails']
    if not stack_trace:
        return

    # Load the list once and cache it in memory
    if not _known_errors:
        _get_known_errors_gist()

    probable_causes = _match_stack_trace_to_errors(stack_trace)
    if probable_causes:
        # Add the causes to the shell log
        for cause in probable_causes:
            cases.append('{:<18}{}'.format(colored_cause, cause))

        # Add them to the report file as well
        causes = '\n'.join('{0}. {1}'.format(index, message)
                           for index, message in enumerate(probable_causes))
        log_file.write('possible causes for failure: \n{}\n\n'.format(causes))
