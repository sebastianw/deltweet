from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import uuid
from enum import IntEnum
from pathlib import Path

import requests

root_log = logging.getLogger("deltweet")
root_log.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
fmt = logging.Formatter("%(asctime)s - %(classInfo)s%(funcName)s - %(levelname)s - %(message)s")
ch.setFormatter(fmt)
root_log.addHandler(ch)
log = logging.LoggerAdapter(root_log, dict(classInfo=""))


# To use logger in classes use something like:
# self.log = logging.LoggerAdapter(root_log, dict(classInfo=f"{self.__class__.__name__}({name})."))


class DelTweetException(Exception):
    pass


class TweetStatus(IntEnum):
    OK = 1
    DELETED = 2


class DelTweet:
    def __init__(self, tweetfile: str, authfile: str, cachefile: str = None):
        self.log = logging.LoggerAdapter(root_log, dict(classInfo=f"{self.__class__.__name__}."))
        if cachefile:
            self.cache_file = Path(cachefile)
        else:
            self.cache_file = Path(__file__).resolve().parent / "cache.json"
        self.session = requests.session()
        self._setup_session(authfile)
        self.tweetstatus = {}
        self._load_cache()
        self._setup_tweets(tweetfile)
        signal.signal(signal.SIGINT, self._signalhandler)

    def _load_cache(self):
        if not self.cache_file.exists():
            self.log.debug(f"Cache {self.cache_file} does not exist")
            return
        self.log.debug(f"Loading cache from {self.cache_file}")
        try:
            self.tweetstatus.update(json.loads(self.cache_file.read_text()))
        except json.JSONDecodeError:
            backup_file = self.cache_file.rename(f"{self.cache_file.name}.{uuid.uuid4()}")
            self.log.warning(f"Cache is invalid, moving file to {backup_file}")

    def _save_cache(self):
        self.log.debug(f"Saving state to cache file {self.cache_file}")
        with open(self.cache_file, "w") as cf:
            json.dump(self.tweetstatus, cf)

    def _signalhandler(self, signalnum, stack):
        self.log.info(f"Interrupted with signal {signalnum}. Saving cache and exiting...")
        self._save_cache()
        sys.exit(0)

    def _setup_session(self, authfile: str):
        authdata = {}
        with open(authfile, "r") as af:
            lines = af.readlines()
            for line in lines:
                kv: list[str, str] = line.split(":", 1)
                authdata[kv[0].lower()] = kv[1].strip()
        self.log.debug(authdata)
        for required in ["x-csrf-token", "authorization", "cookie"]:
            if required not in authdata:
                self.log.error(f"Missing {required} filed in {authfile}")
                raise DelTweetException(f"Missing {required} filed in {authfile}")
        self.session.headers.update(authdata)

    def _setup_tweets(self, tweetfile: str):
        jsdata = Path(tweetfile).read_text(encoding="UTF-8")
        jsonstart = jsdata.find("[")
        jsondata = json.loads(jsdata[jsonstart:])
        self.log.info(f"Loaded {len(jsondata)} tweets")
        loaded_tweetids = set()
        cache_tweetids = set(self.tweetstatus.keys())
        for tweet in jsondata:
            loaded_tweetids.add(tweet["tweet"]["id_str"])
        obsoleted_cached_ids = cache_tweetids - loaded_tweetids
        self.log.debug(
            f"{len(obsoleted_cached_ids)} Tweet IDs in cache but not in loaded archive. Deleting from cache."
        )
        for tid in obsoleted_cached_ids:
            del self.tweetstatus[tid]
        for tid in loaded_tweetids:
            self.tweetstatus[tid] = self.tweetstatus.get(tid, TweetStatus.OK)
        already_deleted = len([tid for tid, status in self.tweetstatus.items() if status == TweetStatus.DELETED])
        self.log.info(f"Setup {len(self.tweetstatus)} tweets with {already_deleted} already deleted")

    def _stats(self) -> tuple[int, int, int]:
        """Return a tuple of all tweets, already deleted and still to be deleted"""
        already_deleted = len([tid for tid, status in self.tweetstatus.items() if status == TweetStatus.DELETED])
        return len(self.tweetstatus), already_deleted, len(self.tweetstatus) - already_deleted

    def delete_tweet(self, tid: str) -> bool:
        self.log.info(f"Deleting tweet {tid}")
        data = {"variables": {"tweet_id": tid, "dark_request": False}, "queryId": "VaenaVgh5q5ih7kvyVjgtg"}
        response = self.session.post("https://twitter.com/i/api/graphql/VaenaVgh5q5ih7kvyVjgtg/DeleteTweet", json=data)
        if response.status_code != 200:
            self.log.warning(f"Could not delete {tid}: {response.text}")
            return False
        self.tweetstatus[tid] = TweetStatus.DELETED
        return True

    def run(self):
        counter = 0
        for tid, status in self.tweetstatus.items():
            if status == TweetStatus.DELETED:
                continue
            self.delete_tweet(tid)
            counter += 1
            if not counter % 100:
                self._save_cache()
            if not counter % 1000:
                stats = self._stats()
                self.log.info(f"Total {stats[0]} tweets, {stats[1]} deleted, {stats[2]} to go")
        self._save_cache()


def main() -> None:
    p = argparse.ArgumentParser(description="Delete all Tweets on TwiXXer")
    p.add_argument("-d", "--debug", action="store_true")
    p.add_argument(
        "-t", "--tweetsjs", metavar="tweets.js", help="Path to tweets.js file from Twitter Archive", required=True
    )
    p.add_argument(
        "-a",
        "--authdata",
        metavar="authdata.txt",
        help="Path to authentication headers from Twitter (Inspect requests to API)",
        required=True,
    )
    args = p.parse_args()
    if args.debug:
        log.setLevel(logging.DEBUG)
    log.debug("Starting")
    d = DelTweet(args.tweetsjs, args.authdata)
    d.run()


if __name__ == "__main__":
    main()
