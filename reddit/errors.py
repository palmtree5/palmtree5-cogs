class NoAccessTokenError(Exception):
    pass


class RedditAPIError(Exception):
    pass


class NotFoundError(RedditAPIError):
    pass


class AccessForbiddenError(RedditAPIError):
    pass
