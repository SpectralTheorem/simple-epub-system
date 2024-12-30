from typing import List, Dict, Any, Optional, Tuple
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import logging
from pathlib import Path

logger = logging.getLogger('epub_navigation')

class NavPoint:
    """Represents a navigation point in the EPUB TOC."""
    def __init__(self, title: str, src: str, level: int = 0):
        self.title = title
        self.src = src  # Format: path#fragment or just path
        self.level = level
        self.children: List['NavPoint'] = []
        self.order: int = 0
        self.id: str = ""
        
    @property
    def path(self) -> str:
        """Get the file path part of the source."""
        return self.src.split('#')[0] if '#' in self.src else self.src
        
    @property
    def fragment(self) -> Optional[str]:
        """Get the fragment/anchor part of the source."""
        return self.src.split('#')[1] if '#' in self.src else None

class EpubNavigator:
    """Handles EPUB navigation parsing for both EPUB2 (NCX) and EPUB3 (nav.xhtml)."""
    
    def __init__(self, epub_path: Path):
        self.book = epub.read_epub(str(epub_path))
        self.nav_points: List[NavPoint] = []
        self.spine_items: List[epub.EpubItem] = []
        self._parse_navigation()
        self._parse_spine()
        
    def _parse_navigation(self):
        """Parse navigation from either EPUB3 nav.xhtml or EPUB2 NCX."""
        # Try EPUB3 nav first
        nav_item = next((item for item in self.book.get_items() 
                        if isinstance(item, epub.EpubNav)), None)
        
        if nav_item:
            self._parse_nav_xhtml(nav_item)
        else:
            # Fallback to EPUB2 NCX
            ncx_item = next((item for item in self.book.get_items() 
                           if isinstance(item, epub.EpubNcx)), None)
            if ncx_item:
                self._parse_ncx(ncx_item)
            else:
                logger.warning("No navigation document found in EPUB")
                
    def _parse_nav_xhtml(self, nav_item: epub.EpubNav):
        """Parse EPUB3 nav.xhtml navigation."""
        soup = BeautifulSoup(nav_item.get_content(), 'html.parser')
        nav = soup.find('nav', attrs={'epub:type': 'toc'})
        if not nav:
            return
            
        def process_nav_list(ol_elem, level=0) -> List[NavPoint]:
            points = []
            for li in ol_elem.find_all('li', recursive=False):
                a_elem = li.find('a')
                if not a_elem:
                    continue
                    
                nav_point = NavPoint(
                    title=a_elem.get_text(strip=True),
                    src=a_elem.get('href', ''),
                    level=level
                )
                
                # Process nested navigation
                nested_ol = li.find('ol')
                if nested_ol:
                    nav_point.children = process_nav_list(nested_ol, level + 1)
                    
                points.append(nav_point)
            return points
            
        nav_ol = nav.find('ol')
        if nav_ol:
            self.nav_points = process_nav_list(nav_ol)
            
    def _parse_ncx(self, ncx_item: epub.EpubNcx):
        """Parse EPUB2 NCX navigation."""
        soup = BeautifulSoup(ncx_item.get_content(), 'html.parser')
        
        def process_nav_point(nav_point_elem, level=0) -> Optional[NavPoint]:
            label_elem = nav_point_elem.find('navlabel')
            content_elem = nav_point_elem.find('content')
            
            if not (label_elem and content_elem):
                return None
                
            title = label_elem.find('text').get_text(strip=True)
            src = content_elem.get('src', '')
            
            nav_point = NavPoint(title=title, src=src, level=level)
            
            # Process nested navigation points
            for child_nav_point in nav_point_elem.find_all('navpoint', recursive=False):
                child = process_nav_point(child_nav_point, level + 1)
                if child:
                    nav_point.children.append(child)
                    
            return nav_point
            
        for nav_point_elem in soup.find_all('navpoint', recursive=False):
            nav_point = process_nav_point(nav_point_elem)
            if nav_point:
                self.nav_points.append(nav_point)
                
    def _parse_spine(self):
        """Parse the spine to get the reading order of content documents."""
        self.spine_items = []
        for spine_tuple in self.book.spine:
            # spine_tuple is (item_id, linear), we need to get the actual item
            item_id = spine_tuple[0] if isinstance(spine_tuple, tuple) else spine_tuple
            item = self.book.get_item_with_id(item_id)
            if item:
                self.spine_items.append(item)
                
    def get_ordered_nav_points(self) -> List[NavPoint]:
        """Get navigation points in reading order, flattening the hierarchy."""
        ordered_points: List[NavPoint] = []
        order = 1
        
        def process_point(point: NavPoint):
            nonlocal order
            point.order = order
            order += 1
            ordered_points.append(point)
            for child in point.children:
                process_point(child)
                
        for point in self.nav_points:
            process_point(point)
            
        return ordered_points
        
    def get_item_by_path(self, path: str) -> Optional[epub.EpubItem]:
        """Get an EPUB item by its path."""
        return next((item for item in self.book.get_items() 
                    if item.get_name() == path), None)
