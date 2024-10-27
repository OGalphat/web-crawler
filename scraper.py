import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup, Comment
from database import Database as db
from robot_parser import RobotParser 

# list of valid domains to check for
valid_domains = [
    "ics.uci.edu",
    "cs.uci.edu",
    "informatics.uci.edu",
    "stat.uci.edu",
    "today.uci.edu/department/information_computer_sciences"
]

def scraper(url, resp):
    links = extract_next_links(url, resp)
    valid_links = []
    robot_parsers = {}

    for link in links:
        if is_valid(link):
            # get the root domain of the current link
            root_domain = f"{urlparse(link).scheme}://{urlparse(link).netloc}"

            # check if RobotParser for this root domain already exists
            if root_domain not in robot_parsers:
                robot_parsers[root_domain] = RobotParser(root_domain)  # create and cache the RobotParser

            current_robot = robot_parsers[root_domain]

            # check if link is allowed by robots.txt and add to valid links if so
            if current_robot.is_allowed(link):
                valid_links.append(link)

            # append sitemaps (once per domain) to valid_links
            valid_links.extend(current_robot.sitemaps)

    return valid_links

def extract_next_links(url, resp):
    """
    Implementation required.
    url: the URL that was used to get the page
    resp.url: the actual url of the page
    resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    resp.error: when status is not 200, you can check the error here, if needed.
    resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
            resp.raw_response.url: the url, again
            resp.raw_response.content: the content of the page!
    Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    """
    # checks status status of the response
    if resp.status < 400 and resp.status >= 300:
        try:
            return list(resp.raw_response.url)
        except:
            pass # skips the url completely
    if (not resp.raw_response) or (not resp.raw_response.content) or (resp.status != 200) or (url in db.crawled_links) or (url in db.blacklist_links): # checks if its blanks or have been crawled already
        return list()

    soup_obj = BeautifulSoup(resp.raw_response.content, "html.parser")

    # removes all comment from the html file
    for comment in soup_obj.find_all(text = lambda text: isinstance(text, Comment)):
        comment.extract()

    # removes all <script> and <style> tags
    for tag_element in soup_obj.find_all(['script', 'style']):  
        tag_element.extract()

    # gets the actual text inside the HTML file
    raw_text = soup_obj.get_text()
    main_text = re.sub('\s+', ' ', raw_text)

    # checks if the file has low contextual value
    if len(main_text) < 150:
        db.blacklist_links.add(url)
        return list()

    links = db.find_unique_links(soup_obj)
    return list(links)

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)

        # conditions that would lead to the current link invalid
        if parsed.scheme not in set(["http", "https"]): # ensures that it is using a secure scheme
            return False
        
        if parsed.netloc not in valid_domains: 
            return False

        if url in db.blacklist_links: 
            return False
        
        if any(substring in url for substring in ("?share=", "pdf", "redirect", "#comment", "#respond", "#comments")):
            return False

        # add another if to check if the url is allowed to be crawled based on the robots.txt?
        
        if re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower()): return False
        
        # url is valid if it passes all the conditions above
        # url can be added to the scraped
        db.crawled_links.add(url)

        return True

    except TypeError:
        print ("TypeError for ", parsed)
        raise
