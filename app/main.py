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
"""`main` is the top level module for your Flask application."""

from functools import wraps
import math
import pickle
import re
import zlib

import analyze_text
import bigquery
import wikipedia
from flask import Flask
from flask import jsonify
from flask import render_template
from flask import request
from google.appengine.api import app_identity
from requests_toolbelt.adapters import appengine
from werkzeug.contrib.cache import GAEMemcachedCache


appengine.monkeypatch()

app = Flask(__name__)


DATASET = 'nl_wikipedia'
TABLE = 'nl_wikipedia'
COMMON_ENTITIES_QUERY = '''
select top(entity_name, {limit}), count(*)
from [{dataset}.{table}]
where article_id in (
    SELECT article_id
    FROM [{dataset}.{table}]
    where {column} = '{value}')
and {column} != '{value}'
'''.strip()
PAGES_WITH_BOTH_QUERY = '''
select article_title, article_id
from [{dataset}.{table}]
where article_id in (
    SELECT article_id
    FROM [{dataset}.{table}]
    where {column} = '{value1}')
and entity_name == '{name2}'
'''.strip()
URL_REGEX = re.compile(r'^https?://(\w+\.?)+/[\w:@%_.~!?$&\'()*+,;=/-]+$')
NAME_REGEX = re.compile(r'^[\w \'.:-]+$')


cache = GAEMemcachedCache()


class ValidationError(Exception):
    pass


def cached(timeout=5 * 60, query_params=None):
    """Cache a request handler based on keys in the query string."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = request.path + '?' + (
                '|'.join(request.args.get(qp, qp) for qp in query_params)
                if query_params else request.query_string)
            rv = cache.get(cache_key)
            if rv is not None:
                return pickle.loads(zlib.decompress(rv))
            rv = f(*args, **kwargs)
            cache.set(
                cache_key, zlib.compress(pickle.dumps(rv)), timeout=timeout)
            return rv
        return decorated_function
    return decorator


@app.route('/')
@cached(query_params=['wiki_title'])
def index():
    wiki_title = request.args.get('wiki_title')
    context = {
        'log': math.log,
    }

    if wiki_title:
        context['wiki_title'] = wiki_title
        context['page_title'], page_content = (
            wikipedia.get_article_content(wiki_title))[0]

        analysis = analyze_text.annotate_text(
            page_content, encoding='UTF16',
            extract_entities=True, extract_document_sentiment=True)

        analysis.update({
            'content': page_content,
        })
        context['analysis'] = analysis

    return render_template('index.html', **context)


@app.route('/common_entities')
@cached(query_params=['wiki', 'limit'])
def common_entities():
    limit = min(int(request.args.get('limit', 10)), 50)
    wiki = request.args.get('wiki')
    if wiki:
        if not URL_REGEX.match(wiki):
            raise ValidationError('URL does not validate: {}'.format(wiki))
        column = 'entity_wikipedia_url'
        entity = wiki
    else:
        name = request.args.get('name')
        if not name or not NAME_REGEX.match(name):
            raise ValidationError('Name does not validate: {}'.format(name))
        column = 'entity_name'
        entity = name

    sanitized_entity = re.sub(r"'", "\\'", entity)

    job = bigquery.async_query(
        app_identity.get_application_id(),
        COMMON_ENTITIES_QUERY.format(
            limit=limit,
            dataset=DATASET, table=TABLE,
            column=column, value=sanitized_entity,
        ))
    bigquery.poll_job(job)
    rows = bigquery.get_results(job)

    return jsonify(rows=rows)


@app.route('/pages_with_both')
@cached(query_params=['wiki1', 'name1', 'name2', 'limit'])
def pages_with_both():
    """Returns the wikipedia pages that contain both the two given entities."""
    limit = min(int(request.args.get('limit', 10)), 100)
    wiki = request.args.get('wiki1')
    if wiki:
        if not URL_REGEX.match(wiki):
            raise ValidationError('URL does not validate: {}'.format(wiki))
        column = 'entity_wikipedia_url'
        entity = wiki
    else:
        name1 = request.args.get('name1')
        if not name1 or not NAME_REGEX.match(name1):
            raise ValidationError('Name does not validate: {}'.format(name1))
        column = 'entity_name'
        entity = re.sub(r'[^\w -]', '', name1)

    name2 = request.args.get('name2')

    sanitized_entity = re.sub(r"'", "''", entity)
    sanitized_name2 = re.sub(r"'", "''", name2)

    job = bigquery.async_query(
        app_identity.get_application_id(),
        PAGES_WITH_BOTH_QUERY.format(
            limit=limit,
            dataset=DATASET, table=TABLE,
            column=column, value1=sanitized_entity,
            name2=sanitized_name2,
        ))

    bigquery.poll_job(job)

    rows = bigquery.get_results(job)

    return jsonify(rows=rows)


@app.errorhandler(ValidationError)
def validation_error(e):
    return jsonify({'error': e.message}), 400


@app.errorhandler(404)
def page_not_found(e):
    return 'Page not found.', 404


@app.errorhandler(500)
def application_error(e):
    return jsonify({'error': 'Sorry, unexpected error: {}'.format(e)}), 500
