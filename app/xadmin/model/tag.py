
from datetime import datetime
from .base import db, Document


class Tag(Document):
    name = db.StringField(max_length=10)
    created = db.DateTimeField(default=datetime.now())
    updated = db.DateTimeField()

    def __unicode__(self):
        return self.name
