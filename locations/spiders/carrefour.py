import scrapy
from urllib import parse
import requests
from locations.items import GeojsonPointItem


MAPQUEST_KEY = 'ybe4KeKi8ACKY0eVqJXAw2QxTKnxnor8'

MAPQ = 'http://www.mapquestapi.com/geocoding/v1/address?'

HEADERS = {
    'origin': 'https://www.carrefour.com.ar',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'en-US,en;q=0.8,ru;q=0.6',
    'content-type': 'application/x-www-form-urlencoded',
    'referer': 'https://www.carrefour.com.ar/storelocator/index',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'

}


class CarreFourSpider(scrapy.Spider):

    name = "carrefour"
    allowed_domains = ["www.carrefour.com.ar", 'www.mapquestapi.com', ]
    download_delay = 1.5
    start_urls = (
        'https://www.carrefour.com.ar/storelocator/index/search/',
        'https://www.carrefour.com.ar/storelocator',
    )

    def norm_time(self, timetable):
        return ''

    def parse(self, response):
        data = response.xpath(
            '//div[@class="storelocator_results scroll-pane"]/div')

        for result, item, detail in zip(*[iter(data)]*3):
            opening_hours = self.norm_time(detail.xpath('.//div[@class="timetable"]'))

            props = {
                'ref': result.xpath('.//a[@href="#showmarker"]/text()').extract_first(),
                'website': 'https://' + self.allowed_domains[0] + result.xpath('.//a[@class="folletos"]/@href').extract_first(),
                'addr_full': result.xpath('.//div[@class="address"]/text()').extract_first(),
                'city': result.xpath('.//div[@class="region"]/text()').extract_first(),
                'phone': result.xpath('normalize-space(.//div[@class="tel"]/text())').extract_first(),
                'lat': float(item.xpath('.//div[@class="geodata"]/@data-lat').extract_first()),
                'lon': float(item.xpath('.//div[@class="geodata"]/@data-lng').extract_first()),
                'opening_hours': opening_hours
            }

            return GeojsonPointItem(**props)

    def parse_regions(self, response):
        regions = response.xpath('//select[@id="region-desktop"]/option/text()').extract()

        for region in regions:

            location = '%s, Argentina' % region
            params = [('key', MAPQUEST_KEY), ('location', location)]
            url = MAPQ + parse.urlencode(params)
            data = requests.get(url).json()

            if data.get('results', {}):
                lat, lng = data['results'][0]['locations'][0]['latLng'].values()
                lat_lng = '{},{}'.format(lat, lng)
                params = {'search[type]': 'address', 'search[geocode]': lat_lng,
                          'search[address]': location, 'country': 'AR'
                          }
                yield scrapy.http.FormRequest(url=self.start_urls[0], formdata=params,
                                              headers=HEADERS, callback=self.parse)

    def start_requests(self):
        yield scrapy.Request(url=self.start_urls[1], callback=self.parse_regions)
