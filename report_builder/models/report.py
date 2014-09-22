from report_builder.unique_slugify import unique_slugify
from django.db.models import Avg, Min, Max, Count, Sum
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from report_builder.utils import get_model_manager, get_allowed_models

from dateutil import parser
from django.db import models

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')

class Report(models.Model):
    """ 
    A saved report with queryset and descriptive fields
    """

    # def _get_model_manager(self):
    #     """ 
    #     Get  manager from settings else use objects
    #     """
    #     model_manager = 'objects'
    #     if getattr(settings, 'REPORT_BUILDER_MODEL_MANAGER', False):
    #         model_manager = settings.REPORT_BUILDER_MODEL_MANAGER
    #     return model_manager

    def get_allowed_models():
        models = ContentType.objects.all()
        if getattr(settings, 'REPORT_BUILDER_INCLUDE', False):
            models = models.filter(name__in=settings.REPORT_BUILDER_INCLUDE)
        if getattr(settings, 'REPORT_BUILDER_EXCLUDE', False):
            models = models.exclude(name__in=settings.REPORT_BUILDER_EXCLUDE)
        return models

    name = models.CharField(max_length=255)
    slug = models.SlugField(verbose_name="Short Name")
    description = models.TextField(blank=True)
    root_model = models.ForeignKey(ContentType, limit_choices_to={'pk__in':_get_allowed_models})
    created = models.DateField(auto_now_add=True)
    modified = models.DateField(auto_now=True)
    user_created = models.ForeignKey(AUTH_USER_MODEL, editable=False, blank=True, null=True)
    user_modified = models.ForeignKey(AUTH_USER_MODEL, editable=False, blank=True, null=True, related_name="report_modified_set")
    distinct = models.BooleanField(default=False)
    report_file = models.FileField(upload_to="report_files", blank=True)
    report_file_creation = models.DateTimeField(blank=True, null=True)
    starred = models.ManyToManyField(AUTH_USER_MODEL, blank=True,
                                     help_text="These users have starred this report for easy reference.",
                                     related_name="report_starred_set")

    
    
    

    def save(self, *args, **kwargs):
        if not self.id:
            unique_slugify(self, self.name)
        super(Report, self).save(*args, **kwargs)

    def add_aggregates(self, queryset):
        """
        Kyle O'Brien
        report_display_fields is the name of the reverse relationship from Report to DisplayField.
        We could technically change this (@TODO)
        annotate is a queryset function that allows us to aggregate data within the query set:
        eg. Entity.objects.annotate(number_of_accounts=Count('account'))
        This results in an additional 'column' in the returned results with the number of accounts
        associated to that user.
        """
        for display_field in self.report_display_fields.filter(aggregate__isnull=False):
            if display_field.aggregate == "Avg":
                queryset = queryset.annotate(Avg(display_field.path + display_field.field))
            elif display_field.aggregate == "Max":
                queryset = queryset.annotate(Max(display_field.path + display_field.field))
            elif display_field.aggregate == "Min":
                queryset = queryset.annotate(Min(display_field.path + display_field.field))
            elif display_field.aggregate == "Count":
                queryset = queryset.annotate(Count(display_field.path + display_field.field))
            elif display_field.aggregate == "Sum":
                queryset = queryset.annotate(Sum(display_field.path + display_field.field))
        return queryset
    
    def get_query(self):
        """
        Constructs the query to retrieve the report results
        """
        report = self
        # Remember that model_class() is technically being called on a ContentType object
        model_class = report.root_model.model_class()
        message= ""

        # Check for report_builder_model_manger property on the model
        if getattr(model_class, 'report_builder_model_manager', False):
            objects = getattr(model_class, 'report_builder_model_manager').all()
        else:
            # Get global model manager
            manager = get_model_manager()
            objects = getattr(model_class, manager).all()

        # Filters
        # NOTE: group all the filters together into one in order to avoid 
        # unnecessary joins
        filters = {}
        excludes = {}
        for filter_field in report.report_filter_fields.all():
            try:
                # exclude properties from standard ORM filtering 
                if '[property]' in filter_field.field_verbose:
                    continue
                if '[custom' in filter_field.field_verbose:
                    continue

                filter_string = str(filter_field.path + filter_field.field)
                
                if filter_field.filter_type:
                    filter_string += '__' + filter_field.filter_type
                
                # Check for special types such as isnull
                if filter_field.filter_type == "isnull" and filter_field.filter_value == "0":
                    filter_ = {filter_string: False}
                elif filter_field.filter_type == "in":
                    filter_ = {filter_string: filter_field.filter_value.split(',')}
                else:
                    # All filter values are stored as strings, but may need to be converted
                    if '[Date' in filter_field.field_verbose:
                        filter_value = parser.parse(filter_field.filter_value)
                        if settings.USE_TZ:
                            filter_value = timezone.make_aware(
                                filter_value,
                                timezone.get_current_timezone()
                            )
                        if filter_field.filter_type == 'range':
                            filter_value = [filter_value, parser.parse(filter_field.filter_value2)]
                            if settings.USE_TZ:
                                filter_value[1] = timezone.make_aware(
                                    filter_value[1],
                                    timezone.get_current_timezone()
                                )
                    else:
                        filter_value = filter_field.filter_value
                        if filter_field.filter_type == 'range':
                            filter_value = [filter_value, filter_field.filter_value2]
                    filter_ = {filter_string: filter_value}

                if not filter_field.exclude:
                    filters.update(filter_) 
                else:
                    excludes.update(filter_) 

            except Exception:
                import sys
                e = sys.exc_info()[1]
                message += "Filter Error on %s. If you are using the report builder then " % filter_field.field_verbose
                message += "you found a bug! "
                message += "If you made this in admin, then you probably did something wrong."

        if filters:
            objects = objects.filter(**filters)
        if excludes:
            objects = objects.exclude(**excludes)

        # Aggregates
        objects = self.add_aggregates(objects) 

        # Distinct
        if report.distinct:
            objects = objects.distinct()

        return objects, message
    
    @models.permalink
    def get_absolute_url(self):
        return ("report_update_view", [str(self.id)])
    
    def edit(self):
        return mark_safe('<a href="{0}"><img style="width: 26px; margin: -6px" src="{1}report_builder/img/edit.svg"/></a>'.format(
            self.get_absolute_url(),
            getattr(settings, 'STATIC_URL', '/static/')   
        ))
    edit.allow_tags = True
    
    def download_xlsx(self):
        if getattr(settings, 'REPORT_BUILDER_ASYNC_REPORT', False):
            return mark_safe('<a href="#" onclick="get_async_report({0})"><img style="width: 26px; margin: -6px" src="{1}report_builder/img/download.svg"/></a>'.format(
                self.id,
                getattr(settings, 'STATIC_URL', '/static/'),
            ))
        else:
            return mark_safe('<a href="{0}"><img style="width: 26px; margin: -6px" src="{1}report_builder/img/download.svg"/></a>'.format(
                reverse('report_download_xlsx', args=[self.id]),
                getattr(settings, 'STATIC_URL', '/static/'),
            ))
    download_xlsx.short_description = "Download"
    download_xlsx.allow_tags = True
    

    def copy_report(self):
        return '<a href="{0}"><img style="width: 26px; margin: -6px" src="{1}report_builder/img/copy.svg"/></a>'.format(
            reverse('report_builder.views.create_copy', args=[self.id]),
            getattr(settings, 'STATIC_URL', '/static/'),
        )
    copy_report.short_description = "Copy"
    copy_report.allow_tags = True

    def check_report_display_field_positions(self):
        """ After report is saved, make sure positions are sane
        """
        for i, display_field in enumerate(self.report_display_fields.all()):
            if display_field.position != i+1:
                display_field.position = i+1
                display_field.save()