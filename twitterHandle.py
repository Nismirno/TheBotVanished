from tweepy import OAuthHandler
from tweepy import Cursor
from tweepy.api import API
from tweepy.error import TweepError
import json
import logging


logger = logging.getLogger("twitter")
logger.setLevel(logging.INFO)

handler = logging.FileHandler(filename="twitter.log",
                              encoding="utf-8",
                              mode='w')
handler.setFormatter(
    logging.Formatter(
        "%(asctime)s:%(levelname)s:%(name)s %(message)s"))
logger.addHandler(handler)


class TwitterHandle():
    def __init__(self, dataFile="data.json"):
        with open(dataFile) as f:
            data = json.load(f)["Twitter"]

        CONSUMER_KEY = data["consumer-key"]
        CONSUMER_SECRET = data["consumer-secret"]
        ACCESS_TOKEN = data["access-token"]
        ACCESS_TOKEN_SECRET = data["access-token-secret"]

        auth = OAuthHandler(CONSUMER_KEY,
                            CONSUMER_SECRET)
        auth.set_access_token(ACCESS_TOKEN,
                              ACCESS_TOKEN_SECRET)
        self.api = API(auth)

    def getTweet(self, **kwargs):
        if "statusID" in kwargs:
            statusID = kwargs["statusID"]
            try:
                status = self.api.get_status(
                    statusID, tweet_mode="extended")
                return status._json
            except TweepError as err:
                errMsg = err.args[0][0]["message"]
                logger.warning(errMsg)
                return errMsg
        if "userID" not in kwargs:
            logger.warning("User ID must be specified")
            return "Missing user"
        iTweet = int(kwargs.get("iTweet", 0))
        maxTweets = kwargs.get("maxTweets", 20)
        if iTweet > maxTweets:
            logger.warning(f"Can't get tweet from before \
{maxTweets} last tweets")
            return f"Please use number between 1 and {maxTweets}"
        userID = kwargs.get("userID")
        statuses = []
        nStatuses = 0
        for status in Cursor(
                self.api.user_timeline,
                id=userID,
                tweet_mode="extended").items(maxTweets):
            statuses.append(status)
        return statuses[iTweet]._json

    pass
