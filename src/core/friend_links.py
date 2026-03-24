"""Friend links model - business logic for managing friend links"""
from typing import List, Dict


class FriendLinksModel:
    """Business logic for friend links management"""

    def __init__(self):
        self._links = []

    def load_from_data(self, data: List[Dict]) -> None:
        """Load from persisted data"""
        self._links = data

    def get_links(self) -> List[Dict]:
        """Get all links"""
        return self._links

    def add_link(self, name: str, url: str) -> bool:
        """Add a new link"""
        if not name.strip():
            return False
        if not url.strip():
            return False

        self._links.append({
            "name": name.strip(),
            "url": url.strip(),
        })
        return True

    def remove_link(self, index: int) -> bool:
        """Remove a link by index"""
        if 0 <= index < len(self._links):
            del self._links[index]
            return True
        return False

    def update_link(self, index: int, name: str, url: str) -> bool:
        """Update a link by index"""
        if not name.strip():
            return False
        if not url.strip():
            return False
        if not (0 <= index < len(self._links)):
            return False

        self._links[index] = {
            "name": name.strip(),
            "url": url.strip(),
        }
        return True

    def validate_url(self, url: str) -> bool:
        """Validate URL format - must start with http:// or https://"""
        url = url.strip()
        if not url:
            return False
        return url.startswith('http://') or url.startswith('https://')

    def clear_all(self) -> None:
        """Clear all links"""
        self._links = []

    def get_data_for_saving(self) -> List[Dict]:
        """Get data for saving"""
        return self._links
