import pandas as pd

class Sitemap: 
    def __init__(self, service, webproperty):
        self.service = service
        self.url = webproperty

    def list_sitemaps(self):
        return (
            pd
            .DataFrame(
                self
                .service
                .sitemaps()
                .list(siteUrl=self.url)
                .execute()
                ['sitemap']
            )
        )
        
    def check_sitemaps(self):
        import requests 
        sitemaps = self.list_sitemaps()
        if len(sitemaps) == 0:
            raise ValueError('No sitemaps found for this property.')
        
        #loop over the sitemaps and get the response code in our sitemaps df 
        sitemaps['response_code'] = (
            sitemaps['path']
            .apply(
                lambda x: 
                    requests.get(x).history[0].status_code if len(requests.get(x).history) > 0 
                    else requests.get(x).status_code
            )
        )
        
        return sitemaps[['path','response_code']]