# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Invokes Cloud Dataflow to perform language processing on Wikipedia."""

import argparse
import re
import textwrap

from nl_api import xml2entities


BIGQUERY_TABLE_FORMAT = re.compile(r'([\w.:-]+:)?\w+\.\w+$')


def bq_table_format_validator(bigquery_table):
    if not BIGQUERY_TABLE_FORMAT.match(bigquery_table):
        raise argparse.ArgumentTypeError(
            'bq_table must be of format (PROJECT:)DATASET.TABLE')
    return bigquery_table


def gcs_uri(src):
    if not src.startswith('gs://'):
        raise argparse.ArgumentTypeError(
            'Must be of the form gs://bucket/object/path')
    return src


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('src', type=gcs_uri)
    parser.add_argument('dest')
    parser.add_argument(
        '--end', type=int, default=None, help=textwrap.dedent('''
        If specified, execute a partial pipeline up to, but not including,
        this step (0-indexed). In this case, the `dest` argument should be
        the gs:// path prefix the results should be output to.'''))
    parser.add_argument(
        '--start', type=int, default=None, help=textwrap.dedent('''
        If specified, execute a partial pipeline beginning at this step
        (0-indexed). In this case, the `src` argument is assumed to be a
        gs:// glob pattern referencing the results of an earlier invocation
        that had specified an `--end`.'''))

    args, pipeline_args = parser.parse_known_args()
    try:
        dest = gcs_uri(args.dest)
    except argparse.ArgumentTypeError:
        dest = bq_table_format_validator(args.dest)

    xml2entities.main(
        args.src, args.dest,
        start=args.start, end=args.end,
        pipeline_args=pipeline_args)
