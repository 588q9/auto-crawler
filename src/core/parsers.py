from dataclasses import dataclass
from typing import List, Optional
from bs4 import BeautifulSoup


@dataclass
class Course:
    id: Optional[int]
    name: str
    url: str


@dataclass
class VideoItem:
    id: int
    name: str
    url: str
    incomplete: Optional[bool]


def parse_overview_courses(html: str) -> List[Course]:
    soup = BeautifulSoup(html, "lxml")
    courses = []
    
    course_cards = soup.select(".course-card, .coursebox, [data-course-id]")
    for card in course_cards:
        link = card.find("a", href=True)
        if link:
            href = link["href"]
            name = link.get_text(strip=True) or link.get("title", "")
            
            course_id = None
            id_match = re.search(r'id=(\d+)', href)
            if id_match:
                course_id = int(id_match.group(1))
            
            courses.append(Course(id=course_id, name=name, url=href))
    
    if not courses:
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/course/view.php?id=" in href:
                name = link.get_text(strip=True) or link.get("title", "")
                course_id = None
                id_match = re.search(r'id=(\d+)', href)
                if id_match:
                    course_id = int(id_match.group(1))
                courses.append(Course(id=course_id, name=name, url=href))
    
    return courses


def parse_course_fsresources(html: str) -> List[VideoItem]:
    soup = BeautifulSoup(html, "lxml")
    items = []
    
    fsresource_links = soup.find_all("a", href=re.compile(r'/mod/fsresource/view\.php\?id=\d+'))
    for link in fsresource_links:
        href = link["href"]
        name = link.get_text(strip=True) or link.get("title", "")
        
        video_id = None
        id_match = re.search(r'id=(\d+)', href)
        if id_match:
            video_id = int(id_match.group(1))
        
        incomplete = None
        parent = link.find_parent("li", class_=re.compile(r'incomplete|notcompleted'))
        if parent:
            incomplete = True
        else:
            parent = link.find_parent("li", class_=re.compile(r'complete|completed'))
            if parent:
                incomplete = False
        
        items.append(VideoItem(id=video_id, name=name, url=href, incomplete=incomplete))
    
    return items
