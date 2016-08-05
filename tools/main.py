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
import argparse
import re

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
    parser = argparse.ArgumentParser()
    parser.add_argument('src', type=gcs_uri)
    parser.add_argument('dest')

    args, pipeline_args = parser.parse_known_args()
    try:
        dest = bq_table_format_validator(args.dest)
    except argparse.ArgumentTypeError:
        dest = gcs_uri(args.dest)

    xml2entities.main(args.src, args.dest, pipeline_args)
