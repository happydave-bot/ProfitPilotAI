from connectors.live_market import LiveMarketConnector


class AmazonConnector(LiveMarketConnector):
    def __init__(self, fetcher=None):
        super().__init__("amazon", fetcher)
