import requests
from bs4 import BeautifulSoup
import html2text

url = "https://support.google.com/adspolicy/answer/6008942"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}
response = requests.get(url, headers=headers)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    # Get the main content area
    content = soup.find('div', {'class': 'article-content'}) or soup.body
    
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    markdown_content = converter.handle(str(content))
    
    with open('google_ads_policy.md', 'w') as f:
        f.write(markdown_content)
    print("Policy successfully saved to google_ads_policy.md")
else:
    print(f"Failed to fetch. Status code: {response.status_code}")
