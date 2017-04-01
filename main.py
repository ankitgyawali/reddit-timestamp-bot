#!/home/dude/anaconda3/bin/python
import praw
import time
import re
import requests
import json
import sqlite3
import logging
import configparser
import pyjokes

config = configparser.ConfigParser()
config.readfp(open(r'config.ini'))

# Bot Configs
YOUTUBE = config.get('YOUTUBE', 'YOUTUBE_API_KEY')
APIURL = "https://www.googleapis.com/youtube/v3/videos?fields=items(id,statistics(likeCount,dislikeCount),contentDetails(duration),snippet(title,channelTitle))&part=snippet,statistics,contentDetails&key=" + YOUTUBE + "&id="
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


reddit = praw.Reddit(client_id=config.get('PRAW_DETAILS', 'CLIENT_ID'),
                     client_secret=config.get('PRAW_DETAILS', 'CLIENT_SECRET'),
                     password=config.get('PRAW_DETAILS', 'BOT_PASSWORD'),
                     user_agent=config.get('PRAW_DETAILS', 'USERAGENT'),
                     username=config.get('PRAW_DETAILS', 'BOT_USERNAME'))

# Regex to match when parsing comments for youtube video link & numeric timestamp
pattern = re.compile("(?:youtube\.com/watch\?v=|youtu.be/)([0-9A-Za-z\-_]*)")
timepattern = re.compile("(\d{1,2}[\:]\d{1,2}([\:]\d{1,2}]?)?)")

# Save processed comments on database to avoid processing them again
def addToDatabase(id, childid):
    logging.info('Added to database :'+ id)
    cur.execute('INSERT INTO timestamp VALUES(?, ?)', [id, childid])
    sql.commit()

# Check if targeted comment has been already replied by our bot
def isinDatabase(id):
    cur.execute('SELECT * FROM timestamp WHERE id == ?', [id])
    item = cur.fetchone()
    if(item is not None):
        logging.info('ID: '+ str(id)+ " found in db!")
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
        videoDetails = requests.get(url).json()
        length =  (videoDetails['items'][0]['contentDetails']['duration'])
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
        videoDetails = None
    return [length, videoDetails]

# Check if the requested timestamp value is lesser than youtube video's lenght before replying
def validate(total,timestamp):
    if(total[1] is None):
        logging.info('Something is wrong with youtube API')
        return False
    else:
        return ((total[0][0]*3600 + total[0][1]*60 + total[0][2])>(timestamp[0]*3600+ timestamp[1]*60 + timestamp[2]))


# Return a comment to be replied
def createComment(videoDetails,time):
    popularity = (int(videoDetails['items'][0]['statistics']['likeCount'])+1)/ ((int(int(videoDetails['items'][0]['statistics']['likeCount']))) + (int(int(videoDetails['items'][0]['statistics']['dislikeCount'])))+1) *100
    timestamp = str(time[0]) + "h" + str(time[1]) + "m" + str(time[2]) + "s"
    logging.info('Comment created for id:'+ videoDetails['items'][0]['id'] + "on time: "+ str(time))
    response = "[ **Jump to "
    if(int(time[0]) != 0):
        response +=  str(time[0]) + ":" + str(time[1]) + ":" + str(time[2])
    else:
        response += str(time[1]) + ":" + str(time[2])
    response += " @** "
    if(len(videoDetails['items'][0]['snippet']['title']) < 81):
        response += videoDetails['items'][0]['snippet']['title']
    else:
        response += "Referenced Video"
    response += "](https://www.youtube.com/watch?v="+ (videoDetails['items'][0]['id']) + "&t=" + timestamp + ")"
    response += "\n \n ^(Video Popularity: " + str("{0:.2f}".format(popularity))+"%"
    response += ", Channel Name: " + str(videoDetails['items'][0]['snippet']['channelTitle']) + ") \n \n"
    response += "----------------------------------------------------------------------------- \n \n "
    response += "^(" + pyjokes.get_joke("en","all").replace('(','[').replace(')',']') + ") \n \n"
    response += "##**^^Beep ^^Bop, ^^I'm ^^a ^^Time ^^Stamp ^^Bot!** [^^Source ^^Code](https://github.com/ankitgyawali/reddit-timestamp-bot)"
    return response

def processABatch(batchSubmissions):
    for submission in batchSubmissions:
        if (isinDatabase(submission.id)):
            continue
        for comment in submission.comments:
            
            if isinstance(comment, praw.models.MoreComments): # Bypass for prototype //comment.body & comment.replies
                continue
            if (isinDatabase(comment.id)):
                continue
            if (len(pattern.findall(submission.url)) == 1) and ((len(timepattern.findall(comment.body)) ==1) and ("youtube.com" not in comment.body) and (("youtu.be" not in comment.body))):
                if(validate(getLength(pattern.findall(submission.url)[0]), parsetime(timepattern.findall(comment.body)[0]))):
                    # Make comment and add to db
                    try:
                        comment.reply(createComment(getLength(pattern.findall(submission.url)[0])[1],parsetime(timepattern.findall(comment.body)[0])))
                        addToDatabase(comment.id,submission.id)
                    except Exception as e:
                        logging.info('Error occurred while comenting, check logs: '+ str(e))
                    # print(createComment(getLength(pattern.findall(submission.url)[0])[1],parsetime(timepattern.findall(comment.body)[0])))              
                    time.sleep(SLEEPTIME)
                continue
            else:
                for sub_comment in comment.replies:
                    if isinstance(sub_comment, praw.models.MoreComments):
                        continue
                    if (isinDatabase(sub_comment.id)):
                        continue
                    if (len(pattern.findall(comment.body)) == 1) and ((len(timepattern.findall(sub_comment.body)) ==1) and ("youtube.com" not in sub_comment.body) and (("youtu.be" not in sub_comment.body))):
                        if(validate(getLength(pattern.findall(comment.body)[0]), parsetime(timepattern.findall(sub_comment.body)[0]))):
                            # Make comment and add to db
                            try:
                                sub_comment.reply(createComment(getLength(pattern.findall(comment.body)[0])[1],parsetime(timepattern.findall(sub_comment.body)[0])))
                                addToDatabase(sub_comment.id,comment.id)
                            except Exception as e:
                                logging.info('Error occurred while comenting, check logs: '+ str(e))  
                            # print(createComment(getLength(pattern.findall(comment.body)[0])[1],parsetime(timepattern.findall(sub_comment.body)[0])))                                                                            
                            time.sleep(SLEEPTIME)
                        continue
                    else:
                        for grandchild_comment in sub_comment.replies:
                            if isinstance(grandchild_comment, praw.models.MoreComments):
                                continue
                            if (isinDatabase(grandchild_comment.id)):
                                continue
                            if (len(pattern.findall(sub_comment.body)) == 1) and ((len(timepattern.findall(grandchild_comment.body)) ==1) and ("youtube.com" not in grandchild_comment.body) and (("youtu.be" not in grandchild_comment.body))):
                                if(validate(getLength(pattern.findall(sub_comment.body)[0]), parsetime(timepattern.findall(grandchild_comment.body)[0]))):
                                    # Make comment and add to db
                                    try:
                                        grandchild_comment.reply(createComment(getLength(pattern.findall(sub_comment.body)[0])[1],parsetime(timepattern.findall(grandchild_comment.body)[0])))
                                        addToDatabase(grandchild_comment.id,sub_comment.id)
                                    except Exception as e:
                                        logging.info('Error occurred while comenting, check logs: '+ str(e))
                                    # print(createComment(getLength(pattern.findall(sub_comment.body)[0])[1],parsetime(timepattern.findall(grandchild_comment.body)[0])))
                                    time.sleep(SLEEPTIME)
                                continue

    logging.info('Finished processing submission rising batch')

# Main
# Subreddits to target
logging.info('New Batch Started: Rising Multireddits')
processABatch(reddit.subreddit("+".join(json.loads(config.get('SUBREDDITS', 'MULTIREDDIT_LIST')))).rising(limit=int(config.get('SUBREDDITS', 'MULTIREDDIT_POSTS'))))
logging.info('New Batch Started: Hot Multireddits')
processABatch(reddit.subreddit("+".join(json.loads(config.get('SUBREDDITS', 'MULTIREDDIT_LIST')))).hot(limit=int(config.get('SUBREDDITS', 'MULTIREDDIT_POSTS'))))

logging.info('New Batch Started: Rising All')
processABatch(reddit.subreddit("+".join(json.loads(config.get('SUBREDDITS', 'ALL_SUBREDDIT')))).rising(limit=int(config.get('SUBREDDITS', 'ALL_POSTS'))))
logging.info('New Batch Started: Hot All')
processABatch(reddit.subreddit("+".join(json.loads(config.get('SUBREDDITS', 'ALL_SUBREDDIT')))).hot(limit=int(config.get('SUBREDDITS', 'ALL_POSTS'))))
logging.info('Finished Processing')