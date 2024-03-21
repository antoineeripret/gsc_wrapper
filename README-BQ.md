# Installation Instructions (BQ)

First, install the package using: 

`pip3 install git+https://github.com/antoineeripret/gsc_wrapper`

## Quickstart 

Since March 2023, [GSC data can be exportd in bulk](https://support.google.com/webmasters/answer/12918484?hl=en) to BigQuery. While the API access id free and enough in most cases, you may want to activate this export if you want to get access to all your data. 

You need to create a service account key with **enough rights to read your data and create jobs**. Once it's done, donwload the service account key and run the following code: 

```python 

import gscwrapper

#create the connection with BQ 
conn = (
    gscwrapper
    .generate_auth(
        client_config="/service_account.json",
        bigquery=True,
        #replace value with your project ID and your dataset name where GSC data are available 
        bigquery_dataset="project_id.dataset"
    )   
)

```

## Querying 

While the design is very similar to what you have for the [API](./README-API.md), please note that **some methods are not available**. Be sure to (slightly) update your code if you switch from an API integration to a BQ integration. 

Why is the integration diffrenet? Because for the API, **we first download the data and then apply some transformations while for BQ transformations are done directly in SQL**. 

To query data from your dataset, you can filter the data you retrieve based on: 

* **range**: Unlike [Josh's library](https://github.com/joshcarty/google-searchconsole), you need to explicitely define the dates (YYYY-MM-DD format). 

```python 
report = (
    conn
    .query
    .range(start="2023-01-01", stop="2023-02-01")
    .get()
)
```

* **filter**: you can decide to analyse just a part of your website. You can filter using any operator included below: 

```python
OPERATORS = ['equals','notEquals','contains','notContains','includingRegex','excludingRegex']
```

**IMPORTANT**: 
- please note that the `page` dimension in the API is called `url` in BigQuery !! 
- Although doable in SQL, I decided to keep behavior similar between the API and BQ, hence filters are merged with AND because the API doesn't allow OR. 

```python 
report = (
    conn
    .query
    .range(start="2023-01-01", stop="2023-02-01")
    .filter("url", "blog", "contains")
    .get()
)
```

When you run any of these code snippets, and despite the `get()` name (used to ensure compatibility with the API side of this library), no data will be actually fetched. You need to use at least one the [available methods](./README-METHODS.md) to actually get data. 