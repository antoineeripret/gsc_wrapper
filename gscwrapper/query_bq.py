
import pandas_gbq
import pandas as pd 
from . import utils
from google.cloud import bigquery

OPERATORS = ['equals','notEquals','contains','notContains','includingRegex','excludingRegex']
OPERATORS_BQ  = ['=','!=','LIKE','NOT LIKE','REGEXP_CONTAINS','NOT REGEXP_CONTAINS']
DIMENSIONS_SITE = ['site_url','query','is_anonymized_query','country','search_type','device']
DIMENSIONS_URL = [
    'url',
    'is_anonymized_discover_',
    'is_amp_top_stories',
    'is_amp_blue_link'
    'is_job_listing',
    'is_job_details',
    'is_tpf_qa',
    'is_tpf_faq',
    'is_tpf_howto',
    'is_weblite',
    'is_action',
    'is_events_listing',
    'is_events_details',
    'is_search_appearance_android_app',
    'is_amp_story',
    'is_amp_image_result',
    'is_video',
    'is_organic_shopping',
    'is_review_snippet',
    'is_special_announcement',
    'is_recipe_feature',
    'is_recipe_rich_snippet',
    'is_subscribed_content',
    'is_page_experience',
    'is_practice_problems',
    'is_math_solvers',
    'is_translated_result',
    'is_edu_q_and_a',
    'is_product_snippets',
    'is_merchant_listings',
    'is_learning_videos',
]

#this is not from the API but we'll use it to group data by period
PERIODS = ['D','W','M','Q','Y','QE','ME']

#function to calculate GBQ query cost before actually running it 
def calculate_gbq_cost(query, client):
    # Create a QueryJobConfig object and enable dry_run
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    # Perform the dry run query to get stats
    dry_run_query_job = client.query(query, job_config=job_config)
    # Calculate the cost assuming the price is $5 per TB (as of the last update, check the pricing page)
    # Note: Prices can vary by region and over time.
    estimated_cost = (dry_run_query_job.total_bytes_processed / (1024**4)) * 5
    return round(estimated_cost,4)

class Query_BQ:
    def __init__(self, credentials, dataset):
        self.credentials = credentials
        self.dataset = dataset
        #we need to define them to have a better filtering of our data 
        self.dates = {} 
        self.filters = ''
        #list of dimensions to define the best table to use to optimize costs 
        self.filters_dimensions = []
        #to connect easily to BQ 
        pandas_gbq.context.credentials = self.credentials
        pandas_gbq.context.project = self.dataset.split('.')[0]
    
    def data_summary(self):
        # The credentials and project_id arguments can be omitted.
        df = pandas_gbq.read_gbq(
            f"""
            SELECT
            table_name,
            CASE
                WHEN regexp_contains(partition_id, '^[0-9]{{4}}$') THEN 'YEAR'
                WHEN regexp_contains(partition_id, '^[0-9]{{6}}$') THEN 'MONTH'
                WHEN regexp_contains(partition_id, '^[0-9]{{8}}$') THEN 'DAY'
                WHEN regexp_contains(partition_id, '^[0-9]{{10}}$') THEN 'HOUR'
                END AS partition_type,
            min(partition_id) AS earliest_partition,
            max(partition_id) AS latest_partition_id,
            COUNT(partition_id) AS partition_count,
            sum(total_logical_bytes) AS sum_total_logical_bytes,
            max(last_modified_time) AS max_last_updated_time
            FROM `{self.dataset}.INFORMATION_SCHEMA.PARTITIONS`
            GROUP BY 1, 2
            HAVING partition_type is not null 

            """)
        
        return df
    
    def range(self, start=None, stop=None):
        #we must check that we are using YYYY-MM-DD format
        if start and stop:
            if len(start) != 10 or len(stop) != 10 or len(start.split('-')) != 3 or len(stop.split('-')) != 3:
                raise ValueError('The dates must be in the format YYYY-MM-DD')
            #get the upper and lower bounds of the date range
            data = self.data_summary()
            if int(start.replace('-','')) < int(data.earliest_partition.min()):
                raise ValueError('The date range is not valid. Check the earliest available in the dataset') 
        
        self.dates.update({
            'startDate': start,
            'endDate': stop, 
        })
        
        return self 
    
    #list of filters 
    #we can apply this method more than once if we want to add more filters
    #note that these filter are applied with an AND operator (only option available in the API)
    #to match behavior between the API and BQ even if BQ would allow us to use OR
    def filter(self, dimension, expression, operator='equals',
            group_type='and'):
        #check the operator 
        if operator not in OPERATORS:
            raise ValueError('Operator not valid. Check https://developers.google.com/webmaster-tools/v1/searchanalytics/query?hl=en#dimensionFilterGroups.filters.operator for the accepted values.')
        
        #check that the dimension is valid 
        if dimension not in DIMENSIONS_SITE and dimension not in DIMENSIONS_URL:
            raise ValueError(f'Dimension not valid: {dimension}')
        
        #create the SQL code based on the condition 
        if operator in ['equals','notEquals']:
            self.filters += f" AND {dimension} {OPERATORS_BQ[OPERATORS.index(operator)]} '{expression}'"
        if operator in ['contains','notContains']:
            self.filters += f" AND {dimension} {OPERATORS_BQ[OPERATORS.index(operator)]} '%{expression}%'"
        if operator in ['includingRegex','excludingRegex']:
            self.filters += f" AND {OPERATORS_BQ[OPERATORS.index(operator)]}({dimension}, '{expression}')"
        
        #append the dimension to the dimension list 
        self.filters_dimensions.append(dimension)
        return self 
            
    def get(self):
        #check that dates are not empty
        if 'startDate' not in self.dates.keys() or 'endDate' not in self.dates.keys():
            raise ValueError('You must define a date range')
        return Report_BQ(self.credentials, self.dataset, self.dates, self.filters, self.filters_dimensions)
    


class Report_BQ:
    def __init__(self, credentials, dataset, dates, filters, filters_dimensions):
        self.credentials = credentials
        self.client = bigquery.Client(credentials=credentials, project=credentials.project_id)
        self.dataset = dataset
        self.dates = dates
        self.filters = filters
        self.filters_dimensions = filters_dimensions
        self.estimate_cost = True
        #to connect easily to BQ 
        pandas_gbq.context.credentials = self.credentials
        pandas_gbq.context.project = self.dataset.split('.')[0]
        #we define the best table to use based on the filters dimensions 
        #in some cases, we'll force the table anyway because we'd need specific dimensions in the report
        self.define_table_to_use()
    
    def define_table_to_use(self):
        #check if all the dimensions are in the list of dimensions for the site table 
        if all([dimension in DIMENSIONS_SITE for dimension in self.filters_dimensions]):
            self.table_to_use = 'searchdata_site_impression'
        #else we use the URL table
        else:
            self.table_to_use = 'searchdata_url_impression'
    
    def define_estimate_cost(self, value=True):
        if not value: 
            self.estimate_cost = False
        return self 
    
    def ctr_yield_curve(self):
        sql = (
            f"""
            WITH raw_data AS (
                SELECT  
                CAST(ROUND((sum_position/impressions)+1) as string) as position, 
                SUM(clicks) as clicks, 
                SUM(impressions) as impressions,
                COUNT(query) as kw_count
                FROM `{self.dataset}.searchdata_url_impression` 
                WHERE 
                data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}" 
                and 
                query is not null
                {self.filters}
                group by position
                order by CAST(position as int) asc
            ) 

            SELECT 
            position, 
            ROUND(100*clicks/impressions,2) as ctr, 
            clicks, 
            impressions, 
            kw_count
            from raw_data 
            where CAST(position as INT) <=10
            """
    )
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            return pandas_gbq.read_gbq(sql)
    
    def group_data_by_period(self, period):
        
        #check tha the period is valid
        if period not in PERIODS:
            raise ValueError('Period not valid. You can only use D, W, M, Q, QE or Y.')
        
        sql = f"""
            WITH raw_data AS (
                SELECT  
                data_date, 
                SUM(clicks) as clicks, 
                SUM(impressions) as impressions,
                FROM `{self.dataset}.{self.table_to_use}` 
                WHERE 
                data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}" 
                {self.filters}
                group by data_date
            ) 
            
            select 
            * 
            from raw_data 
            
            """
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df = pandas_gbq.read_gbq(sql)       
            return (
                df
                #we need to convert the date to a datetime object
                .assign(
                    data_date = lambda df_: pd.to_datetime(df_['data_date']),
                )
                #resample
                .set_index('data_date')
                .filter(items=['clicks','impressions'])
                .resample(period)
                .sum()
                .reset_index()
                .assign(
                    data_date = lambda df_: df_['data_date'].dt.strftime('%Y-%m-%d')
                )
            )
        
    #funtion to know if a page is active (has clicks or has impressions)
    #from a list of URLs or a sitemap
    def active_pages(self,sitemap_url=None, urls=None):
        import numpy as np 
        
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
        
        #get the list of active pages
        sql = f"""
            SELECT 
            url, 
            SUM(impressions) as impressions,
            SUM(clicks) as clicks
            FROM `{self.dataset}.searchdata_url_impression`
            WHERE 
            data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
            {self.filters}
            GROUP BY url
            """
        
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df = pandas_gbq.read_gbq(sql)
            return ( 
                df
                #merge with our list of URLS 
                .merge(
                    urls,
                    left_on = 'url',
                    right_on = 'loc', 
                    #we merge RIGHT 
                    #we just want to check if the page is active
                    #from our initial list of URLs
                    how = 'right'
                )
                .filter(items=['url','clicks','impressions','loc'])
                .assign(
                    active_impression = lambda df_:np.where(df_.url.isna(), False, True), 
                    active_clicks = lambda df_:df_.url.isin(df_.query('clicks>0').url.unique()), 
                    page = lambda df_:df_['url'].fillna(df_['loc'])
                )
                .drop('loc', axis = 1)
                .fillna(0)
            )
        
    
    #inspired by https://github.com/jmelm93/seo_cannibalization_analysis 
    def cannibalization(self, brand_variants):
        
        sql = f"""
            
            WITH raw_data AS (
                SELECT  
                query, 
                url, 
                SUM(clicks) as clicks, 
                SUM(impressions) as impressions
                FROM `{self.dataset}.searchdata_url_impression` 
                WHERE 
                data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
                {self.filters}
                and 
                query is not null
                and 
                NOT regexp_contains(query, "({'|'.join(brand_variants)})")
                group by query, url   
                ), 
            data_per_page AS (
                SELECT 
                url as url_page, 
                SUM(clicks) as clicks_page, 
                SUM(impressions) as impressions_page
                FROM raw_data
                group by url  
                ), 
            data_per_query AS (
                SELECT 
                query as query_query, 
                SUM(clicks) as clicks_query, 
                SUM(impressions) as impressions_query
                FROM raw_data
                group by query  
                ), 
            important_queries AS (
                SELECT 
                raw_data.*, 
                data_per_page.*,
                data_per_query.*, 
                ROUND(100*SAFE_DIVIDE(clicks,clicks_page)) as clicks_pct_page,
                ROUND(100*SAFE_DIVIDE(clicks,clicks_query)) as clicks_pct_query
                from raw_data
                left join data_per_page on data_per_page.url_page = raw_data.url
                left join data_per_query on data_per_query.query_query = raw_data.query
                where 
                ROUND(100*SAFE_DIVIDE(clicks,clicks_page)) >= 10
                AND 
                ROUND(100*SAFE_DIVIDE(clicks,clicks_query)) >= 10
                ), 
            important_queries_with_more_than_one_url AS (
                SELECT 
                query
                from important_queries 
                group by query
                HAVING COUNT(DISTINCT url) >= 2
                ), 
            queries_to_keep AS (
                SELECT 
                important_queries.*
                from important_queries
                inner join important_queries_with_more_than_one_url on important_queries_with_more_than_one_url.query = important_queries.query
                )

            select 
            url, 
            query, 
            impressions, 
            clicks, 
            clicks_page, 
            clicks_query, 
            clicks_pct_page, 
            clicks_pct_query, 
            from queries_to_keep
            order by query asc 

            """
        
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df = pandas_gbq.read_gbq(sql)
            return df 
    
    
    def forecast(self, days):
        from prophet import Prophet
        
        sql = f"""
            SELECT 
            data_date as ds, 
            SUM(clicks) as y
            FROM `{self.dataset}.{self.table_to_use}`
            WHERE 
            data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
            {self.filters}
            GROUP BY ds
            """
        
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df = pandas_gbq.read_gbq(sql)
            m = Prophet()
            m.fit(df)
            future = m.make_future_dataframe(periods=days)
            forecast = m.predict(future)
            return forecast 
    
    
    #brand vs non brand traffic evolution 
    def brand_vs_no_brand(self, brand_variants):
        
        sql = f"""
            WITH brand AS (
                SELECT 
                data_date as date, 
                SUM(clicks) as clicks,
                SUM(impressions) as impressions, 
                FROM `{self.dataset}.searchdata_url_impression`
                WHERE 
                data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
                {self.filters}
                AND 
                REGEXP_CONTAINS(query, {'|'.join(brand_variants)})
            ), 
            no_brand AS (
                SELECT 
                data_date as date, 
                SUM(clicks) as clicks,
                SUM(impressions) as impressions, 
                FROM `{self.dataset}.searchdata_url_impression`
                WHERE 
                data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
                {self.filters}
                AND 
                NOT REGEXP_CONTAINS(query, {'|'.join(brand_variants)})
            )
                
            
            SELECT 
            ISNULL(no_brand.date, brand.date) as date,
            brand.clicks as clicks_brand,
            brand.impressions as impressions_brand,
            no_brand.clicks as clicks_no_brand,
            no_brand.impressions as impressions_no_brand
            from no_brand
            outer join brand on brand.date = no_brand.date
            """
            
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df = pandas_gbq.read_gbq(sql)
            return df.fillna(0)
    
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
        
        sql = f"""
            SELECT 
            query
            FROM `{self.dataset}.searchdata_url_impression`
            WHERE 
            data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
            {self.filters}
            GROUP BY query
            """
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df2 = pandas_gbq.read_gbq(sql)
            return (
                df[df[keyword_column].isin(df2['query'])==False]
            )
        
    
    #causal impact 
    def causal_impact(self, intervention_date = None ):
        
        #we neeed some extra libraries for this method 
        from causalimpact import CausalImpact
        import datetime
        
        #interverntion date must be defined
        if not intervention_date:
            raise ValueError("Intervention_date must be dfined")
        
        sql = f"""
            SELECT 
            data_date as date, 
            SUM(clicks) as clicks
            FROM `{self.dataset}.{self.table_to_use}`
            WHERE 
            data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
            {self.filters}
            GROUP BY date
            """
        
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df = pandas_gbq.read_gbq(sql)
            #calculate the number of days between the last data point and the intervention date 
            days = (pd.to_datetime(df['date']).max() - pd.to_datetime(intervention_date)).days
            #get the prior dates 
            max_date = pd.to_datetime(df['date']).max().strftime("%Y-%m-%d")
            max_before_interenvention = utils.get_date_days_before(intervention_date, days=1)
            min_before_intervention = utils.get_date_days_before(max_before_interenvention, days=days)

            #get the interval for the analysis  
            post_period = [intervention_date, max_date]
            pre_priod = [min_before_intervention, max_before_interenvention]

            #build the ci objec 
            ci = CausalImpact(df.set_index('date').clicks, pre_period = pre_priod, post_period = post_period)
            #return it 
            #the rest of the method are controlled by https://pypi.org/project/pycausalimpact/
            #usually ci.summary() or ci.plot() are enough
            return ci 
    
    
    #fonctions to find potential contents to kill 
    def find_potential_contents_to_kill(self, sitemap_url=None, clicks_threshold = 0, impressions_threshold = 0):

        #check that we have a sitemap 
        if not sitemap_url:
            raise ValueError('Please provide a sitemap_url.')
        
        #download the urle from the sitemap
        urls = pd.DataFrame(utils.get_urls_from_sitemap(sitemap_url), columns=['loc'])
        
        #get the data per page 
        sql = f"""
            SELECT 
            url,  
            SUM(clicks) as clicks,
            SUM(impressions) as impressions
            FROM `{self.dataset}.searchdata_url_impression`
            WHERE 
            data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
            {self.filters}
            GROUP BY url
            """
        
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df = pandas_gbq.read_gbq(sql)
            #return the pages that are in the sitemap but below our thresholds
            return (
                urls
                .merge(
                    df,
                    left_on = 'loc',
                    right_on = 'url',
                    how = 'left'
                )
                .fillna(0)
                .query('clicks <= @clicks_threshold & impressions <= @impressions_threshold')
                .drop('url', axis=1)
            )
        
    
    #change of position ovr time 
    def position_over_time(self):
        
        sql = f"""
            WITH raw_data AS (
                SELECT  
                CAST(ROUND((sum_position/impressions)+1) as string) as position, 
                data_date as date, 
                SUM(clicks) as clicks, 
                SUM(impressions) as impressions,
                COUNT(query) as kw_count
                FROM `{self.dataset}.searchdata_url_impression` 
                WHERE 
                data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}" 
                and 
                query is not null
                {self.filters}
                group by date, position
                order by CAST(position as int) asc
            ) 

            SELECT 
            *
            from raw_data 
            where CAST(position as INT) <=10
            """
        
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df = pandas_gbq.read_gbq(sql)
            return (
                df
                #we create a pivot with position as the x-axis and the yearMonth as the y-axis
                .pivot_table(
                    index = 'position', 
                    columns = 'date', 
                    values = 'kw_count', 
                    aggfunc = 'sum'
                )
            )
        
    
    #function to check if we have pages in GSC that are not in our sitemap
    def pages_not_in_sitemap(self, sitemap_url):
        #list of pages 
        sql = f"""
            SELECT 
            url, 
            SUM(impressions) as impressions,
            SUM(clicks) as clicks
            FROM `{self.dataset}.searchdata_url_impression`
            WHERE 
            data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
            {self.filters}
            GROUP BY url
            """
        
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df = pandas_gbq.read_gbq(sql)
            #check that we have a correct sitemap URL 
            if utils.check_sitemap_url(sitemap_url):
                #download the urle from the sitemap
                urls = pd.DataFrame(utils.get_urls_from_sitemap(sitemap_url), columns=['loc'])
                
                return (
                    df
                    .query('url.isin(@urls.loc)==False')
                )
    
    #function to find winners and losers between two period 
    def winners_losers(self, period_from, period_to):
        from datetime import datetime
        
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
        
        #check that the first element of both list is before the second element
        if datetime.strptime(period_from[1], "%Y-%m-%d") < datetime.strptime(period_from[1], "%Y-%m-%d"):
            raise ValueError('The first element of period from must be before the second element.')
        if datetime.strptime(period_to[1], "%Y-%m-%d") < datetime.strptime(period_to[1], "%Y-%m-%d"):
            raise ValueError('The first element of period from must be before the second element.')
        
        #check that there is no overlap between the two periods
        if datetime.strptime(period_from[1], "%Y-%m-%d") > datetime.strptime(period_to[0], "%Y-%m-%d"):
            raise ValueError('Periods must not overlap.')
        
        #check that the data we provide in df is within the two periods 
        if datetime.strptime(self.dates['startDate'], "%Y-%m-%d") > datetime.strptime(period_from[0], "%Y-%m-%d"):
            raise ValueError('The data in your report is not within the period from.')
        if datetime.strptime(self.dates['endDate'], "%Y-%m-%d") < datetime.strptime(period_to[1], "%Y-%m-%d"):
            raise ValueError('The data in your report is not within the period to.')
        
        #we create two dataframes with the data for each period
        sql_from = f"""
            SELECT 
            url,
            SUM(clicks) as clicks
            FROM `{self.dataset}.searchdata_url_impression`
            WHERE 
            data_date BETWEEN "{period_from[0]}" and "{period_from[1]}"
            {self.filters}
            GROUP BY url
            """
        
        sql_to = f"""
            SELECT 
            url,
            SUM(clicks) as clicks
            FROM `{self.dataset}.searchdata_url_impression`
            WHERE 
            data_date BETWEEN "{period_to[0]}" and "{period_to[1]}"
            {self.filters}
            GROUP BY url
            """
            
        if self.estimate_cost:
            return (calculate_gbq_cost(sql_from, self.client)+calculate_gbq_cost(sql_to, self.client))
        else:
            df_from = pandas_gbq.read_gbq(sql_from)
            df_to = pandas_gbq.read_gbq(sql_to)
        
            return (
            #we marge the two dataframes on the page key 
                df_from
                .merge(
                    df_to,
                    on = 'url',
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
        
        sql = f"""
            SELECT 
            query,
            SUM(clicks) as clicks, 
            SUM(impressions) as impressions
            FROM `{self.dataset}.searchdata_url_impression`
            WHERE 
            data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
            {self.filters}
            AND ARRAY_LENGTH(SPLIT(query, ' ')) >= {number_of_words}
            GROUP BY query
            """
        
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df = pandas_gbq.read_gbq(sql)
            return df 
    
    
    #find outliers based on CTR 
    def find_ctr_outliers(self):
        import numpy as np 
        #first we need to get our ctr curve for our data 
        ctr_yield_curve = self.ctr_yield_curve().filter(items=['position','ctr'])
        #no need to perform all checks here because it would be handled by the
        #ctr_yield_curve() method called just before 
        
        sql = f"""
            WITH raw_data AS (
                SELECT 
                query,
                ROUND((sum_position/impressions)+1) as position, 
                SUM(clicks) as clicks, 
                SUM(impressions) as impressions
                FROM `{self.dataset}.searchdata_url_impression` 
                WHERE 
                data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
                {self.filters}
                and query is not null 
                group by query, position 
                ), 
            data_per_query AS (
                select 
                query, 
                sum(clicks) as clicks_query, 
                sum(impressions) as impressions_query
                from raw_data 
                group by query 
                ),
            weighted_avg_position AS (
                select 
                query, 
                ROUND(SUM(position * impressions) / SUM(position)) AS position
                from raw_data 
                group by query 
                ), 
            ctr_data AS (
                select 
                * 
                from weighted_avg_position
                where position <=10 
                order by position asc
            )

            select 
            ctr_data.query, 
            CAST(ctr_data.position as string) as position, 
            data_per_query.clicks_query, 
            data_per_query.impressions_query, 
            round(data_per_query.clicks_query/data_per_query.impressions_query, 2) as real_ctr
            from ctr_data 
            left join data_per_query on data_per_query.query = ctr_data.query
            """
            
        
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df = pandas_gbq.read_gbq(sql)
        
            return (
                df
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
                    loss = lambda df_:round(df_.impressions_query*(df_.expected_ctr - df_.real_ctr)/100)
                )
                #we order by loss 
                .sort_values(by='loss', ascending=False)
                #we keep only rows where we underperform 
                .query('loss > 0')
            )
            
    
    def abcd(self, metric='clicks', dimensions=['url']):
    #Assign an ABCD class and rank to a metric based on cumulative percentage contribution
    #Based on https://github.com/practical-data-science/ecommercetools/blob/master/ecommercetools/seo/google_search_console.py 
    #even if code is different, the logic is the same
    
        #metric can be either clicks or impressions 
        if metric not in ['clicks', 'impressions']:
            raise ValueError('Metric must be either clicks or impressions.')
        
        #check that the dimensions is a list 
        if not isinstance(dimensions, list):
            raise ValueError('Dimensions must be a list.')
    
        #check that the dimensions is in the list of dimensions
        if not all([dimension in DIMENSIONS_SITE+DIMENSIONS_URL for dimension in dimensions]):
            raise ValueError('One of the dimensions is not valid.')
        
        sql = f"""
            WITH raw_data AS (
                select 
                SUM({metric}) as {metric}, 
                {','.join(dimensions)}
                FROM `{self.dataset}.{self.table_to_use}` 
                WHERE 
                data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
                {self.filters}
                group by {','.join(dimensions)}
            ), 
            cumsum AS (
                select
                {','.join(dimensions)},
                SUM({metric}) OVER (ORDER BY {metric} DESC) AS metric_cumsum
                from raw_data
                group by {metric}, {','.join(dimensions)}
            ), 
            cumsum_pct AS (
                select 
                {','.join(dimensions)},
                metric_cumsum, 
                ROUND(100*metric_cumsum/(select max(metric_cumsum) from cumsum),2) as metric_pct
                from cumsum
            )

            select 
            {','.join(dimensions)},
            metric_pct,
            CASE 
                WHEN metric_pct < 50 THEN 'A'
                WHEN metric_pct < 75 THEN 'B'
                WHEN metric_pct < 90 THEN 'C'
                ELSE 'D'
            END AS abcd
            from cumsum_pct
            
            """
        
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df = pandas_gbq.read_gbq(sql)
            return df
    
    def pages_per_day(self):
        
        sql = f"""
            SELECT 
            data_date as date,
            COUNT(DISTINCT(url)) as page
            FROM `{self.dataset}.searchdata_url_impression`
            WHERE 
            data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
            {self.filters}
            GROUP BY date 
            order by date asc 
            """
        
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df = pandas_gbq.read_gbq(sql)
            return df
    
    
    def pages_lifespan(self):
        
        sql = f"""
            WITH raw_data AS (
                SELECT 
                COUNT(DISTINCT(data_date)) as duration_days,
                url, 
                FROM `{self.dataset}.searchdata_url_impression`
                WHERE 
                data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
                {self.filters}
                GROUP BY url 
            )
            
            select 
            COUNT(url) as pages, 
            duration_days
            from raw_data 
            group by duration_days
            order by duration_days desc
            """
        
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df = pandas_gbq.read_gbq(sql)
            return df
    
    
    def seasonality_per_day(self):
        
        sql = f"""
            SELECT 
            SUM(clicks) AS clicks, 
            SUM(impressions) AS impressions, 
            FORMAT_DATE('%A', data_date) AS date
            FROM `{self.dataset}.{self.table_to_use}`
            WHERE 
            data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
            {self.filters}
            GROUP BY 
            date
            ORDER BY 
            CASE 
                WHEN date = 'Monday' THEN 1
                WHEN date = 'Tuesday' THEN 2
                WHEN date = 'Wednesday' THEN 3
                WHEN date = 'Thursday' THEN 4
                WHEN date = 'Friday' THEN 5
                WHEN date = 'Saturday' THEN 6
                WHEN date = 'Sunday' THEN 7
            END
            """
        
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df = pandas_gbq.read_gbq(sql)
            return df 
    
    
    #inspired by https://www.searchenginejournal.com/big-query-and-gsc-data-content-performance-analysis/508481/ 
    #funtion to get the unique query count per page
    def uqc(self):
        
        sql = f""" 
        
        SELECT 
            url, 
            COUNT(DISTINCT(query)) as uqc
            FROM `{self.dataset}.searchdata_url_impression`
            WHERE 
            data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
            {self.filters}
            and query is not null
            GROUP BY 
            url
            ORDER BY
            uqc DESC
        """
        
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df = pandas_gbq.read_gbq(sql)
            return df 
    
    
    #function to find potential contents to update
    #we use the content decay approach here 
    def find_content_decay(
        self, threshold_decay=0.25,
        metric='clicks',
        threshold_metric=100, 
        type='url', 
        period='week'
        ):
        
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
        if type not in ['url','query']:
            raise ValueError('Type must be either url or query')
        
        if period == 'week': 
            
            sql = f""" 
            
            WITH raw_data AS(
                SELECT 
                {type}, 
                DATE(data_date) as date,
                SUM({metric}) as metric
                FROM `{self.dataset}.searchdata_url_impression` 
                WHERE 
                data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
                {self.filters}
                group by {type}, data_date
                ),
            min_max_date AS (
                SELECT 
                max(date) as max_date, 
                min(date) as min_date  
                from raw_data
                ), 
            last_sunday AS (
                SELECT 
                CASE 
                    WHEN EXTRACT(DAYOFWEEK FROM min_max_date.max_date) = 1 THEN min_max_date.max_date
                    ELSE DATE_TRUNC(min_max_date.max_date, WEEK(SUNDAY))
                    END AS last_sunday, 
                from min_max_date
                ), 
            max_dates AS (
                SELECT 
                last_sunday.last_sunday, 
                DATE_TRUNC(last_sunday.last_sunday, WEEK(MONDAY)) as last_monday
                from last_sunday
                ), 
            first_monday AS (
                SELECT 
                DATE_ADD(
                    min_max_date.min_date,
                    INTERVAL 
                    CASE
                        WHEN EXTRACT(DAYOFWEEK FROM min_max_date.min_date) = 1 THEN 1 
                        WHEN EXTRACT(DAYOFWEEK FROM min_max_date.min_date) = 2 THEN 7
                        WHEN EXTRACT(DAYOFWEEK FROM min_max_date.min_date) = 3 THEN 6 
                        WHEN EXTRACT(DAYOFWEEK FROM min_max_date.min_date) = 4 THEN 5 
                        WHEN EXTRACT(DAYOFWEEK FROM min_max_date.min_date) = 5 THEN 4
                        WHEN EXTRACT(DAYOFWEEK FROM min_max_date.min_date) = 6 THEN 3 
                        WHEN EXTRACT(DAYOFWEEK FROM min_max_date.min_date) = 7 THEN 2 
                    END DAY
                ) AS first_monday
                FROM min_max_date
                ), 
            min_dates AS (
                SELECT 
                first_monday.first_monday, 
                DATE_ADD(first_monday.first_monday, INTERVAL 6 DAY) as first_sunday
                from first_monday
                ), 
            raw_data_within_period AS (
                SELECT 
                {type}, 
                CASE 
                    WHEN EXTRACT(ISOWEEK from date) >= 10 THEN CONCAT(EXTRACT(YEAR from date),"-",EXTRACT(ISOWEEK from date))
                    ELSE CONCAT(EXTRACT(YEAR from date),"-0",EXTRACT(ISOWEEK from date))
                    END as date_period, 
                SUM(metric) as metric
                from raw_data 
                where date BETWEEN (select first_monday from min_dates) and (select last_sunday from max_dates)
                group by url, date_period
                ), 
            data_rank AS (
                SELECT 
                {type}, 
                date_period, 
                metric, 
                RANK () OVER (PARTITION BY {type} order by metric desc) as rank
                from raw_data_within_period
                ), 
            data_current AS (
                SELECT 
                {type}, 
                date_period, 
                metric, 
                from raw_data_within_period 
                where date_period = (select max(date_period) from raw_data_within_period)
                ), 
            final_data AS (
                select 
                data_current.{type}, 
                data_current.metric as metric_last_period, 
                data_rank.metric as metric_max, 
                data_rank.date_period as period_max, 
                IF(data_current.metric = 0, 100, round(1-data_current.metric/data_rank.metric,3)) as decay,
                (data_rank.metric-data_current.metric) as decay_abs
                from data_current
                left join data_rank on data_rank.{type} = data_current.{type}
                where data_rank.rank = 1 
                order by decay_abs desc
            )
            
            select 
            * 
            from final_data 
            where 
            decay_abs >= {threshold_metric}
            and 
            decay >= {threshold_decay}
            
            """
        
        if period == 'month':
            
            sql = f""" 
            
            WITH raw_data AS(
                SELECT 
                {type}, 
                DATE(data_date) as date,
                SUM({metric}) as metric
                FROM `{self.dataset}.searchdata_url_impression` 
                WHERE 
                data_date BETWEEN "{self.dates['startDate']}" and "{self.dates['endDate']}"
                {self.filters}
                group by {type}, data_date
                ),
            min_max_date AS (
                SELECT 
                max(date) as max_date, 
                min(date) as min_date  
                from raw_data
                ), 
            max_dates AS (
                SELECT 
                CASE 
                    WHEN last_day(max_date) = max_date then max_date 
                    ELSE DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 1 DAY)
                END as last_day, 
                from min_max_date
                ), 
            min_dates AS (
                SELECT 
                CASE 
                    WHEN DATE_TRUNC(min_date, MONTH) = min_date then min_date 
                    ELSE DATE_TRUNC(DATE_ADD(min_date, INTERVAL 1 MONTH), MONTH)
                END As first_day, 
                from min_max_date
                ),
            raw_data_within_period AS (
                SELECT 
                {type}, 
                CASE 
                    WHEN EXTRACT(MONTH from date) >= 10 THEN CONCAT(EXTRACT(YEAR from date),"-",EXTRACT(MONTH from date))
                    ELSE CONCAT(EXTRACT(YEAR from date),"-0",EXTRACT(MONTH from date))
                    END as date_period, 
                SUM(metric) as metric
                from raw_data 
                where date BETWEEN (select first_day from min_dates) and (select last_day from max_dates)
                group by {type}, date_period
                ), 
            data_rank AS (
                SELECT 
                {type}, 
                date_period, 
                metric, 
                RANK () OVER (PARTITION BY {type} order by metric desc) as rank
                from raw_data_within_period
                ), 
            data_current AS (
                SELECT 
                {type}, 
                date_period, 
                metric, 
                from raw_data_within_period 
                where date_period = (select max(date_period) from raw_data_within_period)
                ), 
            final_data AS (
                select 
                data_current.{type}, 
                data_current.metric as metric_last_period, 
                data_rank.metric as metric_max, 
                data_rank.date_period as period_max, 
                IF(data_current.metric = 0, 100, round(1-data_current.metric/data_rank.metric,3)) as decay,
                (data_rank.metric-data_current.metric) as decay_abs
                from data_current
                left join data_rank on data_rank.{type} = data_current.{type}
                where data_rank.rank = 1 
                order by decay_abs 
                )

            select 
            * 
            from final_data 
            where 
            decay_abs >= {threshold_metric}
            and 
            decay >= {threshold_decay}
            
            """
        
        
        if self.estimate_cost:
            return calculate_gbq_cost(sql, self.client)
        else:
            df = pandas_gbq.read_gbq(sql)
            return df 