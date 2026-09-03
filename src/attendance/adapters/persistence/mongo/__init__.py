"""Adaptadores de persistencia NoSQL."""

from attendance.adapters.persistence.mongo.client import MongoClientWrapper

__all__ = ["MongoClientWrapper"]
