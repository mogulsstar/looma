"""Source factory for creating update source instances."""

from typing import Dict, Type

from looma.core.constants import (
    SOURCE_ARTIFACTORY,
    SOURCE_GITHUB,
    SOURCE_GITLAB,
    SOURCE_HTTP,
    SOURCE_S3,
)
from looma.core.exceptions import NetworkError
from looma.sources.base import BaseSource


class SourceFactory:
    """
    Factory for creating source instances.
    
    Attributes
    ----------
    sources : dict
        Registry of available sources
    """
    
    def __init__(self):
        """Initialize the source factory."""
        self.sources: Dict[str, Type[BaseSource]] = {}
        self._register_default_sources()
    
    def _register_default_sources(self) -> None:
        """Register default update sources."""
        # Import here to avoid circular dependencies
        from looma.sources.github import GitHubSource
        from looma.sources.gitlab import GitLabSource
        from looma.sources.s3 import S3Source
        from looma.sources.artifactory import ArtifactorySource
        from looma.sources.http import HttpSource
        
        self.register(SOURCE_GITHUB, GitHubSource)
        self.register(SOURCE_GITLAB, GitLabSource)
        self.register(SOURCE_S3, S3Source)
        self.register(SOURCE_ARTIFACTORY, ArtifactorySource)
        self.register(SOURCE_HTTP, HttpSource)
    
    def register(self, name: str, source_class: Type[BaseSource]) -> None:
        """
        Register a new source type.
        
        Parameters
        ----------
        name : str
            Source name
        source_class : Type[BaseSource]
            Source class
        """
        self.sources[name] = source_class
    
    def create(self, name: str, config: Dict) -> BaseSource:
        """
        Create and configure a source instance.
        
        Parameters
        ----------
        name : str
            Source name
        config : dict
            Configuration dictionary
            
        Returns
        -------
        BaseSource
            Configured source instance
            
        Raises
        ------
        NetworkError
            If source is not found
        """
        if name not in self.sources:
            available = ", ".join(self.sources.keys())
            raise NetworkError(
                f"Unknown source: {name}. Available: {available}"
            )
        
        source_class = self.sources[name]
        return source_class(config)
    
    def list_sources(self) -> list:
        """
        List available sources.
        
        Returns
        -------
        list
            List of source names
        """
        return list(self.sources.keys())


# Global factory instance
source_factory = SourceFactory()