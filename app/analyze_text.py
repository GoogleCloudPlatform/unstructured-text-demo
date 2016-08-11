# Copyright 2016 Google, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Analyzes text using the Google Cloud Text API.

Adapted from:

https://github.com/GoogleCloudPlatform/python-docs-samples/\
    blob/master/language/api/analyze.py
"""

from googleapiclient import discovery
import httplib2
from oauth2client.client import GoogleCredentials


def get_service():
    credentials = GoogleCredentials.get_application_default().create_scoped([
        'https://www.googleapis.com/auth/cloud-platform'])
    http = httplib2.Http(timeout=60)
    credentials.authorize(http)
    return discovery.build('language', 'v1beta1', http=http)


def annotate_text(text, encoding='UTF32',
                  extract_syntax=False, extract_entities=False,
                  extract_document_sentiment=False):
    body = {
        'document': {
            'type': 'PLAIN_TEXT',
            'content': text,
        },
        'features': {
            'extract_syntax': extract_syntax,
            'extract_entities': extract_entities,
            'extract_document_sentiment': extract_document_sentiment,
        },
        'encoding_type': encoding,
    }

    service = get_service()

    request = service.documents().annotateText(body=body)
    response = request.execute()

    return response
