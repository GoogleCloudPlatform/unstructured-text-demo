# Wikipedia and the Google Cloud Natural Language API

This demo contains code to detect entities and sentiment of a dump of Wikipedia,
as well as a webapp that queries the resultant BigQuery table.

## Introduction

This demo is split up into two parts:

* The `tools` directory contains a [Google Cloud Dataflow][dataflow] pipeline
  that starts from a [Wikipedia XML dump][wp-xml] and ends with a table in
  [Google BigQuery][bq] containing all detected entities in Wikipedia, by way of
  the [Google Cloud Natural Language API][nl-api].
* The `app` directory contains a [Google App Engine][gae] app that uses
  Wikipedia's [Mediawiki API][mw-api] to fetch a given Wikipedia page
  dynamically, and uses the [Natural Language API][nl-api] to highlight all the
  entities detected. It can also display a related-entities graph, by querying
  the BigQuery table created above.

[dataflow]: https://cloud.google.com/dataflow/
[wp-xml]: https://en.wikipedia.org/wiki/Wikipedia:Database_download#English-language_Wikipedia
[bq]: https://cloud.google.com/bigquery/
[nl-api]: https://cloud.google.com/natural-language/
[gae]: https://cloud.google.com/appengine/
[mw-api]: https://www.mediawiki.org/wiki/API:Main_page

## Prerequisites

* Set up a project in the [Google Cloud Console][cloud-console]
* Enable the [Natural Language API][nl-enable-api]

[cloud-console]: https://console.cloud.google.com
[nl-enable-api]: https://console.cloud.google.com/apis/api/language.googleapis.com/overview?project=_

## Setup

* For `tools/`, see [tools/README.md](tools/README.md)
* For `app/`:
  * Install the [AppEngine Python SDK][gae-python-sdk]
  * Download a [service account key][service-account] and set the
    `GOOGLE_APPLICATION_CREDENTIALS` environment variable, as [detailed
    here][adc].
  * Install the dependencies into a `lib/` directory:

      $ cd app/
      $ pip install -r requirements.txt -t lib/

[gae-python-sdk]: https://cloud.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python
[service-account]: https://console.cloud.google.com/iam-admin/serviceaccounts/project?project=_
[adc]: https://cloud.google.com/docs/authentication#service_running_on-premises

## Running

* For `tools/`, see [tools/README.md](tools/README.md)
* For `app/`:
  * Run the local test server:

      $ cd app/
      $ dev_appserver.py .

  * Visit the site at [http://localhost:8080/](http://localhost:8080)

## Disclaimer

This is not an official Google product.
