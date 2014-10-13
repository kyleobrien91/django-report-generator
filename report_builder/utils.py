import copy
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
import inspect
from django.utils import timezone

def javascript_date_format(python_date_format):
    format = python_date_format.replace(r'Y', 'yyyy')
    format = format.replace(r'm', 'mm')
    format = format.replace(r'd', 'dd')
    if not format:
        format = 'yyyy-mm-dd'
    return format

def duplicate(obj, changes=None):
    """
    Duplicates any object including m2m fields
    changes: any changes that should occur, example
        changes = (('fullname','name (copy)'), ('do not copy me', ''))
    """
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
            except:
                pass

    return duplicate

def get_model_manager():
        """
        Get  manager from settings else use objects
        """
        from django.conf import settings

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

# ======================================================================================================================
# MODEL INTROSPECTION TYPE FUNCTIONS
# ======================================================================================================================

def isprop(v):
    return isinstance(v, property)


def get_properties_from_model(model_class):
    """ Show properties from a model """
    properties = []
    attr_names = [name for (name, value) in inspect.getmembers(model_class, isprop)]
    for attr_name in attr_names:
        if attr_name.endswith('pk'):
            attr_names.remove(attr_name)
        else:
            properties.append(dict(label=attr_name, name=attr_name.strip('_').replace('_',' ')))
    return sorted(properties, key=lambda k: k['label'])


def get_relation_fields_from_model(model_class, exclude = []):
    """ Get related fields (m2m, FK, and reverse FK) """
    relation_fields = []

    all_fields_names = model_class._meta.get_all_field_names()

    for field_name in all_fields_names:

        field = model_class._meta.get_field_by_name(field_name)

        exclude_class_names = []

        for excl in exclude:
            model_name = ContentType.objects.get_for_id(excl).model_class()._meta.model_name
            exclude_class_names.append(model_name)

        if field_name in exclude_class_names:
            continue

        field_object = field[0]
        is_direct = field[2]
        is_m2m = field[3]

        if is_m2m or not is_direct or hasattr(field_object, 'related'):
            # a related field
            if(hasattr(field_object, 'rel')):
                field_model_name = field_object.rel.to._meta.model_name
                field_object.field_ct = ContentType.objects.get(model=field_model_name)
            # If the field is actually a child class that's inherited from our current model
            elif type(field_object).__name__ is 'RelatedObject':
                field_model_name = field_object.model()._meta.model_name
                field_object.field_ct = ContentType.objects.get(model=field_model_name)
            else:
                field_object.field_ct = None

            field_object.field_name = field_name
            relation_fields += [field_object]

    return relation_fields


def get_direct_fields_from_model(model_class):
    """
    Direct, not m2m, not FK

    Interpreting indeces in get_all_field_names():
    Returns the (field_object, model, direct, m2m), where:
    - field_object is the Field instance for the given name,
    - model is the model containing this field (None for local fields),
    - direct is True if the field exists on this model and,
    - m2m is True for many-to-many relations.
    When 'direct' is False, 'field_object' is the corresponding RelatedObject for
    this field (since the field doesn't have an instance associated with it)
    """
    direct_fields = []

    all_fields_names = model_class._meta.get_all_field_names()

    for field_name in all_fields_names:
        field = model_class._meta.get_field_by_name(field_name)

        field_object = field[0]
        is_direct = field[2]
        is_m2m = field[3]
        field_object_name = field_object.__class__.__name__

        is_not_foreign_key = field_object_name != "ForeignKey"

        if is_direct and not is_m2m and is_not_foreign_key:
            direct_fields += [field_object]

    return direct_fields


def get_custom_fields_from_model(model_class):
    """ django-custom-fields support """
    if 'custom_field' in settings.INSTALLED_APPS:
        from custom_field.models import CustomField
        try:
            content_type = ContentType.objects.get(model=model_class._meta.module_name,app_label=model_class._meta.app_label)
        except ContentType.DoesNotExist:
            content_type = None
        custom_fields = CustomField.objects.filter(content_type=content_type)
        return custom_fields


def get_model_from_path_string(root_model, path):
    """
    Return a model class for a related model
    root_model is the class of the initial model
    path is like foo__bar where bar is related to foo
    """
    for path_section in path.split('__'):
        if path_section:
            field = root_model._meta.get_field_by_name(path_section)

            field_object = field[0]
            is_direct = field[2]

            if is_direct:
                root_model = field_object.related.parent_model()
            else:
                root_model = field_object.model

    return root_model

def get_aware_time(value):
    return timezone.make_aware(value, timezone.get_current_timezone())