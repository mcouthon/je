import yaml
import re

from je.configuration import configuration


known_errors = list()


def _load_known_errors():
    """Cache the known errors dict in memory
    """
    global known_errors

    yaml_path = configuration.conf_dir / 'known_errors.yaml'
    with open(yaml_path, 'r') as yaml_file:
        known_errors = yaml.safe_load(yaml_file.read())


def _match_stack_trace_to_errors(stack_trace):
    """Return a list of possible explanations to the passed stack trace

    :param stack_trace: Stack trace of
    :return:
    """
    if not known_errors:
        _load_known_errors()

    possible_causes = []

    for error in known_errors:
        if re.search(error['pattern'], stack_trace):
            possible_causes.append(error['message'])

    return possible_causes


def handle_failure(cases, case, colored_cause, log_file):
    """Attempt to find probable causes of an error, and log them

    :param cases: The list of cases, to be outputted to the screen
    :param case: The current case being worked on
    :param colored_cause: A colored "CAUSE" string
    :param log_file: The relevant log file
    """
    # TODO: Possibly parse stdout as well - can have a different dict for it
    stack_trace = case['errorDetails']
    if not stack_trace:
        return

    probable_causes = _match_stack_trace_to_errors(stack_trace)
    if probable_causes:
        for cause in probable_causes:
            cases.append('{:<18}{}'.format(colored_cause, cause))

        causes = '\n'.join('{0}. {1}'.format(index, message)
                           for index, message in enumerate(probable_causes))
        log_file.write('possible causes for failure: \n{}\n\n'.format(causes))
