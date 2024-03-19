# Installation Instructions (API)

First, install the package using: 

`pip3 install git+https://github.com/antoineeripret/gsc_wrapper`

## Quickstart 

### OAuth

Follow these steps: 
- Create a new project in the [Google Developers Console](https://console.developers.google.com),
- Enable the  Google Search Console API under "APIs & Services". 
- Create an "Oauth consent screen" (External). The app name doesn't really matter. 
- Add the **webmasters.readonly** scope 
- Add your e-mail(s) to the test users. 
- Next, create credentials under "Credentials" (Oauth client ID)
- Choose "Desktop app" for the "Application type". Again, the name doesn't matter. 
- Download the JSON file and save it in your working directory 

If you want more detail about this process, have a look at [this video](https://www.youtube.com/watch?v=ptWJkrd0vqc&t=1882s) (from 12:00 to 27:00). 

After that, executing your first query is as easy as using the following code snippet: 

```python
import gscwrapper
#authentificate 
account = gscwrapper.generate_auth(
    'config/client_secret_mvp.json', 
    serialize='config/credentials.json'
)
#we choose the website we want 
webproperty = account['https://www.exemple.com/']
report = (
    webproperty
    #we call the query method 
    .query
    #we define the dates 
    .range(start="2023-01-01", stop="2023-02-01")
    #we define the dimensions 
    .dimensions(['page'])
    #we get the data 
    .get()
)
```

The above example will use your client configuration file to interactively generate your credentials. You'll then be able to call any available method on the returned object containing your GSC data. 

If you're unsure what webproperties are linked to your account, you can run the following code, which will return a DataFrame with your webproperties and their permission levels. 

```python 

account.list_webproperties()
```

The first time you run this code, you'll be asked to visit an URL: 

- Copy and paste it in your browser 
- Select the e-mail adress you've added as a test user in a previous step 
- Click on "Continue" 
- Click on "Continue" again 
- Copy the authorization code and paste it in the input box that will have appeared in your terminal / notebook from where you run the code 


#### Saving credentials 

If you wish to save your credentials, to avoid going
through the OAuth consent screen in the future, you can specify a path to save
them by specifying `serialize='path/to/credentials.json`.

When you want to authenticate a new account you run:

```python
account = gscwrapper.generate_auth(
    'config/client_secret_mvp.json', 
    serialize='config/credentials.json'
)
```
Which will save your credentials to a file called `credentials.json`.

From then on, you can authenticate with:

```python
account = gscwrapper.generate_auth(
    'config/client_secret_mvp.json', 
    credentials='config/credentials.json'
)
```

### Service Account

If you prefer to use a service account key, the process is easier and you just have to run the following code. **No need to save the credentials in that case**.  

```python 

account = (
    gscwrapper
    .generate_auth(
        client_config="service_account.json", 
        service_account_auth=True
    )
)

```

The service account obviously **need to be added to the GSC property first**. 

## Querying 

To query data from the search analytics, you can filter the data you retrieve based on: 

* **range**: Unlike [Josh's library](https://github.com/joshcarty/google-searchconsole), you need to explicitely define the dates (YYYY-MM-DD format). 

```python 
report = (
    webproperty
    .query
    .range(start="2023-01-01", stop="2023-02-01")
    .dimensions(["date"])
    .get()
)
```
* **dimensions**: dimensions need to be passed as a list. **You cannot get data without specifying at least one dimension**. 

```python 
report = (
    webproperty
    .query
    .range(start="2023-01-01", stop="2023-02-01")
    .dimensions(["date"])
    .get()
)
```

Please be aware that you may be affected by [data sampling](https://www.aeripret.com/gsc-data/) based on the number of dimensions you need. I strongly advise to include only the dimensions you need, otherwise the data extraction may take more time than needed. 

* **filter**: you can decide to analyse just a part of your website. You can filter using any dimension or operator included below: 

```python
DIMENSIONS = ['country','device','page','query','searchAppearance','date']
OPERATORS = ['equals','notEquals','contains','notContains','includingRegex','excludingRegex']
```

If you use a REGEX, I strongly advise to test it using the GSC UI first, because some characters are not suppoorted. 

**IMPORTANT**: you can filter on a dimension that is not included in your report. 

```python 
report = (
    webproperty
    .query
    .range(start="2023-01-01", stop="2023-02-01")
    .filter("page", "blog", "contains")
    .dimensions(["date"])
    .get()
)
```

* **search_type**: we often use the `web` search type, but [others are available](https://developers.google.com/webmaster-tools/v1/searchanalytics/query?hl=en#type). 

```python 
report = (
    webproperty
    .query
    .range(start="2023-01-01", stop="2023-02-01")
    .filter("page", "blog", "contains")
    .dimensions(["date"])
    .search_type('discover')
    .get()
)
```

* **limit**: by default, the library will fetch the API and try to retrieve all the data available. You can decide to retrieve a specific number of results using this method. 

```python 
report = (
    webproperty
    .query
    .range(start="2023-01-01", stop="2023-02-01")
    .filter("page", "blog", "contains")
    .dimensions(["date"])
    .limit(50)
    .get()
)
```
When you run any of these code snippets, you'll generate a `Report` object. For more on that, please refer to the following documentation: [List of methods](./README-METHODS.md). 


## Sitemaps 

You can also query the [Sitemaps](https://developers.google.com/webmaster-tools/v1/sitemaps?hl=en) by creating a `Sitemap` object. 


```python
import gscwrapper

#authentificate 
account = gscwrapper.generate_auth(
    'config/client_secret_mvp.json', 
    serialize='config/credentials.json'
)

#we choose the website we want 
webproperty = account['https://www.exemple.com/']
#we create the sitemap obkect 
sitemap = (webproperty.sitemap)

```

### list_sitemaps()

We can easily list the sitemaps that are included in GSC: 

```python 

(
    sitemap
    .list_sitemaps()
)

```

This would return a DataFrame similar to the following one: 


|path|lastSubmitted|isPending|isSitemapsIndex|lastDownloaded|warnings|errors|contents|type|
|:----|:----|:----|:----|:----|:----|:----|:----|:----|
|https://www.website.com/sitemap_index.xml|2023-12-23T23:41:05.453Z|False|True|2024-01-09T15:07:27.851Z|0|0|[{'type': 'web', 'submitted': '475', 'indexed': '0'}, {'type': 'image', 'submitted': '457', 'indexed': '0'}]| |
|https:///www.website.com/page-sitemap.xml|2019-10-15T15:44:16.831Z|False|False|2024-01-04T09:48:28.500Z|3|0|[{'type': 'web', 'submitted': '14', 'indexed': '0'}]|sitemap|


### check_sitemaps() 

This method will check if the sitemaps we have in GSC are all returning a 200 response code. **If you have a heavy IT policty in place, please note that the response code this method gets and the one Google would get may be different**. 

```python 

(
    sitemap
    .check_sitemaps()
)
```

|path|response_code|
|:----|:----|
|https://www.website.com/sitemap_index.xml|200|
|https://www.website.com/page-sitemap.xml|200|


## URL Inspection 

You can also query the [URL Inspection](https://developers.google.com/webmaster-tools/v1/urlInspection.index/urlInspection.index?hl=en) by creating a `Inspect` object. 

```python 

import gscwrapper

#authentificate 
account = gscwrapper.generate_auth(
    'config/client_secret_mvp.json', 
    serialize='config/credentials.json'
)

#we choose the website we want 
webproperty = account['https://www.exemple.com/']
#we create the sitemap obkect 
inspect = (webproperty.inspect)

```

### add_urls()

This method allows you to add URLs in the `Inspect` object. These URLs are the one you'll send to the API in the `execute()` call to get the data for. 

```python 

(
 inspect
 .add_urls([
     'https://www.website.com/page',
     'https://www.website.com/other-page'
     ]
    )
)

```

### remove_urls()

Same logic but to remove URLs from the `Inspect` object. 

### execute() 

THis will call the API for every **unique** URLs you added using the `add_urls()` method. Based on the number you have, the extraction can take a moment. 

```python 

(
    inspect 
    .execute()
)

```

If for whatever reason the execution fails during the process, you can retrieve the results that have already been generated by inspecting `inspect.results`. 
