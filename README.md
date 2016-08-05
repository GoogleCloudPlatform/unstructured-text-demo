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

## Setup

* For `tools/`:
  * Install the [gcloud][gcloud] command-line tool.
  * You'll first download the [Wikipedia dump][wp-xml] of your choice. You might
    have to unzip it (I did, but Dataflow might be able to handle the zipped
    version as well).
  * Create a [Google Cloud Storage][gcs] bucket, and upload the file using
    either the [web UI][gcs-web] or [gsutil][gsutil]:

      $ gsutil cp <wikipedia-dump.xml> gs://<your-bucket>/

  * [Create a BigQuery dataset][create-bq] that will contain destination table.
  * Install the prerequisites for the script in a [virtualenv][venv]:

      $ cd tools/
      $ virtualenv v
      $ source v/bin/activate
      $ pip install -r requirements.txt

* For `app/`:
  * Install the [AppEngine Python SDK][gae-python-sdk]
  * Download a [service account key][service-account] and set the
    `GOOGLE_APPLICATION_CREDENTIALS` environment variable, as [detailed
    here][adc].

[gcloud]: https://cloud.google.com/sdk/gcloud/
[gcs]: https://cloud.google.com/storage
[gcs-web]: https://console.cloud.google.com/storage/browser?project=_
[gsutil]: https://cloud.google.com/storage/docs/gsutil
[gae-python-sdk]: https://cloud.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python
[create-bq]: https://cloud.google.com/bigquery/quickstart-web-ui#create_a_dataset
[venv]: https://virtualenv.pypa.io/en/stable/
[service-account]: https://console.cloud.google.com/iam-admin/serviceaccounts/project?project=_
[adc]: https://cloud.google.com/docs/authentication#service_running_on-premises

## Running

* For `tools/`, an example invocation:

    $ python main.py gs://<your-bucket>/<your-wikipedia-dump.xml> \
        <your-project-id>:<your-dataset-name>.<your-table-name> \
        --job_name '<pick-a-job-name>' --project '<your-project-id>' \
        --runner 'BlockingDataflowPipelineRunner' \
        --staging_location gs://<your-bucket>/staging \
        --temp_location gs://<your-bucket>/temp \
        --setup_file $PWD/setup.py \
        --autoscaling_algorithm=THROUGHPUT_BASED \
        --disk_size_gb=10
~

* For `app/`:
  * Run the local test server:

      $ cd app/
      $ dev_appserver.py .

  * Visit the site at [http://localhost:8080/](http://localhost:8080)

## Disclaimer

This is not an official Google product.
