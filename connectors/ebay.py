from connectors.live_market import LiveMarketConnector


class EbayConnector(LiveMarketConnector):
    def __init__(self, fetcher=None):
        super().__init__("ebay", fetcher)
