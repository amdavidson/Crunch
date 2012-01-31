# Crunch README

Crunch is a python based command line utility that allows for manual rebuilding of posts, 
index pages, error pages and the home page. It also supports parsing email to create new 
posts. It was created to run amdavidson.com.

The configuration is stored in a file called conf.yaml in the same directory as crunch.

An example configuration follows:

  # extension defines the extension to be used by all the post files.
  extension: .md
  # server_port defines the port to be used by the built in web server.
  server_port: 8000
  # server_redirect_htm enables a redirect of ####/##/slug to ####/##/slug.htm for permalink compatibility.
  server_redirect_htm: True 
  # email_sender defines the address that all post emailed into the system should come from. set to nil to allow anyone to post.
  email_sender: andrew@amdavidson.com
  # email_receiver defines the address that posts are sent to and that the confirmation email should be sent from.
  email_receiver: no-reply@amd.im
  
  ### Site Configuration
  title: my awesome blog
  tagline: writing on the web, so you don't have to.
  author: You!
  description: I love blogging!
  base_url: http://awesomeblog.com/
  build_folder: built
  posts_folder: posts
  public_folder: public
  images_folder: images
  galleries_folder: galleries
  home_count: 5
  image_width: 640
  image_height: 640
  
A series of directories are used to structure the content used by crunch to generate the 
blog. 

The most important is the posts directory which uses a series of folders indicating the 
year with subfolders for the month. Files inside those subfolders are processed to create 
individual posts and the folder structure is used to layout the site.

The images folder can be used to store images for the site layout and for the posts 
themselves. The images/posts folder is used by the email parser to store images that it
encounters.

The galleries folder is not yet used. In the future this will be used to statically 
generate image galleries.

After running crunch the build folder (`built` in the above conf.yaml) will house the 
generated site and can be rsync'ed to the server for use.

It is in a very heavy state of development, but currently will create a fairly well 
functioning site. More to come...
