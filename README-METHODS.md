# Available Methods

I developped a couple of methods you can freely use based on your needs.

## Logic (API)


When you run the `.get()` method, a `Report` object is created. It contains all the data you downloaded from GSC based on your criteria. Based on the method you use, you'll need some dimensions in your report. For instance, you cannot call the `ctr_yield_curve()` method without the `date` and the `query` dimensions. 

If you are not using the API or BQ, you can load a `Report` object from any DataFrame using the following code: 

```python 

(
    gscwrapper
    .query
    .Report(
        #the dataframe where you have your data 
        x, 
        #the name of the webproperty 
        "https://www.website.com/",
        #min date 
        "2023-01-01",
        #max date 
        "2023-30-01"
)

```

You'll then be able to use any of the available methods. 

## Logic (BQ) 

For BigQuery, the logic is different. When you call a method, a SQL code is generated and sent to BQ through the [Pandas GBQ library](https://pandas-gbq.readthedocs.io/en/latest/). For any given method, two calls are done: 
- A first one (free) to check that the dates in your conditions are included in your dataset 
- A second one (cost can vary) to retrieve your data 

To avoid unexpected cost, by default a method will trigger a [dry run](https://cloud.google.com/bigquery/docs/samples/bigquery-query-dry-run) and returns the cost of the query. **This method assumes €5 per TB consumed, so adjust the price accordingly based on your local cost.**  

```python

(
    conn 
    .query 
    .range(
        start="2024-01-01",
        stop="2024-03-31"
    )
    .filter('url','blog','contains')
    .get()
    .group_data_by_period('W')
)

```

To actually run the code, you need to add the `define_estimate_cost(value=True)` before the method name. 

```python 
(
    conn 
    .query 
    .range(
        start="2024-01-01",
        stop="2024-03-31"
    )
    .filter('url','vol','contains')
    .get()
    .define_estimate_cost(value=True)
    .group_data_by_period('W')
)
```


## List of methods 

Most of them are available for both BQ and the API. Some of them just for the API (this is indicated in the documentation). 

- [show_data()](#show_data)
- [ctr_yield_curve()](#ctr_yield_curve)
- [active_pages()](#active_pages)
- [cannibalization()](#cannibalization)
- [forecast()](#forecast)
- [brand_vs_no_brand()](#brand_vs_no_brand)
- [keyword_gap()](#keyword_gap)
- [causal_impact()](#causal_impact)
- [update_urls()](#update_urls)
- [extract_search_volume()](#extract_search_volume)
- [find_potential_contents_to_kill()](#find_potential_contents_to_kill)
- [find_content_decay()](#find_content_decay)
- [winners_losers()](#winners_losers)
- [find_long_tail_keywords()](#find_long_tail_keywords)
- [find_ctr_outliers()](#find_ctr_outliers)
- [abcd()](#abcd)
- [pages_lifespan()](#pages_lifespan)
- [seasonality_per_day()](#seasonality_per_day)
- [replace_query_from_list()](#replace_query_from_list)

Please note that whil there are some checks done for the API methods, almost none are done for BQ because the SQL is generated by the library. A BQ method is not likely to fail, an API can if you don't include the required dimensions. 

#### show_data()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|None|None|pd.DataFrame|:white_check_mark:|


This method is pretty straight-forward. It returns your data as a Pandas DataFrame. Useful to check what the API has returned and perform ad-hoc analysis that are not covered by the other methods from this library. 

#### ctr_yield_curve()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|query / date|clicks / impressions / position |pd.DataFrame|:white_check_mark:|

You can call this method to build a [CTR yield curve](https://www.aeripret.com/ctr-yield-curve/) with your data. 

```python 

(
    report 
    .ctr_yield_curve()
)
```

For example, you could get this output. 

|position|ctr|clicks|impressions|kw_count|
|:----|:----|:----|:----|:----|
|1.0|19.02|807|4242|1516|
|2.0|11.66|476|4084|1026|
|3.0|15.1|340|2252|637|
|4.0|12.2|268|2196|730|
|5.0|7.16|126|1761|551|
|6.0|5.49|195|3552|909|
|7.0|3.66|107|2921|696|
|8.0|3.27|102|3124|930|
|9.0|2.17|67|3087|897|
|10.0|1.51|73|4841|1250|

### group_data_by_period()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|date|None |pd.DataFrame|:white_check_mark:|

We often need to compare weekly or monthly data, when GSC only provides daily data. Using this method, you can resample your data.  

Accepted periods are the following: 
* **D**: day 
* **W**: week 
* **M**: month 
* **Q**: quarter 
* **Y**: year 

```python 
report.group_data_by_period('W')
```

This will output a table where the main metrics (**clicks & impressions**) are grouped by the new period chosen. 

|date|clicks|impressions|
|:----|:----|:----|
|2023-01-01|206|8109|
|2023-01-08|1871|69275|
|2023-01-15|1998|67207|
|2023-01-22|1706|60436|
|2023-01-29|1980|67552|
|2023-02-05|935|29155|

#### active_pages() 

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|page|clicks / impressions |pd.DataFrame|:white_check_mark:|

We sometimes have to know the percentage of pages that are active from a list of URLs. This method allows you to compare the `page`you have in your GSC report to a list of URLs. 

You can either: 

* pass a manual list of URLs 
* provide a sitemap or sitemap index URL and the library will download all the URLs included there. 

```python 

(
    report
    .active_pages(
        sitemap_url = "https://www.website.com/sitemap_index.xml"
    )
)

```

The outcome: a table telling you which pages from your list are active (based on impressions or clicks). 

|page|clicks|impressions|active_impression|active_clicks|
|:----|:----|:----|:----|:----|
|https://www.website.com/blog/content_1|1.0|21.0|True|True|
|https://www.website.com/blog/content_2|0.0|78.0|True|False|
|https://www.website.com/blog/content_3|1.0|161.0|True|True|

#### cannibalization() 

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|query / page|clicks / impressions |pd.DataFrame|:white_check_mark:|

GSC can be a fabulous tool to find cannibalization at scale. The trick is to remove **false positives** and cases of **good cannibaliation**. This method can be used to find queries where: 

* we have more than one page ranking for a specific query 
* we have more than one page representing at least 10% of the clicks for a given query 
* this query represents at least 10% of the total clicks of the page 

This definition is subjective and you are free to have a look at the source code to create your own based on your projects. 

```python 

(
    report 
    .cannibalization(brand_variants=['brand','mybrand'])
)
```

**IMPORTANT**: **you need to provide the common branding structures as a list to remove these cases from the cannibalization analysis. Otherwise, you would end up with a lot of false positives on your branded terms**. 

This method would return the following table, with a selection of the pages that seem to suffer from cannibalization. You can then define what you want to do with them based on the SEO context. 

|page|query|clicks_query|impressions|click_pct|clicks_page|click_pct_page| |
|:----|:----|:----|:----|:----|:----|:----|:----|
|https://www.website.com/blog/content_1|xxxxx|11|385|57.89|44|25.00| |
|https://www.website.com/blog/content_2|xxxxx|8|191|42.10|23|34.78| |
|https://www.website.com/blog/content_1|yyyyy|15|387|62.50|44|34.09| |
|https://www.website.com/blog/content_2|yyyyy|9|148|37.50|23|39.13| |

#### forecast()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|date|clicks |pd.DataFrame|:white_check_mark:|

This method is used to forecast traffic, using [prophet](https://facebook.github.io/prophet/). Using the data available in our `Report`object, we can use this external library to forecast future clicks. 

The function is simple to use but please note that **I do not advise to create forecast if you don't have at least a decent number of days in your `Report` object**, otheriwse the forecast will be inaccurate. 

You can specify the number of days you want to forecast as the only accepted parameter for this method. 

```python 

(
    report 
    .forecast(days=10)
)
```

This method returns the DataFrame as created by Prophet, and if you want to understand the column names, have a look at [their documentation](https://facebook.github.io/prophet/). 

#### brand_vs_no_brand()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|query / date |None |pd.DataFrame|:white_check_mark:|

This method allows you to simply compare your branded and non-branded clicks / impressions over time.

```python 
(
    report 
    .brand_vs_no_brand(brand_variants=['brand', 'mybrand'])
)

```

It returns a clean table with your clicks & impressions over time that allows you to see how your traffic is evolving on branded and non-branded terms. 

|date|clicks_brand|impressions_brand|clicks_no_brand|impressions_no_brand|
|:----|:----|:----|:----|:----|
|2023-01-01|0.0|4.0|60|4917|
|2023-01-02|0.0|15.0|84|6648|
|2023-01-03|1.0|10.0|88|5401|
|2023-01-04|0.0|11.0|80|5390|
|2023-01-05|0.0|12.0|80|5401|
|2023-01-06|0.0|13.0|79|5492|
|2023-01-07|0.0|11.0|80|5458|


#### keyword_gap()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|query|None |pd.DataFrame|:white_check_mark:|

Some common SEO tools such as [Semmrush](https://www.semrush.com/kb/28-keyword-gap), [Ahrefs](https://ahrefs.com/content-gap) or [Sistrix](https://www.sistrix.com/tutorials/how-to-spot-which-keywords-of-your-domain-can-be-immediately-optimised/) allows you to perform a keyword gap analysis. 

This is the first step to understand what contents you may want to create for your projects if it makes sense. 

This method allows you to perform a similar operation by **comparing the keywords you have in your `Report` object and any other list of keywords. 

```python 

(
    report 
    .keyword_gap(
        #the DataFrame where your list of keywords is stored
        df, 
        #the column name where your keywords are stored
        column='keyword',
    )
)

```

This method will filter your `df`to keep only the keywords that are not included in your `Report` object. 

#### causal_impact()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|date|clicks | Causal Impact object|:white_check_mark:|

GSC is a great tool to understand if some changes applied to a specific set of pages is having a positive impact. 

This method allows you to use [Causal Impact](https://pypi.org/project/pycausalimpact/) to infer the expected effect a given intervention (or any action) had on some response variable by analyzing differences between expected and observed time series data.

```python 

(
    report 
    .causal_impact(
        intervention_date="2023-01-01",
    )
)

```

To ensure that the results make sense, **you need to have at least the same amount of days before & after the intervention date in your `Report`object**.

This method will return a `ci`object. Refer to the [documentation](https://pypi.org/project/pycausalimpact/) to understand how you can explore the results. 


#### update_urls()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|page|None | Report object|:x:|

This method is one you need to use if you're dealing with a migration. When you want to compare the traffic before / after, we need to manually update the URLs returned by GSC based on a redirect mapping we have. 

This method simplifies the process: 
* you provide a redirect mapping with **from** and **to** columns 
* the method will update your `Report`object by updating the **from** URLs by the **to** URLs. 

```python 

(
    report 
    .update_urls(
        #the dataframe where we have the from & to columns 
        redirect_mapping=redirects 
    )
)

```

As the method just update the object itself, you can then call any other method freely. 


#### extract_search_volume()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|query|None | pd.DataFrame|:x:|

GSC is a goldmine when it comes to keyword discovery, but it is sometimes handy to know what is the search volume of a given keyword we have in our dataset. 

Even if keyword volume are not the only datapoint you need to use to assess a content potential, in somes cases it must be used. 

This method leverages [DataForSEO](https://dataforseo.com/), an API I often recommand to get search volume at scale, to get the `search_volume`for your keyword. 

**Please note that this method is designed to work with any dataset size, buy I do not recommand to use it if you have more than 100,000 keywords. In that case, use a separate script.**

```python 

(
    report 
    .extract_search_volume(
        #the location code from DataForSEO
        ## 2250 is France 
        location_code=2250, 
        #credentials for the API 
        client_email="xxxx@website.com", 
        client_password="xxxxx", 
        #If you just want to calculate the cost 
        calculate_cost=True
    )
)

```

**To avoid any cost-related issue, you need to explicitely set the calculate_cost parameter to `False`to run the extraction.**. For now, **search volume are extracted for Google only**. 


#### find_potential_contents_to_kill() 

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|page|clicks / impressions | pd.DataFrame|:white_check_mark:|

This method is similar to `active_pages()`: you provide a sitemap URL and the function returns the contents based on your `clicks_threshold` and/or `impressions_threshold`. 

```python 

(
    report 
    .find_potential_contents_to_kill(
        #my sitemap 
        "https://www.website.com/sitemap_index.xml", 
        #the threshold 
        clicks_threshold=0, 
        impressions_threshold=0,
    )
)

```

This code would return a DataFrame like the following one: 

|loc|clicks|impressions|ctr|position|
|:----|:----|:----|:----|:----|
|https://www.website.com/|0.0|0.0|0.0|0.0|
|https://www.website.com/blog/2024/01/09/xxx|0.0|0.0|0.0|0.0|
|https://www.website.com/blog/2024/01/09/yyy|0.0|0.0|0.0|0.0|


Please note that you shouldn't just kill contents that have no impressions / clicks, because: 

* Some are useful even if they do not generate SEO traffic 
* Some of them may have been published some days ago 
* Some of them may need to be updated 

But it speeds a part of this process. 


#### find_content_decay()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|page / date |clicks or impressions | pd.DataFrame|:x:|

[Content Decay](https://www.clearscope.io/blog/content-decay) is something we always have to investigate to ensure that our best performing contents always stay at the top of the SERPs. 

It is indeed easier to rank better for an existing content than ranking a new one (all things being equal, obviously). This method analyzes your data and returns the content that seem to be suffering from this issue. 

```python 

(
    report 
    .find_content_decay(
        threshold_metric=100,
        #to choose between clicks and impressions 
        metric = 'clicks', 
        threshold_decay=0.1, 
        #choose between query or page 
        type='query', 
        #to choose between week and month 
        period='month')
 )
)

```

This code would return a list of contents with the following characteristics: 

* During the last (**full**) month of available data in the `Report` object, the page generating at least 10% less clicks than what it had during the peak month 
* During its peak, the content generated at least 100 clicks 

For instance: 

|query|metric_last_period|metric_max|period_max|decay|decay_abs|
| -------- | ------- |------- |------- |------- |------- |
|xxxxx|39585|78269|2023-04|0.494244|38684|

When you get the output, you need to add your industry knowledge to understand what is going on because: 
* The seasonnality can affect the outcome. Indeed, if your peak month is August and your run the analysis in December, all your contents may be "decaying". 
* New SERP layout can also affect your CTR and hence affect the output of this method 

Still, it's a good to speed-up the process and come up with a smaller list of contents to update to protect your key positions. 


#### pages_not_in_sitemap()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|page|None | pd.DataFrame|:white_check_mark:|

This method is self-explanatory. 

It will allow you to find the pages in your GSC `Report`object that are not included in a sitemap your provide. 

#### winners_losers()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|page / date|clicks | pd.DataFrame|:white_check_mark:|

This method is especially useful after Google Updates. It allows you to **quickly know what content are generating less / more clicks between two periods**.

```python 

(
    report 
    .winners_losers(
        period_from=['2023-01-01', '2023-01-15'],
        period_to=['2023-01-16', '2023-01-31'],
    )
)

```

#### find_long_tail_keywords()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|query|None | pd.DataFrame|:white_check_mark:|

Quickly filter your GSC `Report` object based on the number of words included in your keywords. 

For instance: 

```python 

(
    report 
    .find_long_tail_keywords(number_of_words=7)
)

```

This will simply filter your data to include only keywords that are composed by at least 7 words. 


#### find_ctr_outliers()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|query / date|clicks / impressions / position |pd.DataFrame|:white_check_mark:|

This method allows you to find CTR outliers. 
* It first call the `ctr_yield_curve` method to build a custom basis for comparison. **I strongly advise to filter to `Report`object accordingly to ensure that you are not mixing several SERP layouts**. 
* It then compare the expected CTR (based on weighted average position) and the real CTR (based on clicks & impressions) to find outliers. 


```python 

(
    report 
    .find_ctr_outliers()
)
```

#### abcd() 

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|None| None |pd.DataFrame|:white_check_mark:|

This methods allows you to assign an ABCD rank to a metric based on cumulative percentage contribution.

* **A**: belong to the top 50% 
* **B**: between 50 & 75% 
* **C**: between 75 and 90% 
* **D**: between 90 and 100%

For instance, if e run the following code: 

```python 

(
    report
    .abcd('clicks')
 )

```

we could get this table as the output: 

|country|clicks|abcd|
|:----|:----|:----|
|mex|5955|A|
|ecu|1936|B|
|ven|1447|B|
|esp|765|C|
|col|716|C|


#### pages_per_day()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|date / page | None |pd.DataFrame|:white_check_mark:|

This method has been designed thinking about [Google Discover](https://developers.google.com/search/docs/appearance/google-discover?hl=en). You can easily know how many pages has appeared per day using this method. 

```python 

(
    report
    .pages_per_day()
 )

```

This would return a table with the number of pages per day, as the name of the method suggest. 

|date|page|
|:----|:----|
|2024-01-01|1901|
|2024-01-02|2544|
|2024-01-03|2761|
|2024-01-04|2853|
|2024-01-05|2473|
|2024-01-06|2281|
|2024-01-07|2796|


#### pages_lifespan()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|date / page | None |pd.DataFrame|:white_check_mark:|

Similar function to **pages_per_day()**, but is tells you what is the average lifespan of a page in your dataset. 

#### seasonality_per_day()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|date | clicks / impressions |pd.DataFrame|:white_check_mark:|

This method allows you to quickly understand the weekly seasonnality you have in your data. 

```python 

(
    report
    .seasonality_per_day()
 )

```

It would return a table as the following: 

|date|click|impressions|
|:----|:----|:----|
|Monday|2218|352148|
|Tuesday|2456|399690|
|Wednesday|2532|414933|
|Thursday|2312|381517|
|Friday|1081|195331|
|Saturday|827|142410|
|Sunday|1267|210677|

#### replace_query_from_list()

|Required dimensions|Required metrics| Output|BQ ready|
|:----|:----|:----|:----|
|query | None |pd.DataFrame|:x:|

When you are working on a project where pages are created at scale, you **don't want to understand what are the most common keywords, but are the most common structures**. 

To achieve this objective, this method allow us to **replace any occurence of an element of a list in our query column.** For instance, if you have a travel website, you won't have "flight paris barcelona" but "flight _element_ _element_" assuming that you provide a list of cities. 

**This will considerably speed-up your analysis to optimize your templates.** 

```python 

(
    report
    .replace_query_from_list(word_list)
 )

```


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
