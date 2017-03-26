#!/home/dude/anaconda3/bin/python
import praw
import time
import re
import requests
import json
import sqlite3
import logging
import configparser

config = configparser.ConfigParser()
config.readfp(open(r'config.ini'))


# Bot Configs
YOUTUBE = config.get('YOUTUBE', 'YOUTUBE_API_KEY')
APIURL = "https://www.googleapis.com/youtube/v3/videos?part=contentDetails&key=" + YOUTUBE + "&id="
SLEEPTIME = int(config.get('SLEEPTIME', 'TIME'))


logging.basicConfig(
    format = '[%(asctime)s] %(levelname)s: %(name)s: %(message)s',
    filename = config.get('LOGGING', 'LOG_FILENAME'),
level=logging.INFO)

logging.info('Starting timestamp reddit bot.')

# Initalize & Connect to database to keep track of processed comments
sql = sqlite3.connect(config.get('DATABASE', 'DB_FILENAME'))
cur = sql.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS timestamp(id TEXT, childid TEXT)')
cur.execute('CREATE INDEX IF NOT EXISTS postindex on timestamp(id)')
logging.info('Connected to database.')
# Subreddits to targets
subreddit = json.loads(config.get('SUBREDDITS', 'SUBREDDIT_LIST'))

reddit = praw.Reddit(client_id=config.get('PRAW_DETAILS', 'CLIENT_ID'),
                     client_secret=config.get('PRAW_DETAILS', 'CLIENT_SECRET'),
                     password=config.get('PRAW_DETAILS', 'BOT_PASSWORD'),
                     user_agent=config.get('PRAW_DETAILS', 'USERAGENT'),
                     username=config.get('PRAW_DETAILS', 'BOT_USERNAME'))

# Regex to match when parsing comments for youtube video link & numeric timestamp
pattern = re.compile("(?:youtube\.com/watch\?v=|youtu.be/)([0-9A-Za-z\-_]*)")
timepattern = re.compile("(\d{1,2}[\:|\ |\-]\d{1,2}([\:|\ |\-]\d{1,2}]?)?)")

# Save processed comments on database to avoid processing them again
def addToDatabase(id, childid):
    logging.info('Added to database :'+ id)
    cur.execute('INSERT INTO timestamp VALUES(?, ?)', [id, childid])
    sql.commit()

# Check if targeted comment has been already replied by our bot
def isinDatabase(id):
    cur.execute('SELECT * FROM timestamp WHERE id == ?', [id])
    item = cur.fetchone()
    return (item is not None)

# Parse time from extracted comments
def parsetime(timenum):
    if type(timenum) is tuple:
        timenum = ''.join(timenum[0])
    timenum = timenum.replace(' ',':')
    timenum = timenum.replace('-',':')
    timenum = timenum.split(":")
    timenum = [int(str(times)) for times in timenum]
    if(len(timenum)==1):
        timenum = [0,0] + timenum
    if(len(timenum)==2):
        timenum = [0] + timenum
    return timenum

# Get length of a youtube video from youtube api
def getLength(url):
    url = APIURL + url
    try:
        length =  (requests.get(url).json()['items'][0]['contentDetails']['duration'])
        length = length.replace('PT','')
        length = length.replace('H',':')
        length = length.replace('M',':')
        length = length.replace('S','')
        length = length.split(":")
        length = [int(str(splitLength)) for splitLength in length]
        if(len(length)==1):
            length = [0,0] + length
        if(len(length)==2):
            length = [0] + length
    except:
        length = [0,0,0]
    return length

# Check if the requested timestamp value is lesser than youtube video's lenght before replying
def validate(total,timestamp):
    return ((total[2]*3600 + total[1]*60 + total[0])>(timestamp[2]*3600+ timestamp[1]*60 + timestamp[0]))


# Return a comment to be replied
def createComment(id,time):
    timestamp = str(time[0]) + "h" + str(time[1]) + "m" + str(time[2]) + "s"
    logging.info('Comment created for id:'+ id + "on time: "+ str(time))
    return "https://www.youtube.com/watch?v=" + id + "&t=" + timestamp + "\n \n Reddit Timestamp Bot: [Source Code](https://github.com/ankitgyawali/reddit-timestamp-bot) "

# Main
for submission in reddit.subreddit("+".join(subreddit)).rising(limit=int(config.get('SUBREDDITS', 'SUBMISSIONS_TO_PROCESS'))):
    if (isinDatabase(submission.id)):
        continue
    for comment in submission.comments:
        if isinstance(comment, praw.models.MoreComments): # Bypass for prototype //comment.body & comment.replies
            continue
        if (isinDatabase(comment.id)):
            continue
        if (len(pattern.findall(submission.url)) == 1) and len(timepattern.findall(comment.body)) ==1:
            if(validate(getLength(pattern.findall(submission.url)[0]), parsetime(timepattern.findall(comment.body)[0]))):
                # Make comment and add to db
                comment.reply(createComment(pattern.findall(submission.url)[0],parsetime(timepattern.findall(comment.body)[0])))
                # print(createComment(pattern.findall(submission.url)[0],parsetime(timepattern.findall(comment.body)[0])))                
                time.sleep(SLEEPTIME)
                addToDatabase(submission.id, comment.id)
            continue
        else:
            for sub_comment in comment.replies:
                if isinstance(sub_comment, praw.models.MoreComments):
                    continue
                if (isinDatabase(sub_comment.id)):
                    continue
                if (len(pattern.findall(comment.body)) == 1) and len(timepattern.findall(sub_comment.body)) ==1:
                    if(validate(getLength(pattern.findall(comment.body)[0]), parsetime(timepattern.findall(sub_comment.body)[0]))):
                        # Make comment and add to db
                        sub_comment.reply(createComment(pattern.findall(comment.body)[0],parsetime(timepattern.findall(sub_comment.body)[0])))
                        # print(createComment(pattern.findall(comment.body)[0],parsetime(timepattern.findall(sub_comment.body)[0])))
                        addToDatabase(comment.id,sub_comment.id)
                        time.sleep(SLEEPTIME)
                    continue
logging.info('Finished processing submission batch')