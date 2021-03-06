# cloudwatch_importer
Metrics importer for Amazon AWS CloudWatch from Prometheus

## Quick Start
1. Clone `git clone https://github.com/tivaliy/cloudwatch_importer.git`
2. Create isolated Python environment `virtualenv cw_importer_venv` and activate it `source cw_importer_venv/bin/activate`
3. Install all necessary dependencies: `pip install -r requirements.txt`
4. Configure `config.yaml` to meet your requirements. Specify metrics you want to import to Amazon AWS CloudWatch (`metrics`) from Prometheus:

    ```yaml
       url: http://localhost:9090/
       aws-region: eu-central-1
       namespace: TestNamespace
       metrics:
         - go_memstats_alloc_bytes_total
         - go_goroutines
         - go_memstats_last_gc_time_seconds
    ```
5. Make sure that your `~/.aws/credentials` file is configured properly (or see for more details the ways of how [Configuring Credentials](https://boto3.readthedocs.io/en/latest/guide/configuration.html#configuring-credentials))
6. Run python `import_metrics.py` script (e.g. `python import_metrics.py -c config.yaml`)
