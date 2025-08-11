"""Update sources for Looma."""

from looma.sources.base import BaseSource
from looma.sources.factory import source_factory
from looma.sources.github import GitHubSource
from looma.sources.gitlab import GitLabSource
from looma.sources.s3 import S3Source
from looma.sources.artifactory import ArtifactorySource
from looma.sources.http import HttpSource

__all__ = [
    "BaseSource",
    "source_factory",
    "GitHubSource",
    "GitLabSource",
    "S3Source",
    "ArtifactorySource",
    "HttpSource",
]