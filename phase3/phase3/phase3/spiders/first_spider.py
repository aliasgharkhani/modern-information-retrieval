import scrapy
import random
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError
import re
from ..items import Phase3Item


class firstSpider(scrapy.Spider):
    name = "first"
    allowed_domain = "https://www.semanticscholar.org/"

#     start_urls = [
#         "https://www.semanticscholar.org/paper/The-Lottery-Ticket-Hypothesis%3A-Training-Pruned-Frankle-Carbin/f90720ed12e045ac84beb94c27271d6fb8ad48cf",
#         "https://www.semanticscholar.org/paper/Attention-is-All-you-Need-Vaswani-Shazeer/204e3073870fae3d05bcbc2f6a8e263d9b72e776",
#         "https://www.semanticscholar.org/paper/BERT%3A-Pre-training-of-Deep-Bidirectional-for-Devlin-Chang/df2b0e26d0599ce3e70df8a9da02e51594e0e992"
#     ]
    counter = 0
    visited_links = {
        "https://www.semanticscholar.org/paper/BERT%3A-Pre-training-of-Deep-Bidirectional-for-Devlin-Chang/df2b0e26d0599ce3e70df8a9da02e51594e0e992",
        "https://www.semanticscholar.org/paper/The-Lottery-Ticket-Hypothesis%3A-Training-Pruned-Frankle-Carbin/f90720ed12e045ac84beb94c27271d6fb8ad48cf",
        "https://www.semanticscholar.org/paper/Attention-is-All-you-Need-Vaswani-Shazeer/204e3073870fae3d05bcbc2f6a8e263d9b72e776",
        
    }

#     links = start_urls.copy()

    def parse(self, response):
        item = Phase3Item()
        print('\n\n\n', len(self.visited_links), '\n\n\n')
        self.counter += 1
        item['id'] = response.url.split('/')[-1]
        #try:
            #item['id'] = re.findall('\d+', response.css("ul.paper-meta.paper-detail__paper-meta-top span::text").get())[0]
        #except IndexError:
            #item['id'] = re.findall('\d+', response.css("ul.paper-meta.paper-detail__paper-meta-top span")[1].css("::text").get())[0]
        
        item['title'] = response.css("h1::text").get()
        
        item['authors'] = []
        a = response.css("span.author-list")[0]
        for i in a.css("a.author-list__link.author-list__author-name"):
            item['authors'].append(i.css("span span::text").get())
        
        try:
            li = response.css("li.paper-meta-item")[1]
            span = li.css("span")[3]
            item['date'] = span.css("::text").get()
        except:
            print('years problem!!!!!!!!!!!!!!!!!!!!!!!!\n\n\n\n')
            item['date'] = 0
        
        item['abstract'] = response.css("div.text-truncator.abstract__text.text--preline::text").get()
        if item['abstract'] == None:
            item['abstract'] = response.css("span.text-truncator.abstract__text.text--preline::text").get()
        
        
        
        references_links = []
        references = []
        try:
            all_references_links = response.css("div#references div.paper-citation")
            random_references_links = random.choices(all_references_links, k=10)

            for i in random_references_links:
                references_links.append(i.css("a").attrib['href'])
                references.append(i.css("a").attrib['href'].split('/')[-1])
        except:
            print('references problem!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n\n')
        item['references'] = references
            
        yield item

        if len(self.visited_links) > self.limit:
            print('\n\n\n ended \n\n\n')
            raise StopIteration
        else:
            for reference_link in references_links:
                if self.allowed_domain + reference_link not in self.visited_links:
                    self.visited_links.add(self.allowed_domain + reference_link)
                    yield response.follow(reference_link, callback=self.parse)

    # def parse_dir_contents(self, response):
    #     for sel in response.xpath('//ul/li'):
    #         item = DmozItem()
    #         item['title'] = sel.xpath('a/text()').extract()
    #         item['link'] = sel.xpath('a/@href').extract()
    #         item['desc'] = sel.xpath('text()').extract()
    #         yield item

    def errback_httpbin(self, failure):
        # log all errback failures,
        # in case you want to do something special for some errors,
        # you may need the failure's type
        self.logger.error(repr(failure))

        # if isinstance(failure.value, HttpError):
        if failure.check(HttpError):
            # you can get the response
            response = failure.value.response
            self.logger.error('HttpError on %s', response.url)

        # elif isinstance(failure.value, DNSLookupError):
        elif failure.check(DNSLookupError):
            # this is the original request
            request = failure.request
            self.logger.error('DNSLookupError on %s', request.url)

        # elif isinstance(failure.value, TimeoutError):
        elif failure.check(TimeoutError):
            request = failure.request
            self.logger.error('TimeoutError on %s', request.url)
