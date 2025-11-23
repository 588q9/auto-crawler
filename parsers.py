from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from bs4 import BeautifulSoup


COURSE_LINK_RE = re.compile(r"/course/view\.php\?id=(\d+)")


@dataclass
class Course:
    id: Optional[int]
    name: str
    url: str


def _dedupe(courses: List[Course]) -> List[Course]:
    uniq = {}
    for c in courses:
        key = c.id or c.url
        if key not in uniq:
            uniq[key] = c
    return list(uniq.values())


def parse_overview_courses(html: str) -> List[Course]:
    """Parse courses strictly from the '课程概览' (block myoverview) on /my/.

    Only returns courses that appear inside the myoverview block to match user's intent.
    """
    soup = BeautifulSoup(html, "lxml")

    # Find possible containers for myoverview block across Moodle variants
    containers = []
    containers.extend(soup.select("section#block-myoverview"))
    containers.extend(soup.select("div#block-myoverview"))
    containers.extend(soup.select("div.block_myoverview, section.block_myoverview"))
    containers.extend(soup.find_all(id=re.compile(r"^block-myoverview")))

    courses: List[Course] = []
    seen_urls = set()

    def consider_anchor(a):
        href = a.get("href")
        if not href:
            return
        m = COURSE_LINK_RE.search(href)
        if not m:
            return
        name = a.get_text(strip=True) or a.get("title") or href
        try:
            cid = int(m.group(1))
        except Exception:
            cid = None
        if href in seen_urls:
            return
        seen_urls.add(href)
        courses.append(Course(id=cid, name=name, url=href))

    for container in containers:
        for a in container.select("a[href]"):
            consider_anchor(a)

    return _dedupe(courses)


# Backward-compatible function name for other callers; now focuses on overview first
def parse_my_courses(html: str) -> List[Course]:
    courses = parse_overview_courses(html)
    return courses


# -------------------- course page parsers --------------------
@dataclass
class VideoItem:
    id: int
    name: str
    url: str
    incomplete: Optional[bool] = None


FSRESOURCE_LINK_RE = re.compile(r"/mod/fsresource/view\.php\?id=(\d+)")


def parse_course_fsresources(html: str) -> List[VideoItem]:
    """Parse fsresource video items from a course view page.

    Tries to detect completion state via moodle activity DOM.
    """
    soup = BeautifulSoup(html, "lxml")
    items: List[VideoItem] = []

    # Each activity is often in li.activity with classes and a link
    for li in soup.select("li.activity"):
        # Heuristic A: anchor directly to fsresource
        a = li.select_one("a[href*='mod/fsresource/view.php?id=']")
        href = a.get("href") if a else None
        vid: Optional[int] = None
        name: Optional[str] = None

        m = FSRESOURCE_LINK_RE.search(href or "")
        if m:
            vid = int(m.group(1))
            name = a.get_text(strip=True) or a.get("title")

        # Heuristic B: video icon present (theme image f/video), use data-id
        icon = li.select_one("img.activityicon") or li.select_one("img.activityicon.nofilter")
        if icon:
            src = icon.get("src", "")
            if "/f/video" in src:
                if vid is None:
                    try:
                        vid = int(icon.get("data-id"))
                    except Exception:
                        vid = None
                if name is None:
                    inst = li.select_one(".instancename") or li.select_one(".activityinstance .instancename")
                    name = inst.get_text(strip=True) if inst else None
                if href is None and vid is not None:
                    href = f"/mod/fsresource/view.php?id={vid}"

        # Skip if still not a video fsresource
        if vid is None:
            continue
        name = name or f"fsresource-{vid}"

        # Detect completion state
        incomplete: Optional[bool] = None
        comp = li.select_one(".activity-completion")
        if comp:
            state_attr = comp.get("data-completionstate") or comp.get("data-state")
            if state_attr is not None:
                try:
                    incomplete = (int(state_attr) == 0)
                except Exception:
                    pass
            else:
                # Look at icon class
                classes = " ".join(comp.get("class", []))
                if "completed" in classes:
                    incomplete = False
                elif "incomplete" in classes or "notcompleted" in classes:
                    incomplete = True

        # Heuristic C: presence of 待办事项 button implies incomplete
        if incomplete is None:
            todo_btn = li.find("button", string=lambda s: isinstance(s, str) and "待办事项" in s)
            if todo_btn:
                incomplete = True

        items.append(VideoItem(id=vid, name=name, url=href or f"/mod/fsresource/view.php?id={vid}", incomplete=incomplete))

    # Fallback: any link in page
    if not items:
        for a in soup.find_all("a", href=True):
            m = FSRESOURCE_LINK_RE.search(a["href"])
            if m:
                vid = int(m.group(1))
                name = a.get_text(strip=True) or a.get("title") or f"fsresource-{vid}"
                items.append(VideoItem(id=vid, name=name, url=a["href"], incomplete=None))

    # Deduplicate by id
    uniq = {}
    for it in items:
        if it.id not in uniq:
            uniq[it.id] = it
    return list(uniq.values())
