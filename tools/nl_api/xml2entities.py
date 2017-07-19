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

"""Parses all articles in a Wikipedia XML dump for entities and sentiment."""

import json
import logging
import re

import apache_beam
import apache_beam.io
from apache_beam.transforms import core
from apache_beam.transforms import window
from apache_beam.utils.windowed_value import WindowedValue

import custom_sources
import language
from lxml import etree
from lxml import html
import mwparserfromhell


# https://en.wikipedia.org/wiki/Wikipedia:Namespace
WIKIPEDIA_NAMESPACES = re.compile(
    r'(User( talk)?|Wikipedia( talk)?|Project( talk)?|File( talk)?|'
    r'Image( talk)?|MediaWiki( talk)?|Special|Template( talk)?|Help( talk)?|'
    r'Category( talk)?|Portal( talk)?|Book( talk)?|Draft( talk)?|'
    r'Education Program( talk)?|TimedText( talk)?|Module( talk)?|Topic|'
    r'Gadget( talk)?|Gadget definition( talk)?|Talk|Media|'
    r'WP|WT|CAT|H|MOS|P|T):', re.I)


def _to_unicode(text):
    if isinstance(text, str):
        text = text.decode('utf8')
    elif isinstance(text, unicode):
        text = unicode(text)
    else:
        try:
            text = unicode(text)
        except UnicodeDecodeError:
            text = str(text).decode('utf8')
    return text


def html_to_text(content):
    """Filter out HTML from the text."""
    text = content['text']

    try:
        text = html.document_fromstring(text).text_content()
    except etree.Error as e:
        logging.error(
            'Syntax error while processing {}: {}\n\n'
            'Falling back to regexes'.format(text, e))
        text = re.sub(r'<[^>]*>', '', text)

    text = _to_unicode(text)

    content['text'] = text
    return content


def parse_xml(xml):
    page = etree.fromstring(xml)
    children = dict((el.tag, el) for el in page)

    if 'redirect' in children:
        raise StopIteration()

    if WIKIPEDIA_NAMESPACES.match(children['title'].text):
        raise StopIteration()

    if 'id' in children:
        # Can't yield the page directly, because it's not picklable
        revisions = (rev.text for rev in children['revision'].iter('text'))
        yield {
            'article_id': children['id'].text,
            'article_title': children['title'].text,
            'wikitext': revisions.next(),
        }


def _strip_code(parsed_md):
    """A modification of mwparserfromhell's .strip_code() method.

    Removes unprintable code from the mediawiki markdown, such as templates.

    I was running into some unicode errors with mwparserfromhell's
    .strip_code() method, so hack around that here.
    """
    return (u' '.join((unicode(n.__strip__(True, True)) or '')
                      for n in parsed_md.nodes)).strip()


def parse_wikitext(content):
    text = content['wikitext']

    try:
        parsed_md = mwparserfromhell.parse(content['wikitext'])
        parsed_md = _strip_code(parsed_md)
        if not parsed_md:
            raise StopIteration()
    except mwparserfromhell.parser.ParserError:
        # Bah. We made an effort. Stupid markdown. Just let it through
        parsed_md = text

    content['text'] = parsed_md
    del content['wikitext']
    yield content


def force_string_function(key):
    """Returns a function that forces the value at the key to a string."""
    def force_string(d):
        if isinstance(d[key], unicode):
            d[key] = d[key].encode('utf8')
        return d
    return force_string


def analyze_entities(content):
    """Emits metadata for each entity in the content.

    This includes the entity name, type, salience, as well as the article
    sentiment, and the existing article metadata.
    """
    if not content:
        raise StopIteration()

    analysis = language.annotate_text(
        content['text'], extract_entities=True,
        extract_document_sentiment=True)
    if not analysis:
        logging.error('Falsey analysis for article (%s) %s',
                      content['article_id'], content['article_title'])
        raise StopIteration()

    sentiment = analysis.get('documentSentiment', {})
    for entity in analysis.get('entities', []):
        entity_dict = {
            'article_id': content['article_id'],
            'article_title': content['article_title'],
            'article_sentiment_polarity': sentiment.get('polarity'),
            'article_sentiment_magnitude': sentiment.get('magnitude'),
            'entity_name': entity['name'],
            'entity_type': entity['type'],
            'entity_wikipedia_url': entity.get('metadata', {}).get(
                'wikipedia_url', ''),
            'entity_salience': entity.get('salience'),
            'entity_num_mentions': len(entity.get('mentions', [])),
        }
        yield entity_dict


def analyze_entities_batch(content_list):
    """Like analyze_entities, but performs the API call in a batch.

    Note that, like analyze_entities, it still emits each entity individually.
    """
    if not content_list:
        raise StopIteration()

    analyses = language.annotate_text_batch(
        [content['text'] for content in content_list],
        extract_entities=True, extract_document_sentiment=True)

    for content, analysis in zip(content_list, analyses):
        if not analysis:
            logging.error('Falsey analysis for article (%s) %s',
                          content['article_id'], content['article_title'])
            continue

        sentiment = analysis.get('documentSentiment', {})
        for entity in analysis.get('entities', []):
            entity_dict = {
                'article_id': content['article_id'],
                'article_title': content['article_title'],
                'article_sentiment_polarity': sentiment.get('polarity'),
                'article_sentiment_magnitude': sentiment.get('magnitude'),
                'entity_name': entity['name'],
                'entity_type': entity['type'],
                'entity_wikipedia_url': entity.get('metadata', {}).get(
                    'wikipedia_url', ''),
                'entity_salience': entity.get('salience'),
                'entity_num_mentions': len(entity.get('mentions', [])),
            }
            yield entity_dict


class BatchFn(core.DoFn):
    """Collects a list of entities, and emits them as batches."""
    def __init__(self, batch_size, *args, **kwargs):
        self._batch_size = batch_size

    def start_bundle(self):
        self._batch = []

    def process(self, element, *args, **kwargs):
        self._batch.append(element)
        if len(self._batch) >= self._batch_size:
            batch = self._batch
            self._batch = []
            yield batch

    def finish_bundle(self, *args, **kwargs):
        if self._batch:
            yield WindowedValue(self._batch, -1, [window.GlobalWindow()])


def main(gcs_path, out, start=None, end=None, pipeline_args=None):
    steps = [
        'Parse XML and filter' >> apache_beam.FlatMap(parse_xml),
        'Coerce "wikitext" key to string type' >> apache_beam.Map(
                force_string_function('wikitext')),
        'Parse markdown into plaintext' >> apache_beam.FlatMap(parse_wikitext),
        'Coerce "text" key to string type' >> apache_beam.Map(
                force_string_function('text')),
        'Filter out any vestigial HTML' >> apache_beam.Map(html_to_text),
        'batch' >> core.ParDo(BatchFn(10)),
        'Entities (batch)' >> apache_beam.FlatMap(analyze_entities_batch)
    ]

    p = apache_beam.Pipeline(argv=pipeline_args)

    if start:
        value = p | 'Pick up at step {}'.format(start) >> apache_beam.io.Read(
                apache_beam.io.TextFileSource(gcs_path)) | \
            'Parse JSON' >> apache_beam.Map(json.loads)
    else:
        value = p | 'Read XML' >> apache_beam.io.Read(
                custom_sources.XmlFileSource('page', gcs_path))

    for step in steps[start:end]:
        value = value | step

    if end:
        if not out.startswith('gs://'):
            raise ValueError('Output must be GCS path if an end is specified.')
        value = value | 'to JSON' >> apache_beam.Map(json.dumps) | \
            'Dump to GCS' >> apache_beam.io.Write(
                    apache_beam.io.WriteToText(out))
    else:
        value = value | 'Dump metadata to BigQuery' >> apache_beam.io.Write(
            apache_beam.io.BigQuerySink(
                out,
                schema=', '.join([
                    'article_id:STRING',
                    'article_title:STRING',
                    'article_sentiment_polarity:FLOAT',
                    'article_sentiment_magnitude:FLOAT',
                    'entity_name:STRING',
                    'entity_type:STRING',
                    'entity_wikipedia_url:STRING',
                    'entity_salience:FLOAT',
                    'entity_num_mentions:INTEGER',
                ]),
                create_disposition=(
                    apache_beam.io.BigQueryDisposition.CREATE_IF_NEEDED),
                write_disposition=(
                    apache_beam.io.BigQueryDisposition.WRITE_APPEND)))

    p.run()
