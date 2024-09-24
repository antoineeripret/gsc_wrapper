from . import utils
import time 
import pandas as pd 
from copy import deepcopy
from .stopwords import stopwords
from .regex import WORD_DELIM

#variables we'll use in this code 
#added here to follow DRY principle
#this will also ease updates if the API changes

DIMENSIONS = ['country','device','page','query','searchAppearance','date']
OPERATORS = ['equals','notEquals','contains','notContains','includingRegex','excludingRegex']
SEARCH_TYPES = ['web', 'image', 'video', 'discover','googleNews','news']
DATA_STATES = ['all','final']

#this is not from the API but we'll use it to group data by period
PERIODS = ['D','W','M','Q','Y','QE','ME']

class Query:
    """
    Return a query for certain metrics and dimensions.

    This is the main way through which to produce reports from data in
    Google Search Console.

    The most important methods are:

    * `range` to specify a date range for your query. Queries are still limited
    by the 3 month limit and no Exception is raised if you exceed this limit.
    * `dimensions` to specify the dimensions you would like report on (country,
    device, page, query, searchAppearance)
    * `filter` to specify which rows to filter by.
    * `limit` to specify a subset of results.

    The query object is mostly immutable. Methods return a new query rather
    than modifying in place, allowing you to create new queries without
    unintentionally modifying the state of another query.
    """
    def __init__(self, service, webproperty):
        #the raw request body we'll send to the API
        self.raw = {
            'startRow': 0,
            #this is the max limit we can have 
            #see https://developers.google.com/webmaster-tools/v1/searchanalytics/query?hl=en
            'rowLimit': 25000
        }
        #this is the metadata we'll use to store the limit
        self.meta = {}
        #pass the authentification
        self.service = service
        #pass the webproperty we want to analyze
        self.webproperty = webproperty
        
    #range of dates for the GSC extraction 
    #unlike the original function from https://github.com/joshcarty/google-searchconsole/tree/master, we can't provide a days argument
    def range(self, start=None, stop=None):
        self.raw.update({
            'startDate': start,
            'endDate': stop, 
        })
        
        self.start_date = start
        self.stop_date = stop
        
        return self
    
    #list of dimensions 
    def dimensions(self, dimensions=None):
        #we need to provide at least one dimension 
        if not dimensions: 
            raise ValueError('Please provide at least one dimension.')
        #check if the dimensions is a list 
        #even if e request just one dimension, we need to create a list 
        if not isinstance(dimensions, list):
            raise TypeError('Dimensions must be a list.')
        #check that the values are correct 
        for element in dimensions:
            #see https://developers.google.com/webmaster-tools/v1/searchanalytics/query?hl=en#dimensionFilterGroups.filters.dimension
            if element not in DIMENSIONS:
                raise ValueError('{element} is not a valid dimension. Check https://developers.google.com/webmaster-tools/v1/searchanalytics/query?hl=en#dimensionFilterGroups.filters.dimension for the accepted values.')
        #we update the raw request body
        self.raw['dimensions'] = dimensions
        return self
    
    #list of filters 
    #we can apply this method more than once if we want to add more filters
    #note that these filter are applied with an AND operator (only option available in the API)
    def filter(self, dimension, expression, operator='equals',
            group_type='and'):
        #check that the values are correct 
        if dimension not in DIMENSIONS:
            raise ValueError('Dimension not valid. Check https://developers.google.com/webmaster-tools/v1/searchanalytics/query?hl=en#dimensionFilterGroups.filters.dimension for the accepted values.')
        #check the operator 
        if operator not in OPERATORS:
            raise ValueError('Operator not valid. Check https://developers.google.com/webmaster-tools/v1/searchanalytics/query?hl=en#dimensionFilterGroups.filters.operator for the accepted values.')

        dimension_filter = {
            'dimension': dimension,
            'expression': expression,
            'operator': operator
        }

        filter_group = {
            'groupType': group_type,
            'filters': [dimension_filter]
        }
        #check if we don't already have a dimensionFilterGroups
        if 'dimensionFilterGroups' not in self.raw:
            #if we don't, we create one
            self.raw.setdefault('dimensionFilterGroups', []).append(filter_group)
        else: 
            #if we do, we need to append the new filter to the existing one
            self.raw['dimensionFilterGroups'][-1]['filters'].append(dimension_filter)
        return self

    #define the search type
    def search_type(self, search_type='web'):
        if search_type not in SEARCH_TYPES:
            raise ValueError('Search type not valid. Check https://developers.google.com/webmaster-tools/v1/searchanalytics/query?hl=en#type for the accepted values.')
        self.raw['type'] = search_type
        return self

    #define the data state 
    def data_state(self, data_state='final'):
        if data_state not in DATA_STATES:
            raise ValueError('Data state not valid. Check https://developers.google.com/webmaster-tools/v1/searchanalytics/query?hl=en#dataState for the accepted values.')
        self.raw['dataState'] = data_state
        return self

    #limit the number of rows we want to return 
    def limit(self, limit=None):
        #we cannot call this method without the limit argument
        if limit is None:
            raise ValueError('Please provide a limit.')
        #the limit need to be an integer
        if not isinstance(limit, int):
            raise TypeError('Limit must be an integer.')
        #the limit cannot be negative or 0
        if limit <= 0:
            raise ValueError('Limit must be greater than 0.')
        self.meta['limit'] = limit 
        #by default we use a limit of 25,000 by call 
        #if the user wants less, we update the raw request body
        self.raw['rowLimit'] = min(limit,25000)
        return self
    
    #method to retrieve the data
    def get(self):
        #where we'll store our data 
        report = []
        #boooleans to control the flow 
        is_complete = False
        limit_achieved = False 
        #other information we'll need
        limit = self.meta.get('limit', float('inf'))
        total_rows = 0

        #we continue to execute the request until we have all the data we need
        #this can be either because there is no more date 
        #or because we have reached the limit
        while is_complete == False and limit_achieved == False:
            #wait for 1 second to avoid reaching the quota limits 
            #this is not 100% bulletproof but it should be enough for most use cases
            #while having almost no impact on performance
            time.sleep(1)
            #retrieve the data 
            chunk = self.service.searchanalytics().query(siteUrl=self.webproperty, body=self.raw).execute()
            #add our data to the report list we'll return 
            total_rows += len(chunk.get('rows', []))
            report.append(chunk.get('rows', []))
            #update the is_complete variable if we don't have more data 
            if len(chunk.get('rows', []))<25000:
                is_complete = True
            #else, update the startRow in our request body 
            else: 
                self.raw.update({'startRow': self.raw['startRow'] + 25000})
            #check if we've reached our limit
            if total_rows >= limit:
                limit_achieved = True
        
        #we flatten the list of lists we have 
        flattened = pd.DataFrame([item for row in report for item in row])
        #we check if we have no data 
        #raise an error instead of returning an empty dataframe to ensure the user is aware of the issue
        #linked to https://github.com/antoineeripret/gsc_wrapper/issues/9
        if len(flattened) == 0:
            raise ValueError('No data available. Check your request and ensure you\'re using the right dates and filters.')

        #we create a dataframe from the keys we received from the API 
        #this is the only way to get the data in a proper format 
        #while not passing explicitly the dimensions we want 
        df =   (
            pd
            .DataFrame(
            flattened
                ['keys']
                .tolist(), 
                columns = self.raw['dimensions']
            )
            .join(
                flattened
                .drop('keys', axis = 1)
            )
        )
        
        if limit != float('inf'):
            df = df.head(limit)
        
        #reset filter to prevent issue raised here https://github.com/antoineeripret/gsc_wrapper/issues/9 
        self.raw = {
            'startRow': 0,
            'rowLimit': 25000
        }
        self.meta = {}
        
        return Report(df, self.webproperty)


class Report:
    """
    Executing a query will return a report, which contains the requested data as pandas DataFrame. 
    We can then apply several analysis on the data retrieved. 
    
    """
    
    def __init__(self, df, webproperty):
        
        self.webproperty = webproperty
        self.dimensions = [column for column in df.columns if column in DIMENSIONS]
        self.metrics = [column for column in df.columns if column not in DIMENSIONS]
        if 'date' in self.dimensions:
            self.from_date = df.date.min()
            self.to_date = df.date.max()
        else: 
            self.from_date = None
            self.to_date = None
            
        self.df = df
    
    @classmethod
    def from_dataframe(cls, df, webproperty):
        return cls(df, webproperty)
        
    def __repr__(self):
        return """
    <searchconsole.account.Report(
        webproperty='{}',
        dimensions='{}',
        metrics='{}', 
        from_date='{}',
        to_date='{}'
    )>
    """.format(
            self.webproperty,
            ' - '.join(self.dimensions),
            ' - '.join(self.metrics), 
            self.from_date,
            self.to_date
    )
    
    def show_data(self):
        return self.df
    
    #function to filter data 
    def filter(self, query):
        self_copy = deepcopy(self)
        self_copy.df = self_copy.df.query(query)
        return deepcopy(self_copy) 
    
    #inspired by https://github.com/eliasdabbas/advertools
    def url_to_df(self):
        if 'page' not in self.dimensions:
            raise ValueError('Your report needs a page dimension to call this method.')
                
        #append folders to self.df horizontally 
        self.df = (
            pd
            .concat(
                [
                    #generic info 
                    self
                    .df
                    .assign(
                        #get the scheme 
                        scheme = lambda df_:df_['page'].apply(lambda x: x.split('://')[0]),
                        #get the netloc 
                        netloc = lambda df_:df_['page'].apply(lambda x: x.split('://')[1].split('/')[0]),
                        #get the path 
                        path = lambda df_:df_['page'].apply(lambda x: '/'+'/'.join(x.split('/')[3:])),
                        #get the last folder 
                        last_folder = lambda df_:df_['page'].apply(lambda x: x.split('/')[-1])
                    ), 
                    #folders
                    self
                    .df
                    .page 
                        .str.split("/", expand=True)
                        #just from 3 to N 
                        .iloc[:,3:]
                        #rename columns by adding folder_ before the current name 
                        .rename(columns=lambda x: 'folder_'+str(x-2))
                ]
            , axis=1)
        )
        return self 
    
        
    # method to create a CTR yield curve 
    # concept explained here : https://www.aeripret.com/ctr-yield-curve/
    def ctr_yield_curve(self):
        
        if not all(elem in self.dimensions for elem in ['query','date']):
            raise ValueError('Your report needs a query and a date dimension to call this method.')
        
        if not all(elem in self.metrics for elem in ['clicks','impressions','position']):
            raise ValueError('Your report needs clicks, impressions and position metrics to call this method.')
        
        return (
            self
            .df 
            #round the position 
            .assign(
                position = lambda df_: round(df_['position']),
            )
            #calculate the weighted ctr by rounded position 
            .groupby('position', as_index = False)
            .agg(
                {
                    'clicks': 'sum', 
                    'impressions': 'sum', 
                    'query':'count'
                }
            )
            #remove rows where the position >10, data is irrelevant
            .query('position <= 10')
            #rename the query column to kw_count
            .rename(columns = {'query': 'kw_count'})
            .assign(
                ctr = lambda df_: round(df_['clicks'] *100 / df_['impressions'], 2) 
            )
            #keep only useful columns
            .filter(items=['position', 'ctr','clicks','impressions','kw_count'])
            .set_index('position')
        )

    #create a function to easily group data by period 
    def group_data_by_period(self, period):
        #check if we have a date dimension
        if 'date' not in self.dimensions:
            raise ValueError('Your report needs a date dimension to call this method.')
        
        #check tha the period is valid
        if period not in PERIODS:
            raise ValueError('Period not valid. You can only use D, W, M, Q, QE or Y.')
        
        return (
            self
            .df
            #we need to convert the date to a datetime object
            .assign(
                date = lambda df_: pd.to_datetime(df_['date']),
            )
            #resample
            .set_index('date')
            .filter(items=['clicks','impressions'])
            .resample(period)
            .sum()
            .reset_index()
            .assign(
                date = lambda df_: df_['date'].dt.strftime('%Y-%m-%d')
            )
        )

    #funtion to know if a page is active (has clicks or has impressions)
    #from a list of URLs or a sitemap
    def active_pages(self,sitemap_url=None, urls=None):
        
        import numpy as np
        
        if 'page' not in self.dimensions:
            raise ValueError('Your report needs a page dimension to call this method.')
        
        #check that we have both impressions and clicks 
        if not all(elem in self.metrics for elem in ['clicks','impressions']):
            raise ValueError('Your report needs clicks and impressions metrics to call this method.')
        
        if urls and sitemap_url: 
            raise ValueError('Please provide either sitemap_url or urls')
        if not urls and not sitemap_url:
            raise ValueError('Please provide either sitemap_url or urls')
        #if we have a sitemap 
        if sitemap_url:
            #download the urls from the site map
            urls = pd.DataFrame(utils.get_urls_from_sitemap(sitemap_url), columns=['loc'])
        #otherwlse, just parse the list of urls
        elif urls:
            urls = (
                pd
                .DataFrame(urls, columns=['loc'])
            )
        
        return ( 
            self
            .df
            .groupby('page', as_index=False)
            .agg({'clicks': 'sum', 'impressions': 'sum'})
            #merge with our list of URLS 
            .merge(
                urls,
                left_on = 'page',
                right_on = 'loc', 
                #we merge RIGHT 
                #we just want to check if the page is active
                #from our initial list of URLs
                how = 'right'
            )
            .filter(items=['page','clicks','impressions','loc'])
            .assign(
                active_impression = lambda df_:np.where(df_.page.isna(), False, True), 
                active_clicks = lambda df_:df_.page.isin(df_.query('clicks>0').page.unique()), 
                page = lambda df_:df_['page'].fillna(df_['loc'])
            )
            .drop('loc', axis = 1)
            .fillna(0)

        )

    #inspired by https://github.com/jmelm93/seo_cannibalization_analysis 
    def cannibalization(self, brand_variants):
        import numpy as np 
        #check if we have the required dimensions 
        if not all(elem in self.dimensions for elem in ['query','page']):
            raise ValueError('Your report needs a query and a page dimension to call this method.')
        
        #check that we have clicks and impressions
        if not all(elem in self.metrics for elem in ['clicks','impressions']):
            raise ValueError('Your report needs clicks and impressions metrics to call this method.')
        
        #remove branded queries 
        df = (
            self
            .df
            .groupby(['query','page'], as_index=False)
            .agg({'clicks': 'sum', 'impressions': 'sum'})
            #remove branded queries
            .query('query.str.contains("|".join(@brand_variants))==False')
        )
        
        #create a separate df with the data per query
        df_query = (
            df 
            .groupby('query', as_index=False)
            .agg(
                {'clicks': 'sum', 'page': 'nunique'}
            )
            #at least two pages on the same query 
            .query('page >= 2')
            #at ñeast one click 
            .query('clicks >= 1')
        )

        #do the same for the pages 
        df_page = (
            df
            .groupby('page', as_index=False)
            .agg({'clicks': 'sum'})
        )

        #filter ou initial df based on that 
        final = (
            df
            .merge(
                df_query[['query']], 
                on = 'query',
                how = 'inner'
            )
            .groupby(['page', 'query'], as_index = False)
            .agg({
                'clicks': 'sum',
                'impressions': 'sum',
            }) 
            #we calculate the click percentage 
            .assign(
                click_pct = lambda df_: df_.groupby('query')['clicks'].transform(lambda x: x / x.sum())
            )  
        )
        
        #queries to keep 
        queries_to_keep = (
            final 
            .query('click_pct >= 0.1')
            .groupby('query')
            .filter(lambda x: len(x) >= 2)
            ['query']
            .unique()
        )

        #we keep only these queries 
        final = (
            final 
            .query('query in @queries_to_keep')
            .merge(
                df_page, 
                on='page', 
                how='inner'
            )
            .rename(columns={'clicks_x': 'clicks_query', 'clicks_y': 'clicks_page'})
            .assign(
                click_pct_page = lambda df_:df_.clicks_query / df_.clicks_page, 
                opportunity_level = lambda df_:(
                    np
                    .where(
                        (df_.click_pct_page >=0.1) & (df_.click_pct >= 0.1), 
                        "Potential Opportunity", 
                        "Risk - Low percentage of either query-level or page-level clicks"

                    )
                )
            )
            .query('opportunity_level == "Potential Opportunity"')
            .drop('opportunity_level', axis=1)
            .assign(
                keep = lambda df_:df_.duplicated('query', keep=False), 
                click_pct = lambda df_: round(df_.click_pct*100, 2), 
                click_pct_page = lambda df_: round(df_.click_pct_page*100, 2) 
            )
            .query('keep == True')
            .drop('keep', axis=1)
            .sort_values(['query','clicks_query'], ascending=[True, False])
        )

        return final 

    def forecast(self, days):
        from prophet import Prophet
        
        #ensure that we have date as a dimension 
        if 'date' not in self.dimensions:
            raise ValueError('Your report needs a date dimension to call this method.')
        
        #ensure that we have clicks as a metric
        if 'clicks' not in self.metrics:
            raise ValueError('Your report needs clicks as a metric to call this method.')

        df = (
            self 
            .df
            .groupby('date', as_index=False)
            .agg({'clicks': 'sum'})
            .rename(
                columns = {'date': 'ds', 'clicks': 'y'}
            )
        )

        m = Prophet()
        m.fit(df)
        future = m.make_future_dataframe(periods=days)
        forecast = m.predict(future)
        return forecast 

    #brand vs non brand traffic evolution 
    def brand_vs_no_brand(self, brand_variants):
        
        #check that query is in the dimensions 
        if 'query' not in self.dimensions:
            raise ValueError('Your report needs a query dimension to call this method.')
        
        #we need the date dimension
        if 'date' not in self.dimensions:
            raise ValueError('Your report needs a date dimension to call this method.')
        
        
        brand = (
            self
            .df 
            .query('query.str.contains("|".join(@brand_variants))')
            .groupby('date', as_index=False)
            #dict comprension to create the metrics we want
            .agg({metric: 'sum' for metric in self.metrics})
            .filter(['date','clicks','impressions'])
        )

        no_brand = (
            self 
            .df 
            .query('query.str.contains("|".join(@brand_variants))==False')
            #drop columns that are not clicks or impressions 
            .groupby('date', as_index=False)
            #dict comprension to create the metrics we want
            .agg({metric: 'sum' for metric in self.metrics})
            .filter(['date','clicks','impressions'])
        )

        return (
            brand
            .merge(
                no_brand,
                on = 'date',
                how = 'outer',
                suffixes = ('_brand', '_no_brand')
            )
            .fillna(0)
        )


    #keyword gap
    def keyword_gap(self, df=None, keyword_column=None):
        
        # Check if df is a pandas DataFrame
        if not isinstance(df, pd.DataFrame):
            raise ValueError("df must be a pandas DataFrame")

        # Check if the specified column is in the DataFrame
        if keyword_column not in df.columns:
            raise ValueError(f"{keyword_column} is not a column in the DataFrame")
        
        #ensure that we have the query dimension
        if 'query' not in self.dimensions:
            raise ValueError('Your report needs a query dimension to call this method.')

        return (
            df[df[keyword_column].isin(self.df['query'])==False]
        )
        
    #causal impact 
    def causal_impact(self, intervention_date = None ):
        
        #we neeed some extra libraries for this method 
        from causalimpact import CausalImpact
        import datetime
        
        #interverntion date must be defined
        if not intervention_date:
            raise ValueError("Intervention_date must be defined")
        
        #date must be a dimensions 
        if 'date' not in self.dimensions:
            raise ValueError('Your report needs a date dimension to call this method.')
        
        #clicks must be a metric
        if 'clicks' not in self.metrics:
            raise ValueError('Your report needs clicks as a metric to call this method.')


        data = (
            self
            .df 
            .filter(items=['date', 'clicks'])
            .groupby('date', as_index=False)
            .agg({'clicks': 'sum'})
        )
        
        #calculate the number of days between the last data point and the intervention date 
        days = (pd.to_datetime(data['date']).max() - pd.to_datetime(intervention_date)).days
        #get the prior dates 
        max_date = pd.to_datetime(data['date']).max().strftime("%Y-%m-%d")
        max_before_interenvention = utils.get_date_days_before(intervention_date, days=1)
        min_before_intervention = utils.get_date_days_before(max_before_interenvention, days=days)

        #get the interval for the analysis  
        post_period = [intervention_date, max_date]
        pre_priod = [min_before_intervention, max_before_interenvention]

        #build the ci objec 
        ci = CausalImpact(data.set_index('date').clicks, pre_period = pre_priod, post_period = post_period)
        #return it 
        #the rest of the method are controlled by https://pypi.org/project/pycausalimpact/
        #usually ci.summary() or ci.plot() are enough
        return ci 
    
    #function to update the urls in the report using a redirect mapping 
    def update_urls(self, redirect_mapping):
        
        #redirect mapping needs to be a pandas DataFrame
        if not isinstance(redirect_mapping, pd.DataFrame):
            raise ValueError("redirect_mapping must be a pandas DataFrame")
        
        #we need to have a from & a to column sin redirect_mapping
        if not all(elem in redirect_mapping.columns for elem in ['from','to']):
            raise ValueError('redirect_mapping must have a from and a to column')
        
        #we need to have a page dimension
        if 'page' not in self.dimensions:
            raise ValueError('Your report needs a page dimension to call this method.')
        
        self_copy = deepcopy(self)
        #we update the variables in the object itself 
        self_copy.df = (
            #we marge our initial response from the GSC API 
            self_copy
            .df
            .merge(
                #with our redirect mapping 
                redirect_mapping
                #keep only useful columns 
                .filter(items=['from','to']),
                #the dimension name from GSC API 
                left_on = 'page',
                #the column name in the redirect mapping
                right_on = 'from',
                how = 'left'
            )
            .assign(
                #we change the page value based on the redirect mapping
                #if we have a na value, it's becase the page is not in our redirect mapping 
                page = lambda df_:df_['to'].fillna(df_['page'])
            )
        )
        
        return self_copy
    
    #extract search volume from dataforSEO 
    def extract_search_volume(self, location_code, client_email, client_password, calculate_cost = True):
        #check that the location code is an integer
        if not isinstance(location_code, int):
            raise ValueError('Location code must be an integer.')
        
        #check that we have a query dimension
        if 'query' not in self.dimensions:
            raise ValueError('Your report needs a query dimension to call this method.')
        
        #donwload the valid options for the location code
        client = utils.RestClient(client_email, client_password)
        r = client.get('/v3/keywords_data/google_ads/locations')
        #if we can't download the data, we stop the process
        if r['status_code'] != 20000:
            raise ValueError('We could not download the location data. Please check your credentials.')
        #we convert the data into a dataframe
        location_codes = pd.DataFrame(r['tasks'][0]['result']).location_code.tolist()
        if location_code not in location_codes:
            raise ValueError('Location code not valid. Check https://docs.dataforseo.com/v3/keywords_data/google_ads/locations/ for the accepted values.')
        
        #we create the list of keywords we want to extract
        keywords = utils.return_chunks(self.df['query'].unique().tolist())
        
        if calculate_cost:
            #we calculate the cost of the extraction and print it 
            print('The cost of the extraction will be ${}.'.format(len(keywords)*0.05))
        else:
            #we proceed with the extraction 
            #create the jobs and get the ids in dataforSEO
            jobs_id = utils.create_jobs_and_get_ids(keywords, 'gsc_wrapper', location_code, client)
            #we wait for the data to be ready to download the results 
            sv = utils.get_search_volume(jobs_id, client)
            #we merge the data with our initial report
            
            return (
                self 
                .df 
                .merge(
                    sv
                    .query('monthly_searches.isna()==False')
                    .drop_duplicates(subset = ['keyword'], keep='first')
                    .filter(items = ['keyword', 'search_volume']),
                    left_on = 'query',
                    right_on = 'keyword',
                    how = 'left'
                )
                .assign(
                    search_volume = lambda df_:df_['search_volume'].fillna(0)
                )
                .drop('keyword', axis = 1)
            )
            
    #fonctions to find potential contents to kill 
    def find_potential_contents_to_kill(self, sitemap_url=None, clicks_threshold = 0, impressions_threshold = 0):
        #we need the page dimension
        if 'page' not in self.dimensions:
            raise ValueError('Your report needs a page dimension to call this method.')
        
        #we need the impressions & the clicks 
        if not all(elem in self.metrics for elem in ['clicks','impressions']):
            raise ValueError('Your report needs clicks and impressions metrics to call this method.')
        
        #check that we have a sitemap 
        if not sitemap_url:
            raise ValueError('Please provide a sitemap_url.')
        
        #download the urle from the sitemap
        urls = pd.DataFrame(utils.get_urls_from_sitemap(sitemap_url), columns=['loc'])
        
        #return the pages that are in the sitemap but below our thresholds
        return (
            urls
            .merge(
                self.df.groupby('page', as_index=False).agg({'clicks': 'sum', 'impressions': 'sum'}),
                left_on = 'loc',
                right_on = 'page',
                how = 'left'
            )
            .fillna(0)
            .query('clicks <= @clicks_threshold & impressions <= @impressions_threshold')
            .drop('page', axis=1)
        )
        
    #change of position ovr time 
    def position_over_time(self):
        #ensure that we have the date and query dimension 
        if not all(elem in self.dimensions for elem in ['query','date']):
            raise ValueError('Your report needs a query and a date dimension to call this method.')
        
        return (
            self
            .df
            .assign(
                #we round position to have a better view of the evolution
                position = lambda df_: round(df_['position']), 
                #we need to have a time object here 
                #we then keep only the yearMonth
                date = lambda df_: pd.to_datetime(df_['date']).dt.strftime("%Y-%m")
            )
            #we just want the top 10 here 
            .query('position <= 10')
            #we create a pivot with position as the x-axis and the yearMonth as the y-axis
            .pivot_table(
                index = 'position', 
                columns = 'date', 
                values = 'query', 
                aggfunc = 'count'
            )
        )
    
    
    #function to find potential contents to update
    #we use the content decay approach here 
    def find_content_decay(
        self, threshold_decay=0.25,
        metric='clicks',
        threshold_metric=100, 
        type='page', 
        period='week'
        ):
        #check that we have the page and date dimensions 
        if not all(elem in self.dimensions for elem in [type,'date']):
            raise ValueError(f'Your report needs a {type} and a date dimension to call this method.')
        
        #check that we have the clicks metrics 
        if metric not in self.metrics:
            raise ValueError('Your report needs clicks as a metric to call this method.')
        
        #threshold must be a float between 0.01 and 1
        if not isinstance(threshold_decay, float):
            raise ValueError('Threshold must be a float.')
        if threshold_decay < 0.01 or threshold_decay > 1:
            raise ValueError('Threshold must be between 0.01 and 1.')
        
        #threadhold for clicks must be a positive integer 
        if not isinstance(threshold_metric, int):
            raise ValueError('Threshold must be an integer.')
        if threshold_metric < 0:
            raise ValueError('Threshold must be a positive integer.')
        
        #period must be either week or month 
        if period not in ['week','month']:
            raise ValueError('Period must be either week or month')
        
        #type must be either page or query 
        if type not in ['page','query']:
            raise ValueError('Type must be either page or query')
        
        #cut the df to have complete months only
        #we start by converting the date to a datetime object
        df = (
            self
            .df
            .assign(
                date = lambda df_: pd.to_datetime(df_['date'])
            )
        )
        #Find the start and end of the full months
        start_date = df['date'].min()
        if period == 'month': 
            #used later in the final data manipulation 
            date_format = '%Y-%m'
            #if this is not the first day of the month, we want the first day of the following month 
            if start_date.day != 1:
                start_date = (start_date + pd.offsets.MonthBegin(1))
        
            #do the same for the end date
            end_date = df['date'].max()
            if end_date.is_month_end == False:
                end_date = (end_date - pd.offsets.MonthEnd(1))
        
        elif period == 'week':
            #used later in the final data manipulation 
            date_format = '%Y-%U'
            #if this is not the first day of the week, we want the first day of the following week 
            if start_date.dayofweek != 0:
                start_date = (start_date + pd.offsets.Week(0))
            
            #do the same for the end date
            end_date = df['date'].max()
            if end_date.dayofweek != 6:
                #get prevous monday
                end_date = (end_date + pd.offsets.Week(0))

        df = (
            df
            #filter based on start & end date 
            .query('@start_date <= date <= @end_date')
            #.query('date >= @start_date & date <= @end_date')
            #create a yearMonth column
            .assign(
                date_period = lambda df_: df_['date'].dt.strftime(date_format)
            )
            #group by page and date 
            .groupby([type,'date_period'], as_index=False)
            .agg({metric: 'sum'})
            .assign(
                #get the max number of clicks per page 
                metric_max = lambda df_: df_.groupby(type)[metric].transform('max'), 
                #get the date of the max period 
                period_max = lambda df_:(
                    df_
                    .groupby([type,'date_period'], as_index=False)
                    .agg({metric:'sum'})
                    .sort_values(metric, ascending=False)['date_period']
                    .iloc[0]
                )
            )
            #remove pages with less than X clicks based on the threshold
            .query('metric_max >= @threshold_metric')
            #reame column to better reflect what we have
            .rename(columns = {metric: 'metric_last_period'})
            #keep only the last month
            .query('date_period == @end_date.strftime(@date_format)')
            .assign(
                decay = lambda df_: round(1 - df_['metric_last_period'] / df_['metric_max'],3), 
                decay_abs = lambda df_: df_['metric_max'] - df_['metric_last_period']
            )
            .drop('date_period', axis = 1)
            .query('decay >= @threshold_decay')
            .sort_values('decay_abs', ascending=False)
        )
        
        return df 
    
    #function to check if we have pages in GSC that are not in our sitemap
    def pages_not_in_sitemap(self, sitemap_url):
        #we need the page dimension
        if 'page' not in self.dimensions:
            raise ValueError('Your report needs a page dimension to call this method.')
        
        #check that we have a correct sitemap URL 
        if utils.check_sitemap_url(sitemap_url):
            #download the urle from the sitemap
            urls = pd.DataFrame(utils.get_urls_from_sitemap(sitemap_url), columns=['loc'])
            
            return (
                self
                .df
                .query('page.isin(@urls["loc"])==False')
            )
    
    #function to find winners and losers between two period 
    def winners_losers(self, period_from, period_to):
        from datetime import datetime
        
        #we need to have the page and the date dimensions 
        if not all(elem in self.dimensions for elem in ['page','date']):
            raise ValueError('Your report needs a page and a date dimension to call this method.')
        
        #check that we have the metric in our metrics 
        if 'clicks' not in self.metrics:
            raise ValueError('Your report needs clicks to call this method.')
        
        #period from and period to must be a list of two elements
        if not isinstance(period_from, list) or len(period_from) != 2:
            raise ValueError('Period from must be a list of two elements.')
        if not isinstance(period_to, list) or len(period_to) != 2:
            raise ValueError('Period to must be a list of two elements.')
        
        #check that in these list we have parsable dates 
        period_from_check = [utils.are_dates_parsable(date) for date in period_from]
        period_to_check = [utils.are_dates_parsable(date) for date in period_to]
        
        if not all(period_from_check) or not all(period_to_check):
            raise ValueError('Periods from must be a list of two parsable dates using the YYYY-MM-DD format.')
        
        #check that the first element of both list is before the seoond element
        if datetime.strptime(period_from[1], "%Y-%m-%d") < datetime.strptime(period_from[1], "%Y-%m-%d"):
            raise ValueError('The first element of period from must be before the second element.')
        if datetime.strptime(period_to[1], "%Y-%m-%d") < datetime.strptime(period_to[1], "%Y-%m-%d"):
            raise ValueError('The first element of period from must be before the second element.')
        
        #check that there is no overlap between the two periods
        if datetime.strptime(period_from[1], "%Y-%m-%d") > datetime.strptime(period_to[0], "%Y-%m-%d"):
            raise ValueError('Periods must not overlap.')
        
        #check that the data we provide in df is within the two periods 
        if pd.to_datetime(self.df['date']).min() > datetime.strptime(period_from[0], "%Y-%m-%d"):
            raise ValueError('The data in your report is not within the period from.')
        if pd.to_datetime(self.df['date']).max() < datetime.strptime(period_to[1], "%Y-%m-%d"):
            raise ValueError('The data in your report is not within the period to.')
        
        #we create two dataframes with the data for each period
        df_from = (
            self
            .df
            .query('@period_from[0] <= date <= @period_from[1]')
            .groupby(['page'], as_index=False)
            .agg({'clicks': 'sum'})
        )
        
        df_to = (
            self
            .df
            .query('@period_to[0] <= date <= @period_to[1]')
            .groupby(['page'], as_index=False)
            .agg({'clicks': 'sum'})
        )
        
        return (
        #we marge the two dataframes on the page key 
            df_from
            .merge(
                df_to,
                on = 'page',
                how = 'outer',
                suffixes = ('_before','_after')
            )
            #we assign a value based on either it is a winner or a loser 
            .assign(
                diff = lambda df_:df_.clicks_after - df_.clicks_before, 
                winner = lambda df_:df_['diff'] > 0, 
            )
        )
        
        
    #fonction to filter to keep only keyword with at least X keywords 
    def find_long_tail_keywords(self, number_of_words):
        #check that the number of words is a positive integer greater than 0 
        if not isinstance(number_of_words, int):
            raise ValueError('The number of words argument needs to be an integer')
        if number_of_words < 1: 
            raise ValueError('The number of words argument must be greater than 0.')
        
        #check that we have keywords in our dimensions 
        if 'query' not in self.dimensions: 
            raise ValueError('The query dimension is not included in your report.')
        
        return (
            self 
            .df 
            .assign(
                #count the number of words per query 
                n_words = lambda df_:df_['query'].str.split(' ').str.len()
            )
            #we filter based on our condition 
            .query('n_words >= @number_of_words')
        )
    
    #find outliers based on CTR 
    def find_ctr_outliers(self):
        import numpy as np 
        #first we need to get our ctr curve for our data 
        ctr_yield_curve = self.ctr_yield_curve().filter(items=['position','ctr'])
        #no need to perform all checks here because it would be handled by the
        #ctr_yield_curve() method called just before 
        
        #first we get the weighted average position for the query
        weighted_avg_position = (
            self 
            .df 
            .groupby('query')
            .apply(lambda x: round(np.average(x['position'], weights=x['impressions'])))
            .reset_index(name='position')
            #keep only useful columns 
            .filter(items=['query','position'])
            #do not keep query below 10 
            .query('position <= 10')
        )
        
        df = (
            self
            .df 
            .groupby('query', as_index=False)
            .agg(
                {
                    'clicks':'sum',
                    'impressions':'sum', 
                }
            )
            .assign(
                #we calcule the CTR by query 
                real_ctr=lambda df_:round(100*df_.clicks/df_.impressions, 2)
            )
            #add the position 
            .merge(
                weighted_avg_position, 
                on='query',
                #right to remove the query with a weighted position > 10  
                how='right'
            )
            #add the expected ctr 
            .merge(
                ctr_yield_curve, 
                on='position', 
                how='left'
            )
            #rename column to have a better name in this context 
            .rename({'ctr':'expected_ctr'}, axis=1)
            #calculate the diff between expected and real clicks 
            .assign(
                loss = lambda df_:round(df_.impressions*(df_.expected_ctr - df_.real_ctr)/100)
            )
            #we order by loss 
            .sort_values(by='loss', ascending=False)
            #we keep only rows where we underperform 
            .query('loss > 0')
        )
        
        return df 
        
    def abcd(self, metric='clicks'):
    #Assign an ABCD class and rank to a metric based on cumulative percentage contribution
    #Based on https://github.com/practical-data-science/ecommercetools/blob/master/ecommercetools/seo/google_search_console.py 
    #even if code is different, the logic is the same
        
        #check that we have the metric in our metrics
        if metric not in self.metrics:
            raise ValueError('Your report needs the metric you want to use to call this method.')
        
        return (
            self
            .df 
            .sort_values(metric, ascending=False)
            .assign(
                metric_cumsum = lambda df_:round(100*df_[metric].cumsum()/df_[metric].sum(), 2),
                abcd = lambda df_:(
                    df_
                    ['metric_cumsum']
                    .case_when(
                        caselist = [
                            (df_['metric_cumsum'].between(0, 50, inclusive='left'), 'A'),
                            (df_['metric_cumsum'].between(50, 75, inclusive='left'), 'B'),
                            (df_['metric_cumsum'].between(75, 90, inclusive='left'), 'C'),
                            (df_['metric_cumsum'].between(90, 100, inclusive='both'), 'D'),
                        ]
                    )
                )
            )
            .drop('metric_cumsum', axis=1)
        )
    
    def pages_per_day(self):
        #check that we have the date and page dimensions
        if not all(elem in self.dimensions for elem in ['date','page']):
            raise ValueError('Your report needs a date and a page dimension to call this method.')
        
        return (
            self
            .df
            .assign(
                date = lambda df_: pd.to_datetime(df_['date']).dt.strftime('%Y-%m-%d')
            )
            .sort_values('date', ascending=True)
            .groupby('date')
            .agg({'page': 'nunique'})
        )
        
    def pages_lifespan(self):
        #check that we have the date and page dimensions
        if not all(elem in self.dimensions for elem in ['date','page']):
            raise ValueError('Your report needs a date and a page dimension to call this method.')
        
        return (
            self
            .df 
            #group by page
            .groupby('page', as_index=False)
            #get the number of unique dates by page 
            .agg({'date':'nunique'})
            .date
            #summarize 
            .value_counts()
            .reset_index()
            .rename(columns={'date':'duration (days)'})
        )
    
    def seasonality_per_day(self):
        #check that we have the date dimension
        if 'date' not in self.dimensions:
            raise ValueError('Your report needs a date dimension to call this method.')
        
        return (
            self.df
            .assign(
                #get the day of the week 
                date=lambda df_: pd.to_datetime(df_['date']).dt.day_name()
            )
            .assign(
                #reorder from Monday to Sunday 
                date=lambda df_: pd.Categorical(df_['date'], categories=[
                    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                    ordered=True)
            )
            #group by day of the week
            .sort_values('date', ascending=True)
            .groupby('date')
            .agg({'clicks': 'sum', 'impressions': 'sum'})
        )
    
    def replace_query_from_list(self, list_to_replace):
        from functools import reduce
        #Function to apply replacements
        def replace_element(column, element):
            return column.str.replace(element, "_element_")
        
        #we need to have the query dimension
        if 'query' not in self.dimensions:
            raise ValueError('Your report needs a query dimension to call this method.')
        
        return (
            self 
            .df 
            .assign(
                #freduce funtion to apply the replace_element function to the query column
                query_replaced = reduce(replace_element, list_to_replace, self.df['query'])
            )
        )
    
    #inspired by https://www.searchenginejournal.com/big-query-and-gsc-data-content-performance-analysis/508481/ 
    #funtion to get the unique query count per page
    def uqc(self):
        #check that we have the query dimension
        if 'query' not in self.dimensions:
            raise ValueError('Your report needs a query dimension to call this method.')
        
        if 'page' not in self.dimensions:
            raise ValueError('Your report needs a page dimension to call this method.')
        
        return (
            self
            .df
            .groupby('page', as_index=False)
            .agg({'query': 'nunique'})
            .rename(columns={'query': 'uqc'})
            .sort_values('uqc', ascending=False)
        )
    
    #method used to classify pages based on a DataFrame with rules 
    def classify_pages(self, rules):
        #check that we have the page dimension
        if 'page' not in self.dimensions:
            raise ValueError('Your report needs a page dimension to call this method.')
        
        #check that the rules are a pandas DataFrame
        if not isinstance(rules, pd.DataFrame):
            raise ValueError('Rules must be a pandas DataFrame.')
        
        #check that we have the page and the classification columns in the rules
        if not all(elem in rules.columns for elem in ['category','rule','type']):
            raise ValueError('Rules must have a page and a classification column.')
        
        #rules types must be within the same types supported by the filter() call 
        if not all(elem in ['equals','contains','includingRegex'] for elem in rules.type.unique()):
            raise ValueError('Check that the rules types are within the following list: equals, contains, includingRegex')
        
        
        
        #create all the caselist for Pandas 
        caselist=[]
        #loop the rules to create the caselist
        #that we will use to update the self.df object 
        for index, row in rules.iterrows():
            if row['type'] == 'equals':
                caselist.append((self.df['page']==row['rule'], row['category']))
            elif row['type'] == 'contains':
                caselist.append((self.df['page'].str.contains(row['rule'], regex=False), row['category']))
            elif row['type'] == 'includingRegex':
                caselist.append((self.df['page'].str.contains(row['rule'], regex=True), row['category']))
        
        #last rule to ensure we always have a category
        caselist.append((self.df['page'].str.contains("http"), 'Other'))
                
        #based on these rules, we update the self.df object 
        self_copy = deepcopy(self)
        self_copy.df = (
            self_copy
            .df
            .assign(
                category = lambda df_:df_
                .page
                .case_when(
                    caselist = caselist
                )
            )
        )
        
        return self_copy
    
    #function to know when a page or a query was first found
    def add_first_found(self, dimension):
        if dimension not in ['page','query']:
            raise ValueError('Dimension must be either page or query.')
        
        if dimension not in self.dimensions:
            raise ValueError(f'Your report needs a {dimension} dimension to call this method.')
        
        if 'date' not in self.dimensions:
            raise ValueError('Your report needs a date dimension to call this method.')
        
        #create a copy of self to modify it 
        self_copy = deepcopy(self)
        #we create the df with the first_found column
        first_found = (
            self 
            .df 
            .assign(
                date = lambda df_: pd.to_datetime(df_['date'])
            )
            .groupby(dimension, as_index=False)
            .agg({'date': 'min'})
            .rename(columns={'date': f'first_found_{dimension}'})
        )
        
        #we merge and return the result 
        self_copy.df = (
            self_copy
            .df
            .merge(
                first_found,
                on=dimension,
                how='left'
            )
        )
        
        return self_copy
        
    #heavily inspired by https://advertools.readthedocs.io/en/master/_modules/advertools/word_frequency.html 
    #fonction to return word frequency 
    def word_frequency(
        #the df with query and the dimensions 
        self, 
        #the number of words we want to analyze 
        phrase_len=1, 
        #the stopwords we want to remove 
        stopwords=stopwords['english'], 
        #custom stopwords we want to remove
        rm_words=[]
    ):
        
        #needed for part of the process 
        from collections import defaultdict
        
        #we need the query dimension
        if 'query' not in self.dimensions:
            raise ValueError('Your report needs a query dimension to call this method.')
        
        #we need clicks and impressions 
        if not all(elem in self.metrics for elem in ['clicks','impressions']):
            raise ValueError('Your report needs clicks and impressions as metrics to call this method')
        
        #we split using the spaces 
        word_split = [text.lower().split() for text in self.df['query']]
        #we also split using other delimiters we have stored 
        word_split = [[word.strip(WORD_DELIM) for word in text] for text in word_split]
        #we keep only the words based on our phrase_len limit 
        word_split = [[' '.join(s[i:i + phrase_len]) for i in range(len(s) - phrase_len + 1)] for s in word_split]
        
        #we lower the stopwords
        stopwords = [word.lower() for word in stopwords]
        #we create a dictionary with the default values
        word_freq = defaultdict(lambda: [0, 0, 0])
        
        #we loop our words and our values 
        for text, clicks, impressions in zip(word_split, self.df['clicks'], self.df['impressions']):
            for word in text:
                if word.lower() in rm_words:
                    continue 
                if word.lower() in stopwords:
                    continue
                word_freq[word.lower()][0] += 1
                word_freq[word.lower()][1] += clicks
                word_freq[word.lower()][2] += impressions
        
        columns = ["count", "clicks", "impressions"]
        word_freq = (
            pd
            .DataFrame
            .from_dict(word_freq, columns=columns, orient="index")
        )
        return word_freq
    
    #function to get the response codes of the pages 
    def get_response_codes(self, wait_time=0): 
        from tqdm import tqdm
        
        #we need the page dimension
        if 'page' not in self.dimensions:
            raise ValueError('Your report needs a page dimension to call this method.')
        
        #we create the unique list of page s
        pages = self.df['page'].unique().tolist()
        #we create the dict where we'll store our results 
        response_codes = {}
        #we loop our pages and get  the response code 
        #and append it to the dict 
        for page in tqdm(pages):
            response_codes[page] = utils.get_response_code(page)
            if wait_time > 0:
                time.sleep(wait_time)
        
        #we load the result into a dataframe
        response_codes = pd.DataFrame(response_codes.items(), columns=['page', 'response_code'])
        
        #we create a copy of self to modify it 
        self_copy = deepcopy(self)
        self_copy.df = (
            self_copy
            .df
            .merge(
                response_codes,
                on='page',
                how='left'
            )
        )
        
        return self_copy

