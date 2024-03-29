#!/usr/bin/env python

##########################################################################################
### Prep stuff
##########################################################################################
# Get some stuff that we need.
import sys
import os
import shutil
import re
import time
import uuid
import urllib2
import email
import smtplib
from email.mime.text import MIMEText
from email.Utils import formatdate

try:
  import argparse
  argparse_available = True
except:
  argparse_available = False

try:
  import yaml
  yaml_available = True
except:
  yaml_available = False

try:
  import markdown2
  markdown_available = True
except: 
  markdown_available = False

try:
  from PIL import Image
  from StringIO import StringIO
  from PIL import ExifTags
  imaging_available = True
except:
  imaging_available = False


if argparse_available:
  # Setup the arguments we'll use and parse the ones we've gotten.
  parser = argparse.ArgumentParser()
  parser.add_argument('--all', dest='all', action='store_true',
                      help='Builds the entire site.')
  parser.add_argument('--clean', dest='clean', action='store_true',
                      help='Empties the build folder.')
  parser.add_argument('--dependencies', dest='dependencies', action='store_true',
                      help='Builds all the dependencies, ignored unless used with \
                      --single, --new, or --email.')
  parser.add_argument('--email', dest='email', action='store_true',
                      help='Reads an email message from STDIN and parses to create a new \
                      post. Overrides --all, --posts, --indexes, --home, and --single')
  parser.add_argument('--error', dest='error', action='store_true', 
                      help='Generates static error pages.')
  parser.add_argument('--extras', dest='extras', action='store_true',
                      help='Generates minified css and js files.')
  parser.add_argument('--feed', dest='feed', action='store_true',
                      help='Generates RSS feed.')
  parser.add_argument('--galleries', dest='galleries', action='store_true',
                      help='Generates galleries.')
  parser.add_argument('--home', dest='home', action='store_true',
                      help='Builds the home page.')
  parser.add_argument('--indexes', dest='indexes', action='store_true',
                      help='Builds the index pages.')
  parser.add_argument('--new', dest='new', action='store_true',
                      help='Starts an interactive sesson to create a new post. *Not yet \
                      implemented*')
  parser.add_argument('--no-http', dest='http', action='store_false',
                      help='Prevents crunch from contacting external sources during the \
                      build.')
  parser.add_argument('--pages', dest='pages', action='store_true',
                      help='Builds all static pages.')
  parser.add_argument('--posts', dest='posts', action='store_true',
                      help='Builds all posts.')
  parser.add_argument('--serve', dest='serve', action='store_true',
                      help='Starts a lightweight HTTP server to serve build folder to \
                      localhost.')
  parser.add_argument('--setup', dest='setup', action='store_true',
                      help='Creates a basic blog framework to start with. *Not yet \
                      implemented.*')
  parser.add_argument('--single', dest='single',
                      help='Builds a single post. Takes a filename as an argument or use \
                      - to read from STDIN. Overrides --all, --posts, --indexes, --home \
                      *Not yet implemented.*')
  parser.add_argument('--verbose', dest='verbose', action='store_true',
                      help='Enables information display other than errors.')
  args = parser.parse_args()
else:
  print 'ERROR: The python module argparse is unavailable. Please install argparse and \
    try again.'
  sys.exit(1)

##########################################################################################
### Define some variables
##########################################################################################

### Folder Structures are relative to where crunch is.
base_folder = os.path.abspath(os.path.dirname(sys.argv[0]))


### Define the configuration file:
conf_file = base_folder + '/conf.yaml'

### Get configuration
if yaml_available:
  conf = yaml.load(open(conf_file).read())
else:
  print 'ERROR: yaml is unavailable, please install and retry.'
  sys.exit(1)
  

# Define some variables for reuse.
build_folder = base_folder + '/' + conf['build_folder']
pages_folder = base_folder + '/' + conf['pages_folder']
posts_folder = base_folder + '/' + conf['posts_folder']
public_folder = base_folder + '/' + conf['public_folder']
images_folder = base_folder + '/' + conf['images_folder']
galleries_folder = base_folder + '/' + conf['galleries_folder']
css_folder = base_folder + '/' + conf['css_folder']
scripts_folder = base_folder + '/' + conf['scripts_folder']


### Classes

# Define a class for creating a specific page.
class Page:
  title = conf['title']
  body = conf['tagline']
  author = conf['author']
  description = conf['description']
  base_url = conf['base_url']
  
  
  # Return a formatted version of the page using the template function format_layout()
  def formatted(self):
    return format_layout(self)
    
  # Return an xml formatted version of the page using the template function format_xml()
  def xml(self):
    return format_xml(self)

# Define a class for a blog post.
class Post:
  # Fill the post with bogus data.
  title = 'Title'
  time = 0.0
  markdown = 'Content'
  content = '<p>Content</p>'
  slug = 'slug'
  short = 'amd1'
  filename = slug + '.md'

  # Get a 4 digit year from the epoch time.
  def year(self):
    return time.strftime("%Y", self.time)

  # Get a 2 digit month from the epoch time.
  def month(self):
    return time.strftime("%m", self.time)
    
  # Return a formatted date, won't show HMS for 
  # old posts that don't have full dates.
  def date_pretty(self):
    if time.strftime("%H", self.time) == "00" and time.strftime("%M", self.time) == "00":
      return time.strftime("posted on %Y-%m-%d", self.time)
    else:
      return time.strftime("posted on %Y-%m-%d at %I:%M %p", self.time)
  
  # Generate a date in a specific format for the RSS feed.
  def date_2822(self):
    return formatdate(time.mktime(self.time))
  
  # Generate a date in the 8601 format.
  def date_8601(self):
    return time.strftime("%Y-%m-%dT%H:%M:%S", self.time)

  # Returns the relative url for the post.
  def url(self):
    return '/' + self.year() + '/' + self.month() + '/' + self.slug

  # Returns the full short url for the post.
  def url_short(self):
    return 'http://amd.im/' + self.short

  # Parses a string to populate the post object.
  def parse(self, string):
    header, body = string.split('\n\n', 1)               
  
    y = yaml.load(header)
      
    self.title = y['title']
    
    self.time = time.localtime(y['date'])
    
    self.slug = re.sub('\-{2,}', '-', re.sub('[^a-z0-9-]', '', re.sub('\s', '-', \
                re.sub('&', 'and', str(self.title).lower()))))

    # if the short url is pre-defined, use that, otherwise get a new one from amd.im.
    if 'short' in y: 
      self.short = y['short']
    else:
      if args.http:
        self.short = urllib2.urlopen('http://amd.im/api-create/' + conf['base_url'] + \
                                      self.year() + '/' + self.month() + '/' + \
                                      self.slug).read().lstrip('http://amd.im/')
      else:
        if args.verbose: print 'WARN: HTTP disabled. Short URL unavailable.'
        self.short = ''


    # if markdown is available, use that to process the post body.
    self.markdown = body
    if markdown_available:
      self.content = markdown2.markdown(str(body), extras=["code-color", "code-friendly"])
    else:
      if args.verbose: print 'WARN: markdown unavailable, using raw post data.'
      self.content = self.markdown

  # returns a string that has a fully templated post.
  def formatted(self):
    return format_post(self)
    
  def xml(self):
    return format_xml_item(self)


class Gallery_Image:
  master_image = 'img.jpg'
  gallery_name = 'test'
  
  def name(self):
    [name, extension] = str.split(self.master_image, '.')
    return name
  
  def full_url(self):
    return '/' + conf['galleries_folder'] + '/' + self.gallery_name + '/' + \
      self.master_image
  
  def thumbnail_file(self):
    [name, extension] = str.split(self.master_image, '.')
    return name + '_thm.' + extension
    
  def thumbnail_url(self):
    return '/' + conf['galleries_folder'] + '/' + self.gallery_name + '/' + \
      self.thumbnail_file()
    
  def mid_file(self):
    [name, extension] = str.split(self.master_image, '.')
    return name + '_z.' + extension
    
  def mid_url(self):
    return '/' + conf['galleries_folder'] + '/' + self.gallery_name + '/' + \
      self.mid_file()
    
  def mid_page(self):
    return '/' + conf['galleries_folder'] + '/' + self.gallery_name + '/' + \
      str.split(self.master_image, '.')[0] + '.htm'
    
  def formatted_single(self):
    return format_gallery_single(self)
  
  def formatted_thumb(self):
    return format_gallery_thumb(self)


##########################################################################################
### Templates.
##########################################################################################


# General purpose formatter for a full page, takes in a Page object. 
def format_layout(page):
  return """<html>
  <head>
    <meta charset="utf-8" />
    <meta name="author" content="%(author)s" />
    <meta name="description" content="%(description)s" />
    <!--[if lt IE 9]>
      <script src="http://html5shim.googlecode.com/svn/trunk/html5.js"></script>
    <![endif]-->
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />

    <link rel="icon" type="image/png" href="/images/favicon.png" />

    <link rel="stylesheet" type="text/css" href="/css/app.css" />

    <link rel="alternate" type="application/atom+xml" title="amdavidson.com feed" 
          href="/index.xml" />
              
    <title>%(title)s</title>
  </head>
  <body>
    <div class="container">
    <div class="six columns">
      <div class="five columns">
        <h1><a href="/">amdavidson</a></h1>
      </div>
    </div>
    <div class="twelve columns">
      %(body)s
    </div>
    <div class="four columns">
      <h6><a href="/about.htm">about</a></h6>
      <p class="small">amdavidson.com is a simple blog run by Andrew Davidson, a 
      manufacturing engineer with a blogging habit. He sometimes posts 140 character 
      <a href="http://twitter.com/amdavidson">tidbits</a>, shares 
      <a href="/">photos</a>, and saves 
      <a href="http://pinboard.in/u:amdavidson/">links</a>. You can also see posts 
      dating <a href="/archives.htm">back to 2005</a>.</p>
      
      <div id="twitter" style="display:none;">
        <h6><a href="http://twitter.com/amdavidson">tweeted</a></h6>
        <p class="small"><span id="tweet"></span><br/>
        <span id="tweet-date"></span></p>
      </div>

      <div id="pinboard" style="display:none;">
        <h6><a href="http://pinboard.in/u:amdavidson">bookmarked</a></h6>
        <p class="small"><a id="pin-link" href="/"><span id="pin-title"></span></a><br/>
        <span id="pin-description"></span><br/>
        <span id="pin-date"></span></p>
      </div>

      <h6>Search</h6>
      <form method="get" id="search" action="http://duckduckgo.com/">
        <input type="hidden" name="kj" value="#181818" />
        <input type="hidden" name="kl" value="us-en" />
        <input type="hidden" name="kg" value="g" />
        <input type="hidden" name="k4" value="-1" />
        <input type="hidden" name="k1" value="-1" />
        <input type="hidden" name="sites" value="amdavidson.com"/>
        <input type="text" name="q" maxlength="255" placeholder="Search&hellip;"/>
        <input type="submit" value="DuckDuckGo Search" style="visibility: hidden;" />
      </form>
                        
    </div>
    </div>

    <script src="/scripts/zepto.min.js"></script>
    <script src="/scripts/app.js"></script>
    <script src="http://mint.amdavidson.com/?js" type="text/javascript"></script>

  </body>
  <!-- Generated by crunch on %(date)s -->
</html>
""" % {'title':page.title, 'body':page.body, 'author':page.author, 
       'description':page.description, 'date':time.strftime('%Y-%m-%d at %H:%M:%S')}

# General purpose formatter for a specific post, takes in a Post object
def format_post(post):
  return """
      <div class="eleven columns">
        <h3><a href=\"%(url)s\" title="%(title)s">%(title)s</a></h3>
        <p class="small"><span class="timeago" title="%(isodate)s">%(date)s</span> - 
          <a href=\"%(short_url)s\">amd.im/%(short)s</a></p>
      </div>
      <div class="eleven columns">
        %(content)s
      </div>
    """ % {'title':post.title, 'content':post.content, 'url':post.url(), 
           'isodate':post.date_8601(), 'date':post.date_pretty(), 
           'short_url':post.url_short(), 'short':post.short}

def format_static(title, content, url):
  return """
      <div class="eleven columns">
        <h3><a href=\"%(url)s\" title="%(title)s">%(title)s</a></h3>
      </div>
      <div class="eleven columns">
        %(content)s
      </div>
  """ % {'title':title, 'content':content, 'url':url}

# General purpose formatter for error pages. Takes in an error code string.
def format_error(code):
  return """
      <div class="eleven columns">
        <h3>Error %(code)s</h3>
      </div>
      <div class="eleven columns">
        <p>Unfortunately, you've found one of those elusive error %(code)s pages.</p>
        <p>However you ended up here, I'm going to guess this isn't where you wanted 
          to be.</p>
        <p>Perhaps you were looking for the <a href="/">home page</a>? If not, maybe you 
        can find what you need in the <a href="/archives.htm">archives</a>.</p>
      </div>
    """ % {'code': code}

def format_xml(page):
  return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>%(title)s</title>
    <description>%(description)s</description>
    <link>%(base_url)s</link>
    
    %(yield)s
    
  </channel>
</rss>
    """ % {'title': page.title, 'description': page.description, 
           'base_url': page.base_url, 'yield': page.body}
           
def format_xml_item(post):
  return """
    <item>
      <title>%(title)s</title>
      <link>%(url)s</link>
      <guid>%(url)s</guid>
      <pubDate>%(date_2822)s</pubDate>
      <description>
        %(body)s
      </description>
    </item>
  """ % {'title': post.title, 'url': conf['base_url'].rstrip('/') + post.url(), \
         'date_2822': post.date_2822(), 'body': post.content }

def format_gallery_single(image):
  return """
      <div class="eleven columns">
        <h3>%(name)s</h3>
        <p style="text-align:center;"><a href="%(full_url)s">
          <img class="scale-with-grid" src="%(mid_url)s" />
        </a></p>
      </div>
  """ % { 'name': image.name(), 'full_url': image.full_url(), 'mid_url': image.mid_url() }
  
def format_gallery_thumb(image):
  return """
      <div class="thumbnail">
        <a href="%(mid_page)s"><img src="%(thm_path)s" /></a>
      </div>
  """ % { 'mid_page': image.mid_page(), 'thm_path': image.thumbnail_url() }

##########################################################################################
### Helper Functions
##########################################################################################


# get_recent() takes in an integer that sets the number of recent posts to get, it 
# returns a list of post objects in reverse chronological order. This function is used
# in crunch_feed() and crunch_home().
def get_recent(count):
  # Create an empty variable to store posts in.
  post_list = []
      
  # Get all the years in reverse order.
  for year in sorted(os.listdir(posts_folder), reverse = True):

    # Make sure we're using a year folder.
    if re.match('\d\d\d\d', year): 
      
      # Get all the months for the year in reverse order.
      for month in sorted(os.listdir(posts_folder + '/' + year), reverse = True):
        
        # Make sure we're working with a month folder:
        if re.match('\d\d', month):
          
          # Make a temporary list.
          tmp = []
          
          # Grab all the posts in the folder in no particular order.
          for file in os.listdir(posts_folder + '/' + year + '/' + month):
            
            # Ensure we're only grabbing files with the correct extension.
            if file.endswith(conf['extension']):
              
              # Make a new post object
              p = Post()
              
              # Open the file.
              f = open(posts_folder + '/' + year + '/' + month + '/' + file)
              
              # Set the filename.
              p.filename = file
              
              # Parse the post.
              p.parse(f.read())
              
              # Add the post to the tmp list
              tmp.append(p)
          
          # Process this month's posts and add them to the empty variable in reverse
          # chronological order.
          for post in sorted(tmp, key=lambda p: p.time, reverse = True):
            if len(post_list) >= count: break
            post_list.append(post)
            
        if len(post_list) >= count:
          break
    
    if len(post_list) >= count:
      break
      
  return post_list


##########################################################################################
### Build Functions
##########################################################################################

# Function to ensure that the build folder exists for use. Creates one from the parent 
# folders if it does not exist.
def ensure_build_folder():
  if os.path.exists(build_folder):
    return 0
  else:
    shutil.copytree(public_folder, build_folder)
    shutil.copytree(images_folder, build_folder + '/' + conf['images_folder'])
    os.mkdir(build_folder + '/' + conf['galleries_folder'])
    os.mkdir(build_folder + '/' + conf['css_folder'])
    os.mkdir(build_folder + '/' + conf['scripts_folder'])
    return 2
  return 1

# Generate error pages.
def crunch_errors():
  if args.verbose: print 'Building error pages.'
  
  error_list = ['400', '401', '403', '404', '500', '502', '503', '509']
 
  for error in error_list:
    page = Page()
    page.title = 'Error ' + error + ' | ' + page.title
    page.body = format_error(error)
    
    f = open(build_folder + '/error/' + error + '.htm', 'w')
    f.writelines(page.formatted())
    f.close

# Process pages.
def crunch_pages(): 
  if args.verbose: print 'Building the static pages.'

  # Get all the files in the pages folder.
  for filename in os.listdir(pages_folder):
    # Ensure we're looking at only the files with the right extension per 
    # conf['extension'].
    if filename.endswith(conf['extension']):
      if args.verbose: print 'Building ' + filename
      
      # Split the page header from the body.
      header, body = open(pages_folder + '/' + filename).read().split('\n\n', 1)               
  
      # Pull a dict from the yaml in the header.
      y = yaml.load(header)
      
      # Parse the post and grab the content.
      content = markdown2.markdown(body, extras=["code-color", "code-friendly"])
      
      # Pull the title out of the metadata.
      title = y['title']
      
      # Generate the url
      url = '/' + filename.rstrip(conf['extension']) + '.htm'
      
      # Make the body of the page
      body = format_static(title, content, url)
      
      # Make a new page object and add the body.
      page = Page()
      page.title = title + ' | ' + page.title
      page.body = body
      
      # Make a new file and write out the page.
      n = open(build_folder + url, 'w')
      n.writelines(page.formatted())
      n.close
      os.chmod(build_folder + url, 0644)
      


# Processes all posts. 
def crunch_posts():
  if args.verbose: print 'Building the posts.'
  
  # Get every year in the posts folder.
  for year in os.listdir(posts_folder):
    # Ensure we're not processing some errant folder that isn't a 'year'
    if re.match('\d\d\d\d', year):
      if args.verbose: print 'Building ' + year + ':'

      # Build a corresponding year folder in the build folder.
      year_path = build_folder + '/' + year
      if not os.path.exists(year_path): os.makedirs(year_path)
      
      # Get every month in the year folder.
      for month in os.listdir(posts_folder + '/' + year):
        if re.match('\d\d', month):
          if args.verbose: print "\t" + month + ':'

          # Build a corresponding month folder in the build/year folder.
          month_path = build_folder + '/' + year + '/' + month
          if not os.path.exists(month_path): os.makedirs(month_path)
          
          # Grab every post in the month folder.
          for i in os.listdir(posts_folder + '/' + year + '/' + month):
            
            # Only process files with the correct extension per `conf.yaml`.
            if i.endswith(conf['extension']):
              if args.verbose: print '\t\t' + i
              
              # Process the post
              crunch_single(open(posts_folder + '/' + year + '/' + month \
                + '/' + i).read())

# Function to process the home file.
def crunch_home():
  if args.verbose: print 'Building the home page.'  
  
  # Grab the recent posts.
  if args.verbose: print '\tGet all the required posts.'
  postlist = get_recent(conf['home_count'])
  
  # Create the home page. 
  if args.verbose: print '\tWriting the home page.'
  home = Page()
  
  # Make an empty home variable
  home.body = ''

  # Sort the posts by their actual timestamps and then assemble the most recent formatted 
  # posts into the body of the page. The post count is determined by the home_count 
  # variable in the configuration file.
  for p in postlist:
    home.body += p.formatted()
  
  # Write out the home page. 
  h = open(build_folder + '/index.htm', 'w')
  h.writelines(home.formatted())
  h.close()
  os.chmod(build_folder + '/index.htm', 0644)
            
  
# Function to create all the index pages for the month and year folders. 
# This should be extended to also generate an 'archive' page to allow visitors to traverse
# the archives.
def crunch_indexes():
  if args.verbose: print 'Building the indexes.'
  
  # Start the body for the archives.htm page.
  archives_body = '\t<div class="eleven-columns">\n\t\t<h3>Post Archives</h3>\n\t</div>\n' + \
    '\t<div class="eleven-columns">\n\t\t<ul class="square">\n'

  # Grab all the years in the posts folder.
  for year in sorted(os.listdir(posts_folder), reverse=True): 

    # Ensure that we're working with a year folder.
    if re.match('\d\d\d\d', year):
      if args.verbose: print 'Building indexes for ' + year + ':'
			
      # Add an entry to archives.htm
      archives_body += '\t\t\t<li><a href="/' + year + '">' + year + '</a>\n\t\
        \t\t<ul class="circle">\n'

      # Make a corresponding year folder in the build folder if it doesn't exist.
      year_path = build_folder + '/' + year
      if not os.path.exists(year_path): os.makedirs(year_path)
      
      # Open up a list to dump all the year's posts in.
      year_catch = []

      # Grab all the month folders for the current year.
      for month in sorted(os.listdir(posts_folder + '/' + year), reverse=True):

        # Ensure we're working with a year folder.
        if re.match('\d\d', month):
          if args.verbose: print "\t" + month

          # Add an entry to archives.htm.
          archives_body += '\t\t\t\t\t<li><a href="/' + year + '/' + month + '">' + month \
              + '</a>\n'

          # Make a corresponding month folder in the build folder if it doesn't exist.
          month_path = build_folder + '/' + year + '/' + month
          if not os.path.exists(month_path): os.makedirs(month_path)

          # Open up a list to dump all the month's posts in.
          month_catch = []

          # Grab all the posts for the current month.
          for i in os.listdir(posts_folder + '/' + year + '/' + month):

            # Process the posts with the correct extension.
            if i.endswith(conf['extension']):

              # Create a new post object and parse the post file.
              post = Post()
              f = open(posts_folder + '/' + year + '/' + month + '/' + i)
              post.filename = i
              post.parse(f.read())        
              f.close()

              # Add this post to the list for the current month and year.
              month_catch.append(post)
              year_catch.append(post)
          
          # Once all the posts for the current month have been processed. make a new 
          # Page object for the month.
          month_page = Page()
          month_page.title = 'Posts from ' + str(year) + '/' + str(month) + ' | ' + \
                             month_page.title
          month_body = ""

          # Create the body of the month page with all the posts for the month 
          # in reverse chronological order.
          for post in sorted(month_catch, key=lambda post: post.time, reverse = True):
            month_body += post.formatted()
          month_page.body = month_body

          # Write out the titles to the posts to archives.htm in ascending order.
          archives_body += '\t\t\t\t\t\t<ul>\n'
          for post in sorted(month_catch, key=lambda post: post.time, reverse=True):
            archives_body += '\t\t\t\t\t\t\t<li><a href="' + post.url() + '">' + \
              str(post.title) + '</a></li>\n'
          archives_body += '\t\t\t\t\t\t</ul>\n\t\t\t\t\t</li>\n'

          # Write out the month page into the build folder.
          m = open(build_folder + '/' + year + '/' + month + '/index.htm', "w")
          m.writelines(month_page.formatted())
          m.close()
          os.chmod(build_folder + '/' + year + '/' + month + '/index.htm', 0644)
      
      # Close out the list of months in archive.htm
      archives_body += '\t\t\t\t</ul>\n\t\t\t</li>\n'
      
      # Once all the posts for the current year have been processed, make a new
      # Page object for the year.
      year_page = Page()
      year_page.title = 'Posts from ' + str(year) + ' | ' + year_page.title
      year_body = ""

      # Create the body of the year page with all the posts for the year in reverse 
      # chronological order. 
      for post in sorted(year_catch, key=lambda post: post.time, reverse = True):
        year_body += post.formatted()
      year_page.body = year_body

      # Write out the year page to the build folder.
      y = open(build_folder + '/' + year + '/index.htm', "w")
      y.writelines(year_page.formatted())
      y.close
      os.chmod(build_folder + '/' + year + '/index.htm', 0644)
    
  # Close out the list of years in archive.htm
  archives_body += '\t\t</ul>\n\t</div>'
  
  archives_page = Page()
  archives_page.title = 'Archives | ' + archives_page.title
  archives_page.body = archives_body
  
  a = open(build_folder + '/archives.htm', 'w')
  a.writelines(archives_page.formatted())
  a.close
  os.chmod(build_folder + '/archives.htm', 0644)
    
    
# crunch_clean() deletes the build folder to clear out old ghosts.
# This function is not generally necessary as files will be overwritten 
# when they are re-processed.
def crunch_clean():
  if args.verbose: print 'Cleaning out the old build(s).'
  if os.path.exists(build_folder):
    shutil.rmtree(build_folder)

# crunch_email(message) processes an email from a string (message) to create a new post.
# it returns the filename of the post file that was created.
def crunch_email(message):
  if args.verbose: print 'Crunching the email.'

  # Validate the email is OK to process based on the sender (easily spoofable).
  if re.search(conf['email_sender'], message.get('from'), re.I):
    if args.verbose: print 'Sender validated.'
    
    # Get the date from the email.
    email_date = email.utils.parsedate(message.get('date'))
    if args.verbose: print 'Message date: ', time.strftime('%Y-%m-%d %H:%M:%S', \
                                                           email_date)
    # Create the epoch time from the date.
    epoch_time = time.mktime(email_date)
    if args.verbose: print 'Epoch time: ', epoch_time
    
    # Get the title from the Subject line.
    title = message.get('subject')
    if args.verbose: print 'Title: ', title
    
    # Process the post slug from the title, the slug is also the filename.
    slug = re.sub('\-{2,}', '-', re.sub('[^a-z0-9-]', '', re.sub('\s', '-', re.sub('&', \
                  'and', title.lower()))))
    if args.verbose: print 'Slug:', slug
    
    # Making empty body to put stuff in.
    body = ''
    
    # Walk through the message parts to find any plain/text body elements or 
    # image attachments.
    if args.verbose: print 'Running through the message parts.'
    for part in message.walk():
      type = part.get_content_type()
    
      # If the content is text/plain, use it for the message body. (This may accidentally
      # collect certain types of forwarded messages.)
      if type == 'text/plain':
        body = body + part.get_payload()
    
      # If the content/type starts with 'image' process the image and add it to the top 
      # of the body.
      elif re.search('image', type, re.I):
        if args.verbose: print 'Found an image.'

        # Let's make sure that we have the necessary libraries for image processing.
        if not imaging_available:
          if args.verbose: print 'WARN: PIL not available, skipping image.'
          continue
    
        # If we have the imaging libraries, process the image.
        else:

          # Generate a UUID to use for the filename.
          id = str(uuid.uuid4())

          # Ensure that the UUID does not already exist.
          while os.path.exists(images_folder + '/posts/' + id + '.jpg'):
            id = str(uuid.uuid4())
          
          # Get the image blob from the email.
          payload = part.get_payload(decode=True)

          # Open the image with PIL.
          original = Image.open(StringIO(payload))

          # Check for a rotated image.
          for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation]=='Orientation' : break
          if original._getexif():
            exif = dict(original._getexif().items())
          else: 
            exif = False 
          
          
          
          if not exif == False:
            try:
              if args.verbose: print 'Image is rotated, correcting.'
              if exif[orientation] == 3:
                original = original.rotate(180, expand=True)
              elif exif[orientation] == 6:
                original = original.rotate(270, expand=True)
              elif exif[orientation] == 8:
                original = original.rotate(90, expand=True)
            except:
              if args.verbose: print 'Cannot detect rotation from EXIF.'
              

          # Create empty resized var.
          resized = False

          # If the image extends beyond the image_width x image_height square we
          # need to resize the image and save a smaller version.
          # This should not upscale any smaller images.
          if original.size[0] > conf['image_width'] or original.size[1] > \
            conf['image_height']:
            if args.verbose: print 'Image is larger than ' + str(conf['image_width']) + \
              'x' + str(conf['image_height'])
            # Calculate the aspect ratio of the image.
            aspect = float(original.size[0])/float(original.size[1])

            # If the image is wider than it is tall, calculate the height from 
            # image_width.
            if aspect > 1:
              resized = original.resize((conf['image_width'],int(conf['image_width'] / \
                aspect)), Image.ANTIALIAS)

            # If the image is taller than it is wider, calculate the width from 
            # image_height.
            elif aspect < 1:
              resized = original.resize((int(conf['image_height']*aspect), \
                conf['image_height']), Image.ANTIALIAS)

            # If the image is square use image_width to set the size.
            else:
              resized = original.resize((conf['image_width'], conf['image_width']), \
                Image.ANTIALIAS)
          
          if args.verbose: print 'Saving image to ' + images_folder + '/posts'
          
          # Save the original file to the $images/posts folder.
          original.save(images_folder + '/posts/' + id + '.jpg')
          os.chmod(images_folder + '/posts/' + id + '.jpg', 0644)

          # If we created a resized copy, save to the $images/posts folder.
          if not resized == False:
            if args.verbose: print 'Saving resized image to ' + images_folder + '/posts'
            resized.save(images_folder + '/posts/' + id + '_z.jpg')
            os.chmod(images_folder + '/posts/' + id + '_z.jpg', 0644)
          
          # If the build folder exists save the image(s) to there as well.
          if os.path.exists(build_folder):
            if args.verbose: print 'Saving image to ' + build_folder + '/images/posts/'
            original.save(build_folder + '/images/posts/' + id + '.jpg')
            os.chmod(build_folder + '/images/posts/' + id + '.jpg', 0644)
            
            if not resized == False:
              if args.verbose: print 'Saving resized image to ' + build_folder + \
                '/images/posts/'
              resized.save(build_folder + '/images/posts/' + id + '_z.jpg')
              os.chmod(build_folder + '/images/posts/' + id + '_z.jpg', 0644)
          
          # Generate an image tag string based on whether we had to resize the image or 
          # not.
          if resized:
            if args.verbose: print 'Generating image tag (resized).'
            img_tag = '<p style="text-align:center;"><a href="/images/posts/' + id + \
                      '.jpg"><img class="scale-with-grid" src="/images/posts/' + id + \
                      '_z.jpg" /></a></p>\n\n'
          else:
            if args.verbose: print 'Generating image tag.'
            img_tag = '<p style="text-align:center;"><a href="/images/posts/' + id + \
                      '.jpg"><img class="scale-with-grid" src="/images/posts/' + id + \
                      '.jpg" /></a></p>\n\n'
          
          print img_tag
          
          # Add the image tag to the top of the body.
          if args.verbose: print 'Adding image tag to post.'
          body = img_tag + body
          
    if args.verbose: print 'Body:', body
    
    # Let's get the short url for the post.           
    short = None
    if args.http:
      if args.verbose: print 'Getting short url.'
      short = urllib2.urlopen('http://amd.im/api-create/' + conf['base_url'] + \
                              time.strftime('%Y', email_date) + '/' + time.strftime('%Y',\
                              email_date) + '/' + slug).read().lstrip('http://amd.im/')
    else:
      if args.verbose: print 'WARN: HTTP calls disabled, short url unavailable.'
          
    # Generate the filename for the new post.
    filename = posts_folder + time.strftime("/%Y/%m/", email_date) + slug + \
               conf['extension']

    # Check to make sure the directory exists for the new post.
    if not os.path.exists(posts_folder + time.strftime("/%Y/%m/", email_date)):
      if not os.path.exists(posts_folder + time.strftime("/%Y/", email_date)):
        if args.verbose: print 'Making a new month folder.'
        os.mkdir(posts_folder + time.strftime("/%Y/", email_date))
        os.chmod(posts_folder + time.strftime("/%Y/", email_date), 0755)
      if args.verbose: print 'Making a new year folder.'
      os.mkdir(posts_folder + time.strftime("/%Y/%m/", email_date))
      os.chmod(posts_folder + time.strftime("/%Y/%m/", email_date), 0755)


    # Write out the post to the new file.
    if args.verbose: print 'Making a new post in the posts folder.'
    f = open(filename, 'w')
    f.write('title: ' + title + '\n')
    f.write('date: ' + str(epoch_time) + '\n')
    f.write('author: ' + conf['author'] + '\n')
    f.write('slug: ' + slug + '\n')
    if not short == None:
      f.write('short: ' + short + '\n')
    f.write('\n')
    f.write(body)
    f.close
    os.chmod(filename, 0644)
    
    # Return the filename.
    return filename


# crunch_single() generates a new post file from an inputted string and returns the post 
# object. Is used for both generating from a post file, from stdin, or from a parsed 
# email.
def crunch_single(string): 
  # Create a new Post object for this new post.
  post = Post()
  if args.verbose: print 'Parsing post.'

  # Parse the incoming string into the post object.
  post.parse(string)

  # Create a new page.
  if args.verbose: print 'Creating new page.'
  page = Page()

  # Modify the title.
  page.title = str(post.title) + ' | ' + page.title

  # Include the formatted post in the page's body.
  page.body = post.formatted()
  
  if args.verbose: print 'Saving page.'

  # Generate the filename of the new post.
  filename = build_folder + '/' + post.year() + '/' + post.month() + '/' + post.slug + \
             '.htm'
  if args.verbose: print 'Filename:', filename

  # Check to make sure the directory exists for the new post.
  if not os.path.exists(build_folder + '/' + post.year() + '/' + post.month()):
    if not os.path.exists(build_folder + '/' + post.year()):
      os.mkdir(build_folder + '/' + post.year())
      os.chmod(build_folder + '/' + post.year(), 0755)
    os.mkdir(build_folder + '/' + post.year() + '/' + post.month())
    os.chmod(build_folder + '/' + post.year() + '/' + post.month(), 0755)

  
  # Write out the page to the new file.
  n = open(filename, "w")
  n.writelines(page.formatted())
  n.close
  os.chmod(filename, 0644)

  # If the dependencies flag is set, we need to rebuild the pages that would include
  # this post.
  if args.dependencies:
    
    # Let's rebuild the index pages for this post's year and month.
    if args.verbose: print 'Rebuilding indexes for ' + post.year() + '/' + post.month() \
      + ':'
    
    # Make the year folder if it doesn't exist. (First post of a new year.)
    year_path = build_folder + '/' + post.year()
    if not os.path.exists(year_path): os.makedirs(year_path)

    # Open up a new list to dump all the years' posts.
    year_catch = []

    # Iterate through all the months for that year.
    for month in os.listdir(year_path):
      
      # Make sure the folder's filename looks like a two digit month.
      if re.match('\d\d', month):

        # Create the current month's folder if it doesn't exist.
        month_path = build_folder + '/' + post.year() + '/' + month
        if not os.path.exists(month_path): os.makedirs(month_path)

        # Create a list to dump all the current month's posts in.
        month_catch = []

        # Iterate through all the posts for the current month.
        for i in os.listdir(posts_folder + '/' + post.year() + '/' + month):
          
          # Only process files that end with the correct extension.
          if i.endswith(conf['extension']):
            
            # Create a new post object.
            p = Post()

            # Open the post file.
            f = open(posts_folder + '/' + post.year() + '/' + month + '/' + i)
            
            # Parse the post.
            p.filename = i
            p.parse(f.read())
            
            # Close the post file.        
            f.close()

            # Add it to the year list. Add it to the month list, IF it is the 
            # correct month for the new post we created. 
            if month == post.month():
              month_catch.append(p)
            year_catch.append(p)
    
    # Create a new page for the month.    
    month_page = Page()
    month_page.title = 'Posts from ' + str(post.year()) + '/' + str(post.month()) + ' | '\
                       + month_page.title
    month_body = ""

    # Insert all the posts for that month into the body sorted reverse chronologically.
    for p in sorted(month_catch, key=lambda p: p.time, reverse = True):
      month_body += p.formatted()
    month_page.body = month_body

    # Write out the index page for the post's month.
    m = open(build_folder + '/' + post.year() + '/' + post.month() + '/index.htm', "w")
    m.writelines(month_page.formatted())
    m.close()
    os.chmod(build_folder + '/' + post.year() + '/' + post.month() + '/index.htm', 0644)
    
    # Create a new page for the post's year.
    year_page = Page()
    year_page.title = 'Posts from ' + str(post.year()) + ' | ' + year_page.title
    year_body = ""

    # Insert all the posts for that year into the body sorted reverse chronologically.
    for p in sorted(year_catch, key=lambda p: p.time, reverse = True):
      year_body += p.formatted()
    year_page.body = year_body

    # Write out the index page for the post's year.
    y = open(build_folder + '/' + post.year() + '/index.htm', "w")
    y.writelines(year_page.formatted())
    y.close
    os.chmod(build_folder + '/' + post.year() + '/index.htm', 0644)
    
    # Use crunch_home to rebuild the home page just to be sure that the new post 
    # hasn't affected it.
    if args.verbose: print 'Rebuilding the home page.'    
    crunch_home()
    
    # Rebuild the feed, just in case.
    if args.verbose: print 'Rebuilding the feed.'
    crunch_feed()

  return post

# confirmation_email() sends an email that confirms that a post has been created.
# only used for --email, but might be extended elsewhere.
def confirmation_email(post):
  if args.verbose: print 'Sending a confirmation email.'

  # Use sendmail and send email via the command line.
  sendmail_location = '/usr/sbin/sendmail'

  # Open sendmail and create a file-like object (p) for STDIN.
  p = os.popen(sendmail_location + ' -t', 'w')

  # Write out the email to p.
  p.write("From: " + conf['email_receiver'] + '\n')
  p.write('To: ' + conf['email_sender'] + '\n')
  p.write('Subject: Created "' + post.title + '"\n')
  p.write('\n')
  p.write('"' + post.title + '" created.\n' + 
          'pretty_date: "' + post.date_pretty() + '"\n' +
          'slug: "' + post.slug + '"\n' +
          'filename: "' + post.filename + '"\n' + 
          'body: \n\n' + post.content)
  
  # Close p and send the email
  p.close
    

# crunch_feed() will generate an rss feed for the site.
def crunch_feed():
  if args.verbose: print 'Crunch RSS feed.'

  # Get recent posts.  
  if args.verbose: print '\tGet all the required posts.'
  post_list = get_recent(conf['feed_count'])
                  
  if args.verbose: print '\tGenerating the new feed.'

  # Make an empty body variable
  body = ''
   
  # Add all the xml formatted posts to the body.
  for post in post_list:
    body += post.xml()

  # Make a new page object.
  page = Page()
  
  # Add in the new body.
  page.body = body

  # Write out the post to the new file.
  if args.verbose: print '\tWriting out the feed.'
  f = open(build_folder + '/index.xml' , 'w')
  f.writelines(page.xml())
  f.close
  os.chmod(build_folder + '/index.xml', 0644)  

# Create a specific gallery matching a string identifier.
def crunch_gallery(name):
  if args.verbose: print 'Crunching gallery "' + name + '".'
  
  if not os.path.exists(galleries_folder + '/' + name):
    print 'ERROR: Gallery ' + name + ' does not exist.'
    return 1

  # Define some allowable image extensions.
  image_extensions = ('.jpg', '.jpeg', '.gif', '.png')

  # Make a destination gallery.
  if not os.path.exists(build_folder + '/' + conf['galleries_folder'] + '/' + name):
    os.mkdir(build_folder + '/' + conf['galleries_folder'] + '/' + name)
    os.chmod(build_folder + '/' + conf['galleries_folder'] + '/' + name, 0755)

  images = ''
  
  # Run through the files in the directory.
  for file in os.listdir(galleries_folder + '/' + name):

    # Process the meta data file.
    if file == 'meta.yaml':
      if args.verbose: print '\tProcessing metadata.'
      
      a = open(galleries_folder + '/' + name + '/' + file, \
        'r').read().split('\n\n', 1)               
      
      y = yaml.load(a[0])
      
      try:
        description = '<div class="eleven columns">' + \
          markdown2.markdown(str(a[1]), extras=["code-color", "code-friendly"])  
      except:
        description = '<div class="eleven columns">'
  
    # Copy all the images.
    if filter(file.endswith, image_extensions):
      if args.verbose: print '\tCopying image ' + file
      shutil.copy(galleries_folder + '/' + name + '/' + file, 
                  build_folder + '/'+ conf['galleries_folder'] + '/' + name + '/' + file)
    
      if not re.search('_z', file) and not re.search('_thm', file):
        i = Gallery_Image()
        i.master_image = file
        i.gallery_name = name
        
        p = Page()
      
        images += i.formatted_thumb()
        p.body = i.formatted_single()
        
        f = open(build_folder + '/' + conf['galleries_folder'] + '/' + name + '/' + \
          i.name() + '.htm', 'w')
        f.writelines(p.formatted())
        f.close
        os.chmod(build_folder + '/' + conf['galleries_folder'] + '/' + name + '/' + \
          i.name() + '.htm', 0644)
   
   
  images += "</div>"
   
  gal_page = Page()
  
  leader = '<div class="eleven columns">\n<h3>' + str(y['title']) + \
    '</h3>\n<p class="small">' + \
    time.strftime("posted on %Y-%m-%d at %I:%M %p", \
    time.localtime(float(y['date']))) + '</p></div>'
  
  gal_page.body = leader + description + images
  
  gal_page.title = str(y['title']) + ' | ' + gal_page.title
  
  f = open(build_folder + '/' + conf['galleries_folder'] + '/' + name + '/index.htm', 'w')
  f.writelines(gal_page.formatted())
  f.close
  os.chmod(build_folder + '/' + conf['galleries_folder'] + '/' + name + \
    '/index.htm', 0644)
  
  
  
# Run crunch_gallery() for all galleries in the conf['galleries_folder'] folder.
def crunch_gallery_all():
  if args.verbose: print 'Building all galleries.'
  
  for dir in [x[0] for x in os.walk(galleries_folder)]:
    if not re.search(conf['galleries_folder'] + '$', dir):
      crunch_gallery(os.path.basename(dir))

      
      
      
# Combine and minify CSS and JS.
def crunch_extras():
  if args.verbose: print 'Combining and minifying stylesheets and scripts.'
  
  # Make some empty variables to put the minified content in.
  css_min = []
  js_min = []
  
  # Iterate through the css files.
  for file in sorted(os.listdir(css_folder)):
    
    # Ignore excluded files. 
    if not file.startswith('_'):
      
      # Only Process all the non-minified CSS files.
      if file.endswith('.css') and not file.endswith('.min.css'):
      
        # Read the file into a tmp var.
        tmp = open(css_folder + '/' + file).read()
        
        # Kill all the comments.
        tmp = re.sub( r'/\*[\s\S]*?\*/', '', tmp)
        
        # Minimize the whitespace.
        tmp = ' '.join(tmp.split())
        
        # Add it to the new file.
        css_min.append(tmp)
      
      # If the file is minified, we still want it but don't want to waste time.
      if file.endswith('.min.css'):
        css_min.append(open(css_folder + '/' + file).read())
      
    # If the file is excluded just copy it over.
    if file.startswith('_'):
      shutil.copy2(css_folder + '/' + file, build_folder + '/' + \
        conf['css_folder'] + '/' + file.lstrip('_'))      
  
  # Write out our new minified CSS file.
  f = open(build_folder + '/' + conf['css_folder'] + '/app.css', 'w')
  f.writelines(''.join(css_min))
  f.close
  os.chmod(build_folder + '/' + conf['css_folder'] + '/app.css', 0644)      
      
  # Iterate through JS files.
  for file in sorted(os.listdir(scripts_folder)):
  
    # Ignore excluded files.
    if not file.startswith('_'):
      
      # Only bother with JS files and ignore pre-minified ones.
      if file.endswith('.js') and not file.endswith('.min.js'):
        # Read the file into a tmp var.
        for line in open(scripts_folder + '/' + file).readlines():
      
          # Ignore comments lines.
          if not re.match('//', line) and not re.match('\s+//', line):
              
              # minimize whitespace
              line = ' '.join(line.split())          
              
              # add the minimized js to the new file
              js_min.append(line)

        # Kill all the comments.
        #tmp = re.sub( r'\/\*.+?\*\/|\/\/.*(?=[\n\r])', "", tmp)
        
        # Minimize the whitespace. Can't eliminate as some is critical.
        # Cannot be used unless comments are removed.
        #tmp = re.sub(r'\s+', ' ', tmp)
              
        #js_min.append(tmp)
      
      # Included the minified js file, but don't process it.
      if file.endswith('.min.js'):
        js_min.append(open(scripts_folder + '/' + file).read())
        
    # Copy excluded files straight over with no changes.
    if file.startswith('_'):
      shutil.copy2(scripts_folder + '/' + file, build_folder + '/' + \
        conf['scripts_folder'] + '/' + file.lstrip('_'))
    
  # Write out our new minified JS file.
  f = open(build_folder + '/' + conf['scripts_folder'] + '/app.js', 'w')
  f.writelines(''.join(js_min))
  f.close
  os.chmod(build_folder + '/' + conf['scripts_folder'] + '/app.js', 0644)

    
  
  
  
##########################################################################################
### Party Time.
##########################################################################################
def main():
  # Setup a new blog structure.
  if args.setup:
    sys.stderr.write('This build case not implemented yet.\nPlease build with --clean.\n')
    sys.exit()
  
  # Clean out the build folder.
  if args.clean:
    crunch_clean()
  
  # Process an email message that is fed in through STDIN.
  if args.email:
    # Ensure that we have a build folder to use.
    ensure_build_folder()
  
    # Crunch the email and grab the new filename.
    filename = crunch_email(email.message_from_string(sys.stdin.read()))
  
    # Crunch the new post file and pass back the post object.
    post = crunch_single(open(filename).read())
  
    # Use the post object to send a confirmation email.
    confirmation_email(post)
    
    
  else:
    # Just process a single post file.
    if args.single:
      #ensure_build_folder()
      #crunch_single()
      sys.stderr.write('This build case not implemented yet.\n')
    else:  
  
      # Re-process everything.
      if args.all:
        if args.verbose: print 'Building all the things.'
        # Make sure we have a build folder to use.
        ensure_build_folder()
        
        # Rebuild the error pages
        crunch_errors()
  
        # Rebuild all the static pages.
        crunch_pages()
  
        # Rebuild all posts.
        crunch_posts()
  
        # Rebuild all the indexes.
        crunch_indexes()
  
        # Rebuild the home page. 
        crunch_home()
        
        # Rebuild the feed.
        crunch_feed()
        
        # Rebuild the extras.
        crunch_extras()
        
        # Build the galleries.
        crunch_gallery_all()
      
      # We're going to do a partial rebuild.
      elif args.posts or args.home or args.indexes or args.feed or args.galleries or \
        args.pages or args.extras:
        
        ensure_build_folder()
        
        if args.verbose: print 'Selectively building.'
        
        # Build error pages if the --error flag is set
        if args.error:
          crunch_errors()
          
        # Build static pages if the --pages flag is set
        if args.pages:
          crunch_pages()
        
        # Build posts if the --posts flag is set.    
        if args.posts:
          crunch_posts()    
        
        # Build home if the --home flag is set.
        if args.home:
          crunch_home()
  
        # Build indexes if the --indexes flag is set.
        if args.indexes:
          crunch_indexes()
          
        # Build the feed if the --feed flag is set.
        if args.feed:
          crunch_feed()
          
        # Build the extras if the --extras flag is set.
        if args.extras:
          crunch_extras()
          
        # Build the galleries if the --galleries flag is set.
        if args.galleries:
          crunch_gallery_all()
  
  # Start up a uber-simple webserver to test the build on localhost. 
  if args.serve:
  
    # Pull in the modules we need.
    try:
      import SimpleHTTPServer
      import SocketServer
    except:
      print 'Please ensure that the SimpleHTTPServer and SocketServer modules are \
            installed to enable the built in webserver.'
  
    # Make sure there's a build folder to serve.
    ensure_build_folder()
  
    if args.verbose: print 'Starting server.'
  
    # Create a simple handler for HTTP GET requests.
    class myHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
      def do_GET(self):
        if args.verbose: print self.path
  
        # For permalink compatibility, create a redirect so that '.htm' 
        # isn't necessary for post pages. Enable with server_redirect_htm in 
        # the configuration file.
        if conf['server_redirect_htm']:
          if re.match('/\d\d\d\d\/\d\d\/\w', self.path):
            self.path = self.path + '.htm'
            if args.verbose: print 'redirecting to ' + self.path
              
        return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
    
    # Use the handler class and setup a SocketServer instance.
    handler = myHandler
    
    server = False
    
    while server == False:
      try:
        server = SocketServer.TCPServer(("", conf['server_port']), handler)
      except:
        print "Port occupied... Retrying."
        time.sleep(5)
         
    # Change to the build folder. 
    os.chdir(build_folder)
  
    # Start up the server.
    if args.verbose: print 'Server going live on port', conf['server_port']
    server.serve_forever()

if __name__ == "__main__":
  main()
   
### End Program Stuff ###
