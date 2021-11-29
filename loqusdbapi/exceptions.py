class LoqusdbAPIError(Exception):
    def __init__(self, message: str = ""):
        super(LoqusdbAPIError, self).__init__()
        self.message = message


class VCFParserError(LoqusdbAPIError):
    """Raise when provided VCF is malformed"""
