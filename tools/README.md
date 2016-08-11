# Wikipedia dump to BigQuery preprocessing pipeline

This tool creates a pipeline that:

* Reads in a [Wikipedia XML dump][wp-xml]
* Filters out Wikipedia meta pages
* Parses out the text for each article
* Uses the [Google Cloud Natural Language API][cloud-nl] to extract the entities
  present and the sentiment from each article
* Inserts the entities into a [BigQuery][bq] table.

[wp-xml]: https://en.wikipedia.org/wiki/Wikipedia:Database_download#English-language_Wikipedia
[cloud-nl]: https://cloud.google.com/natural-language/
[bq]: https://cloud.google.com/bigquery/

## Prerequisites

* Set up a project on the [Google Cloud Console][cloud-console]
* Install the [gcloud][gcloud] command-line tool.
* You'll first download the [Wikipedia dump][wp-xml] of your choice. You might
  have to unzip it (I did, but Dataflow might be able to handle the zipped
  version as well).
* Create a [Google Cloud Storage][gcs] bucket, and upload the file using
  either the [web UI][gcs-web] or [gsutil][gsutil]:

    $ gsutil cp [wikipedia-dump.xml] gs://[your-bucket]/

* [Create a BigQuery dataset][create-bq] that will contain destination table.
* Define some environment variables (which will be referenced below):

      MY_PROJECT=[your-project-name]
      MY_BUCKET=[your-bucket]
      GCS_PATH_TO_XML=gs://$MY_BUCKET/[path/to/wikipedia.xml]
      BIGQUERY_DESTINATION_TABLE="$MY_PROJECT:[your-dataset].[table-name]"

[cloud-console]: https://console.cloud.google.com
[gcloud]: https://cloud.google.com/sdk/gcloud/
[gcs]: https://cloud.google.com/storage/
[gcs-web]: https://console.cloud.google.com/storage/browser?project=_
[gsutil]: https://cloud.google.com/storage/docs/gsutil
[create-bq]: https://cloud.google.com/bigquery/quickstart-web-ui#create_a_dataset

## Setup

* Install the prerequisites for the script in a [virtualenv][venv]:

    $ cd tools/
    $ virtualenv v
    $ source v/bin/activate
    $ pip install -r requirements.txt

* You can run the entire pipeline at once:

    python main.py "$GCS_PATH_TO_XML" "$BIGQUERY_DESTINATION_TABLE" \
        --job_name 'wikipedia-ingestion' --project "$MY_PROJECT" \
        --runner 'BlockingDataflowPipelineRunner' \
        --staging_location "gs://$MY_BUCKET/staging" \
        --temp_location "gs://$MY_BUCKET/temp" \
        --setup_file $PWD/setup.py \
        --autoscaling_algorithm=THROUGHPUT_BASED \
        # Limit disk size to avoid going over disk quota as the job scales up
        --disk_size_gb=10

* Or you can run it in pieces (for example, so that if there's an error, you
  don't have to start again from the beginning):

  * Run the first part of the pipeline, before the entity extraction step. Note
    that the steps are 0-indexed (ie the first step is step 0), and the pipeline
    includes all the steps up to, but not including, the `--end` step.

      python main.py "$GCS_PATH_TO_XML" "gs://$MY_BUCKET/articles.json" \
          --end 5 \
          --job_name 'wikipedia-ingestion-1' --project "$MY_PROJECT" \
          --runner 'BlockingDataflowPipelineRunner' \
          --staging_location "gs://$MY_BUCKET/staging \
          --temp_location "gs://$MY_BUCKET/temp" \
          --setup_file $PWD/setup.py \
          --autoscaling_algorithm=THROUGHPUT_BASED \
          --disk_size_gb=10

  * Wait while Dataflow parses Wikipedia's XML, markdown, and HTML; filters out
    redirects and metapages; converts to JSON; and saves to intermediate Cloud
    Storage objects.

  * Perform the entity extraction, picking up where the last step left off, and
    save the results into BigQuery. Note that the steps are 0-indexed, and the
    pipeline includes all the steps starting from, and including, the `--start`
    step.

      python main.py "$GCS_PATH_TO_XML" "gs://$MY_BUCKET/articles.json*" \
          --start 5 \
          --job_name 'wikipedia-ingestion-1' --project "$MY_PROJECT" \
          --runner 'BlockingDataflowPipelineRunner' \
          --staging_location "gs://$MY_BUCKET/staging \
          --temp_location "gs://$MY_BUCKET/temp" \
          --setup_file $PWD/setup.py \
          --autoscaling_algorithm=THROUGHPUT_BASED \
          --disk_size_gb=10

[venv]: https://virtualenv.pypa.io/en/stable/
