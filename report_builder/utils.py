import copy
from django.conf import settings

def javascript_date_format(python_date_format):
    format = python_date_format.replace(r'Y', 'yyyy')
    format = format.replace(r'm', 'mm')
    format = format.replace(r'd', 'dd')
    if not format:
        format = 'yyyy-mm-dd'
    return format

def duplicate(obj, changes=None):
    """ Duplicates any object including m2m fields
    changes: any changes that should occur, example
    changes = (('fullname','name (copy)'), ('do not copy me', ''))"""

    if not obj.pk:
        raise ValueError('Instance must be saved before it can be cloned.')

    duplicate = copy.copy(obj)

    duplicate.pk = None

    for change in changes:
        duplicate.__setattr__(change[0], change[1])

    duplicate.save()

    # trick to copy ManyToMany relations.
    for field in obj._meta.many_to_many:
        source = getattr(obj, field.attname)
        destination = getattr(duplicate, field.attname)
        for item in source.all():
            try: # m2m, through fields will fail.
                destination.add(item)
            except: pass
    return duplicate

def get_model_manager():
    """ 
    Get  manager from settings else use objects
    """
    model_manager = 'objects'

    if getattr(settings, 'REPORT_BUILDER_MODEL_MANAGER', False):
        model_manager = settings.REPORT_BUILDER_MODEL_MANAGER

    return model_manager

def get_allowed_models():
    models = ContentType.objects.all()
    if getattr(settings, 'REPORT_BUILDER_INCLUDE', False):
        models = models.filter(name__in=settings.REPORT_BUILDER_INCLUDE)
    if getattr(settings, 'REPORT_BUILDER_EXCLUDE', False):
        models = models.exclude(name__in=settings.REPORT_BUILDER_EXCLUDE)
    return models


    