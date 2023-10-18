A tool to mass-delete tweets
============================

This tool uses a (as of now) not ratelimited API on Twitter/X to delete all you tweets before
you say goodbye to this hellhole.

To use this tool you need two things:

### Archive of your tweets

You can request this archive by going to
Settings -> Your Account -> Download an archive of your data. When you receive this archive it
will contain a file `data/tweets.js` that you need for this tool.

### Authdata from Twitter/X

You need authentication data for this tool to work. To get this you will need to use the _Inspect_ Tool
of your browser (For Firefox it is under Tools -> Browser Tools -> Web Developer Tools).
Go to the Twitter homepage and open the tool on the _Network_ Page. Then reload the Twitter homepage.
You should see a lot of requests. Look for requests of the type `xhr`. When you find one click on it
and on the right side you should see a tab with the headers of the request. The authentication data is
under `Response Headers`. You need three header lines to make this tool work, `x-csrf-token`, `authorization`
and `cookie`.

Copy all three of these into a textfile. It should look something like this:

```text
x-csrf-token: 8a1999b9ba[...]
authorization: Bearer AAAAAAAAAAAAAAAAAAAAANRI[...]
Cookie: guest_id=v1%[...]
```

Now you can run the tool and it will start deleting your tweets. It will save its current state to
an `cache.json` file in the same directory as the tool.

To set it up in a python virtual environment and run it, just do this:

```shell
$ python3 -m venv venv
$ source venv/bin/activate
(venv) $ pip install -U pip wheel
(venv) $ pip install -r requirements.txt
(venv) $ python3 ./deltweet.py -t twitter-archive/data/tweets.js -a twitter-auth.txt
2023-10-18 17:54:49,570 - DelTweet._setup_tweets - INFO - Loaded 31209 tweets
2023-10-18 17:54:49,595 - DelTweet._setup_tweets - INFO - Setup 31209 tweets with 15702 already deleted
2023-10-18 17:54:49,638 - DelTweet.delete_tweet - INFO - Deleting tweet 7748268540821504
2023-10-18 17:54:49,943 - DelTweet.delete_tweet - INFO - Deleting tweet 1456910654066118658
2023-10-18 17:54:50,118 - DelTweet.delete_tweet - INFO - Deleting tweet 1598813283816980482
```

Just let it run, it can take a few hours depending on the amount of tweets. You can stop it by
pressing `CTRL-C` and it  will resume where it was when you start it the next time.
