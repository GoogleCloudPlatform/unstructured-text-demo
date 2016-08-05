# Copyright 2015, Google, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Command-line application to perform an asynchronous query in BigQuery.

This sample is used on this page:

    https://cloud.google.com/bigquery/querying-data#asyncqueries

For more information, see the README.md under /bigquery.
"""

import time
import uuid

from googleapiclient import discovery
from oauth2client.client import GoogleCredentials


# [START async_query]
def async_query(project_id, query, batch=False, num_retries=5):
    # Grab the application's default credentials from the environment.
    credentials = GoogleCredentials.get_application_default()

    # Construct the service object for interacting with the BigQuery API.
    bigquery = discovery.build('bigquery', 'v2', credentials=credentials)

    # Generate a unique job_id so retries
    # don't accidentally duplicate query
    job_data = {
        'jobReference': {
            'projectId': project_id,
            'job_id': str(uuid.uuid4())
        },
        'configuration': {
            'query': {
                'query': query,
                'priority': 'BATCH' if batch else 'INTERACTIVE'
            }
        }
    }
    return bigquery.jobs().insert(
        projectId=project_id,
        body=job_data).execute(num_retries=num_retries)
# [END async_query]


# [START poll_job]
def poll_job(job):
    """Waits for a job to complete."""
    # Grab the application's default credentials from the environment.
    credentials = GoogleCredentials.get_application_default()

    # Construct the service object for interacting with the BigQuery API.
    bigquery = discovery.build('bigquery', 'v2', credentials=credentials)

    print('Waiting for job to finish...')

    request = bigquery.jobs().get(
        projectId=job['jobReference']['projectId'],
        jobId=job['jobReference']['jobId'])

    while True:
        result = request.execute(num_retries=2)

        if result['status']['state'] == 'DONE':
            if 'errorResult' in result['status']:
                raise RuntimeError(result['status']['errorResult'])
            print('Job complete.')
            return

        time.sleep(1)
# [END poll_job]


def get_results(query_job):
    # Grab the application's default credentials from the environment.
    credentials = GoogleCredentials.get_application_default()

    # Construct the service object for interacting with the BigQuery API.
    bigquery = discovery.build('bigquery', 'v2', credentials=credentials)

    # Page through the result set and print all results.
    page_token = None
    results = []
    while True:
        page = bigquery.jobs().getQueryResults(
            pageToken=page_token,
            **query_job['jobReference']).execute(num_retries=2)

        if int(page['totalRows']):
            results.extend(page['rows'])

        page_token = page.get('pageToken')
        if not page_token:
            break

    return results
