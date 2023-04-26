import praw
import os
import re
from dotenv import load_dotenv
import collections
import time

# Open the text file containing the words
with open('wholesomewords.txt', 'r') as f:
    # Initialize an empty set
    wholesome_set = set()

    # Read the file line by line
    for line in f:
        # Split the line into words and add them to the set
        words = line.strip().split()
        wholesome_set.update(words)

load_dotenv()

# Authenticate with Reddit API
reddit = praw.Reddit(
    client_id=os.environ['REDDIT_CLIENT_ID'],
    client_secret=os.environ['REDDIT_CLIENT_SECRET'],
    username=os.environ['REDDIT_USERNAME'],
    password=os.environ['REDDIT_PASSWORD'],
    user_agent=os.environ['REDDIT_USER_AGENT']
)

# Cache dictionary for API responses
cache = {}

# Subreddit and trigger phrase
subreddit_names = "flatapartmentcheck+IndianTeenagers+JEENEETards"
trigger_phrases = ['!wholesomenesscheck',
                   '!wholesomecheck', '!uwucheck', '!uwucheckself']

# Bot username
bot_username = 'wholesome-counter'

# Listen for comments in subreddits
comments_to_reply = []
for subreddit_name in subreddit_names:
    subreddit = reddit.subreddit(
        "flatapartmentcheck+IndianTeenagers+JEENEETards")
    for incoming_comment in subreddit.stream.comments(skip_existing=True):
        # Check if comment contains any of the trigger phrases
        if any(phrase in incoming_comment.body.lower() for phrase in trigger_phrases):
            # Check if trigger phrase is !uwucheckself and set username
            if '!uwucheckself' in incoming_comment.body.lower():
                user_name = incoming_comment.author.name
            else:
                # Get parent comment and author name
                if '[self]' in incoming_comment.body:
                    parent_comment = incoming_comment
                    user_name = incoming_comment.author.name
                else:
                    parent_comment = incoming_comment.parent()
                    user_name = incoming_comment.parent().author.name

            # Check if bot is being called
            if user_name.lower() == bot_username.lower():
                # Construct reply text without times_called
                reply_text = 'This is the Reddit wholesome counter bot. Leave a comment with a username to get their wholesome count!'
                # Add comment to list of comments to reply to
                comments_to_reply.append((incoming_comment, reply_text))

            else:
                # Get top 300 comments of user
                # Check if cached response exists, then skip it to avoid spam
                # 640 seconds = 10 minutes
                if user_name in cache and 'timestamp' in cache[user_name] and time.time() - cache[user_name]['timestamp'] <= 640:
                    api_comments = cache[user_name]['response']
                else:
                    # Make API request for user comments
                    retries = 3
                    for i in range(retries):
                        try:
                            api_comments = reddit.redditor(
                                user_name).comments.new(limit=300)
                            api_comments = [
                                comment for comment in api_comments]
                            break
                        except praw.exceptions.PRAWException as e:
                            if i == retries - 1:
                                print(
                                    f"Error occurred while making the API request: {e}")
                                api_comments = []
                            else:
                                print(
                                    f"Retrying API request. Attempt {i+1} of {retries}.")
                                time.sleep(10)

                    # Store response in cache
                    cache[user_name] = {
                        'response': api_comments,
                        'timestamp': time.time()
                    }

                    # Initialize wholesome count
                    wholesome_count = 0
                    word_count = collections.Counter()

                    # Analyze comments for wholesome words
                    comment_count = 0
                    for comment in api_comments:
                        # Clean and tokenize comment
                        comment_text = re.sub(
                            r'[^\w\s]', '', comment.body).lower()
                        comment_tokens = comment_text.split()

                        # Count wholesome occurrences
                        for token in comment_tokens:
                            if token in wholesome_set:
                                wholesome_count += 1
                                word_count[token] += 1
                        comment_count += 1

                    # Construct table of wholesome words and counts
                    table_rows = [
                        f"| {word} | {count} |" for word, count in word_count.items()
                    ]
                    table = "\n".join(table_rows)

                    # Construct reply text with wholesome count and table
                    if '!uwucheckself' in incoming_comment.body.lower():
                        reply_text = f'The number of wholesome occurrences in your recent {comment_count} comments is {wholesome_count}.\n\n| Word | Count |\n| --- | --- |\n{table} |\n\nStay wholesome!  \n\nWanna do something even more wholesome? Leave a \u2B50 at the [GitHub repository](https://github.com/MeowthyVoyager/wholesomebot-reddit).'
                    else:
                        reply_text = f'The number of wholesome occurrences in the recent {comment_count} comments of u/{user_name} is {wholesome_count}.\n\n| Word | Count |\n| --- | --- |\n{table} |\n\nStay wholesome!  \n\nWanna do something even more wholesome? Leave a \u2B50 at the [GitHub repository](https://github.com/MeowthyVoyager/wholesomebot-reddit).'

                    # Reply to the comment
                    incoming_comment.reply(reply_text)
