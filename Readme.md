### About
Reddit bot that parses rising posts with parent comments as youtube url & child replies as timestamps to create grand child comments of timestamped youtube url link.

Ran as a cron job every 1 hour.

### Steps to Run (on linux server)
1. `cp sample-config.ini config.ini` & configure your bot.
2. `which python` & replace shebang line#1 of main.py with the python path. [Python3 recommended]
3. `pip install -r requirements.txt` to install python dependencies.
4.  `crontab -e` & add `main.py` as cronjob at the end of file with following format:

`0 * * * * cd <absolute-path-to-repo>;<absolute-path-to-main.py> >> <aboluste-path-to-cron.log> 2>&1`

Example:
`0 * * * * cd /var/www/timestamp_bot;/var/www/timestamp_bot/main.py >> /var/www/timestamp_bot/cron.log 2>&1`

### Debugging
1. `cat /var/log/syslog | grep cron` to check if cron job is running fine.
2. `cat cron.log` to check for errors from bot/reddit server.
3. `cat timestamp_bot_log.log` to check bot process/logs.

### Issues/Suggestions
Report all issues/suggestions at <a href="https://github.com/ankitgyawali/reddit-timestamp-bot/issues" target="_blank">issue page</a>.