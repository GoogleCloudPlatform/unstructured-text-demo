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

"""Fetches data from Wikipedia."""

from lxml import html
import mwparserfromhell
import requests


WIKIPEDIA_BASE = 'https://en.wikipedia.org/w/api.php'
HEADERS = {
    'User-Agent': ('GCP-NL-Demo/0.1 (http://github.com/GoogleCloudPlatform'
                   '/python-docs-samples;)'),
}


def get_article(titles=None, pageids=None):
    """Uses the MediaWiki API to fetch Wikipedia pages."""
    headers = HEADERS
    params = {
        'action': 'query',
        'prop': 'revisions',
        'rvprop': 'content',
        'redirects': True,
        'format': 'json',
    }
    if titles:
        params['titles'] = titles
    if pageids:
        params['pageids'] = pageids

    r = requests.get(WIKIPEDIA_BASE, params=params, headers=headers)
    r.raise_for_status()
    content = r.json()
    return content


def get_article_content(title):
    """Gets the contents of the articles with the given title."""
    pages = get_article(title)['query']['pages']
    content = []
    for v in pages.itervalues():
        title = v['title']
        txt_content = mwparserfromhell.parse(
            # TODO: give it html
            v['revisions'][0]['*']).strip_code()
        tree = html.document_fromstring(txt_content)
        notags = html.tostring(tree, encoding='utf8', method='text')
        content.append((title, notags.decode('utf8')))

    return content
