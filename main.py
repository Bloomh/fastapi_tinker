from fastapi import FastAPI, Response, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import httpx
import xml.etree.ElementTree as ET
from pathlib import Path

# Create the templates directory if it doesn't exist
templates_dir = Path("templates")
templates_dir.mkdir(exist_ok=True)

# Create the static directory if it doesn't exist
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Regular expression to extract paper details from XML
TITLE_PATTERN = r'<title[^>]*>([^<]+)</title>'
SUMMARY_PATTERN = r'<summary[^>]*>([^<]+)</summary>'
AUTHOR_PATTERN = r'<name[^>]*>([^<]+)</name>'

def get_paper(id: str):
    """Fetch paper details from arXiv API and extract relevant information."""
    url = f"http://export.arxiv.org/api/query?id_list={id}"
    
    try:
        response = httpx.get(url)
        
        if response.status_code != 200:
            return {"error": f"Failed to fetch paper: HTTP {response.status_code}"}
        
        # Check if the paper exists (contains entry elements)
        xml_content = response.text
        if "<entry" not in xml_content:
            return {"error": "No paper found with this ID"}
        
        # Parse the XML
        # Add namespaces to properly parse the XML
        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }
        
        root = ET.fromstring(xml_content)
        
        # Find the entry element (paper details)
        entry = root.find('.//atom:entry', namespaces)
        
        if entry is None:
            return {"error": "Could not parse paper details"}
        
        # Extract paper details
        title = entry.find('./atom:title', namespaces)
        title_text = title.text.strip() if title is not None and title.text else "Unknown Title"
        
        summary = entry.find('./atom:summary', namespaces)
        summary_text = summary.text.strip() if summary is not None and summary.text else "No summary available"
        
        authors = []
        for author in entry.findall('./atom:author/atom:name', namespaces):
            if author.text:
                authors.append(author.text.strip())
        
        # Get the DOI if available
        doi = None
        for link in entry.findall('./atom:link', namespaces):
            if link.get('title') == 'doi':
                doi = link.get('href')
                break
        
        # Get the PDF link
        pdf_link = None
        for link in entry.findall('./atom:link', namespaces):
            if link.get('title') == 'pdf':
                pdf_link = link.get('href')
                break
        
        # Get the published date
        published = entry.find('./atom:published', namespaces)
        published_date = published.text if published is not None and published.text else None
        
        # Get categories/tags
        categories = []
        for category in entry.findall('./atom:category', namespaces):
            term = category.get('term')
            if term:
                categories.append(term)
        
        return {
            "id": id,
            "title": title_text,
            "summary": summary_text,
            "authors": authors,
            "published_date": published_date,
            "categories": categories,
            "doi": doi,
            "pdf_link": pdf_link,
            "url": f"https://arxiv.org/abs/{id}"
        }
    except Exception as e:
        return {"error": f"Error parsing paper: {str(e)}"}

@app.get("/{_}/{id}")
async def read_item(id: str):
    paper = get_paper(id)

    return paper