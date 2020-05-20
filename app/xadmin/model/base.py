# coding=utf8
from datetime import datetime
from flask_mongoengine import MongoEngine, BaseQuerySet
from flask_login import current_user


db = MongoEngine()


class Document(db.Document):
    meta = {'abstract': True,
            'queryset_class': BaseQuerySet}

    def _save_create(self, doc, force_insert, write_concern):
        if 'owner' in self._fields:
            doc['owner'] = current_user.to_dbref()
        if 'created' in self._fields:
            doc['created'] = datetime.now()
        return super(Document, self)._save_create(doc, force_insert, write_concern)

    def _save_update(self, doc, save_condition, write_concern):
        if 'created' in self._fields:
            del doc['created']
        if 'updated' in self._fields:
            doc['updated'] = datetime.now()
        return super(Document, self)._save_update(doc, save_condition, write_concern)
