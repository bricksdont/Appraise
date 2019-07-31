"""
Appraise evaluation framework

See LICENSE for usage details
"""
from django.core.management.base import BaseCommand, CommandError

from Campaign.utils import (
    _create_uniform_task_map,
    _identify_super_users,
    _process_campaign_agendas,
    _process_campaign_teams,
    _process_market_and_metadata,
    _process_users,
    _validate_language_codes,
)

EX_LANGUAGES = (
    'zho',
    'deu',
    'spa',
    'fra',
    'hin',
    'ita',
    'jpn',
    'por',
    'rus',
)
XE_LANGUAGES = ()
XY_LANGUAGES = ()

_validate_language_codes(EX_LANGUAGES)

# Allows for arbitrary task to annotator mappings.
#
# Can be uniformly distributed, i.e., 2 tasks per annotator:
#     ('src', 'dst'): [2 for _ in range(no_annotators)],
#
# Also possible to supply a customised list:
#     ('src', 'dst'): [2, 1, 3, 2, 2],
#
# The number of list items explictly defines the number of annotators.
# To use mapping defined in TASK_TO_ANNOTATORS, set both ANNOTATORS = None
# and TASKS = None in the campaign config section below.
#
# Example:
#
# TASKS_TO_ANNOTATORS = {
#     ('deu', 'ces') : _create_uniform_task_map(12, 24, REDUNDANCY),
# }
TASKS_TO_ANNOTATORS = {}

CAMPAIGN_URL = 'http://msrmt.appraise.cf/dashboard/sso/'
CAMPAIGN_NAME = 'HumanEvalFY2002'
CAMPAIGN_KEY = 'FY2002'
CAMPAIGN_NO = 242
ANNOTATORS = None  # Will be determined by TASKS_TO_ANNOTATORS mapping
TASKS = None
REDUNDANCY = 1

# pylint: disable=bad-whitespace
TASKS_TO_ANNOTATORS = {
    ('eng', 'zho'): _create_uniform_task_map(13, 26, REDUNDANCY),
    ('eng', 'deu'): _create_uniform_task_map( 3,  6, REDUNDANCY),
    ('eng', 'spa'): _create_uniform_task_map(14, 28, REDUNDANCY),
    ('eng', 'fra'): _create_uniform_task_map(16, 32, REDUNDANCY),
    ('eng', 'hin'): _create_uniform_task_map(20, 40, REDUNDANCY),
    ('eng', 'ita'): _create_uniform_task_map(14, 28, REDUNDANCY),
    ('eng', 'jpn'): _create_uniform_task_map(12, 24, REDUNDANCY),
    ('eng', 'por'): _create_uniform_task_map(20, 40, REDUNDANCY),
    ('eng', 'rus'): _create_uniform_task_map(19, 38, REDUNDANCY),
}

CONTEXT = {
    'ANNOTATORS': ANNOTATORS,
    'CAMPAIGN_KEY': CAMPAIGN_KEY,
    'CAMPAIGN_NAME': CAMPAIGN_NAME,
    'CAMPAIGN_NO': CAMPAIGN_NO,
    'CAMPAIGN_URL': CAMPAIGN_URL,
    'REDUNDANCY': REDUNDANCY,
    'TASKS': TASKS,
    'TASKS_TO_ANNOTATORS': TASKS_TO_ANNOTATORS,
}

# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'Initialises campaign FY20 #2'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-output',
            type=str,
            default=None,
            metavar='--csv',
            help='Path used to create CSV file containing credentials.',
        )

    def handle(self, *args, **options):
        csv_output = options['csv_output']
        self.stdout.write('CSV output path: {0!r}'.format(csv_output))
        if csv_output and not csv_output.lower().endswith('.csv'):
            raise CommandError(
                'csv_output {0!r} does not point to .csv file'.format(
                    csv_output
                )
            )

        # Find super user
        superusers = _identify_super_users()
        self.stdout.write(
            'Identified superuser: {0}'.format(superusers[0])
        )

        # Compute list of all language pairs
        _all_languages = (
            [('eng', _tgt) for _tgt in EX_LANGUAGES]
            + [(_src, 'eng') for _src in XE_LANGUAGES]
            + [(_src, _tgt) for _src, _tgt in XY_LANGUAGES]
        )

        # Process Market and Metadata instances for all language pairs
        _process_market_and_metadata(
            _all_languages,
            superusers[0],
            domain_name='AppenFY20',
            corpus_name='AppenFY20',
        )
        self.stdout.write('Processed Market/Metadata instances')

        # Create User accounts for all language pairs. We collect the
        # resulting user credentials for later print out/CSV export.
        credentials = _process_users(_all_languages, CONTEXT)
        self.stdout.write('Processed User instances')

        # Print credentials to screen.
        for username, secret in credentials.items():
            print(username, secret)

        # Write credentials to CSV file if specified.
        if csv_output:
            csv_lines = [','.join(('Username', 'Password', 'URL')) + '\n']
            for _user, _password in credentials.items():
                _url = '{0}{1}/{2}/'.format(CAMPAIGN_URL, _user, _password)
                csv_lines.append(','.join((_user, _password, _url)) + '\n')
            with open(csv_output, mode='w') as out_file:
                out_file.writelines(csv_lines)

        # Add User instances as CampaignTeam members
        _process_campaign_teams(_all_languages, superusers[0], CONTEXT)
        self.stdout.write('Processed CampaignTeam members')

        # Process TaskAgenda instances for current campaign
        _process_campaign_agendas(credentials.keys(), CONTEXT)
