# coding=utf8
import mongoengine
from mongoengine.base import get_document
from flask_admin._compat import string_types, as_unicode, iteritems
from flask_admin.model.ajax import DEFAULT_PAGE_SIZE
from flask_admin.contrib.mongoengine import ajax


class QueryAjaxModelLoader(ajax.QueryAjaxModelLoader):

    def get_list(self, term, offset=0, limit=DEFAULT_PAGE_SIZE, **kwargs):
        query = kwargs.get('query', self.model.objects)
        filters = (self.options and self.options.get('filters')) or {}
        if kwargs.get('filters'):
            filters.update(kwargs['filters'])
        if filters:
            query = query.filter(**filters)

        criteria = None
        if term:
            for field in self._cached_fields:
                flt = {u'%s__icontains' % field.name: term}

                if not criteria:
                    criteria = mongoengine.Q(**flt)
                else:
                    criteria |= mongoengine.Q(**flt)

            query = query.filter(criteria)

        order_by = kwargs.get('order_by', self.options.get('order_by'))
        if order_by:
            query.order_by(order_by)

        if offset:
            query = query.skip(offset)

        return query.limit(limit).all()

    def format(self, model, key_field=None):
        if not model:
            return None
        if not key_field:
            key_field = self.options.get('key', 'id')
        key = getattr(model, key_field)
        return (as_unicode(key), as_unicode(model))


def create_ajax_loader(model, name, field_name, opts):
    # print('create_ajax_loader => ', field_name, name, opts)
    if field_name == '__self__':
        return QueryAjaxModelLoader(name, model, **opts)

    prop = getattr(model, field_name, None)
    remote_model = opts.pop('model', None)

    if prop is None:
        if remote_model:
            if isinstance(remote_model, string_types):
                remote_model = get_document(remote_model)
            if remote_model:
                return QueryAjaxModelLoader(name, remote_model, **opts)

        raise ValueError('Model %s does not have field %s.' % (model, field_name))

    ftype = type(prop).__name__

    if ftype == 'ListField' or ftype == 'SortedListField':
        prop = prop.field
        ftype = type(prop).__name__

    if ftype == 'ReferenceField':
        remote_model = prop.document_type
    else:
        if remote_model:
            if isinstance(remote_model, string_types):
                remote_model = get_document(remote_model)
        if not remote_model:
            raise ValueError('Dont know how to convert %s type for AJAX loader' % ftype)
    # print(' after create_ajax_loader => ', remote_model, field_name, name, opts)
    return QueryAjaxModelLoader(name, remote_model, **opts)


def process_ajax_references(references, view):
    def make_name(base, name):
        if base:
            return ('%s-%s' % (base, name)).lower()
        else:
            return as_unicode(name).lower()

    def handle_field(field, subdoc, base):
        ftype = type(field).__name__

        if ftype == 'ListField' or ftype == 'SortedListField':
            child_doc = getattr(subdoc, '_form_subdocuments', {}).get(None)

            if child_doc:
                handle_field(field.field, child_doc, base)
        elif ftype == 'EmbeddedDocumentField':
            result = {}

            ajax_refs = getattr(subdoc, 'form_ajax_refs', {})

            for field_name, opts in iteritems(ajax_refs):
                child_name = make_name(base, field_name)

                if isinstance(opts, dict):
                    loader = create_ajax_loader(field.document_type_obj, child_name, field_name, opts)
                else:
                    loader = opts

                result[field_name] = loader
                references[child_name] = loader

            subdoc._form_ajax_refs = result

            child_doc = getattr(subdoc, '_form_subdocuments', None)
            if child_doc:
                handle_subdoc(field.document_type_obj, subdoc, base)
        else:
            raise ValueError('Failed to process subdocument field %s' % (field,))

    def handle_subdoc(model, subdoc, base):
        documents = getattr(subdoc, '_form_subdocuments', {})

        for name, doc in iteritems(documents):
            field = getattr(model, name, None)

            if not field:
                raise ValueError('Invalid subdocument field %s.%s' % (model, name))

            handle_field(field, doc, make_name(base, name))

    handle_subdoc(view.model, view, '')

    return references
