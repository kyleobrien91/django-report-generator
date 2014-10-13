from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Avg, Min, Max, Count, Sum, Q
from report_builder.unique_slugify import unique_slugify
from django.template import loader, Context
from report_builder.models import FilterField
from report_builder.utils import get_allowed_models, get_model_manager
import operator
from functools import reduce

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')

class Report(models.Model):
    """
    A saved report with queryset and descriptive fields
    """
    name = models.CharField(max_length=255, verbose_name='Name')
    slug = models.SlugField(verbose_name="Short Name")
    description = models.TextField(blank=True, verbose_name='Description')
    created = models.DateField(auto_now_add=True)
    modified = models.DateField(auto_now=True)
    distinct = models.BooleanField(default=False)
    report_file = models.FileField(upload_to="report_files", blank=True)
    report_file_creation = models.DateTimeField(blank=True, null=True)

    root_model = models.ForeignKey(ContentType, limit_choices_to={'pk__in': get_allowed_models()})
    user_created = models.ForeignKey(AUTH_USER_MODEL, editable=False, blank=True, null=True)
    user_modified = models.ForeignKey(AUTH_USER_MODEL, editable=False, blank=True, null=True,
                                      related_name="report_modified_set")
    starred = models.ManyToManyField(AUTH_USER_MODEL, blank=True,
                                     help_text="These users have starred this report for easy reference.",
                                     related_name="report_starred_set")

    def save(self, *args, **kwargs):
        if not self.id:
            unique_slugify(self, self.name)
        super(Report, self).save(*args, **kwargs)

    def add_aggregates(self, queryset):
        """
        Updates the query set with any annotations if necessary. These will happen if any of the report's display fields
        are set to have an aggregate value
        :param queryset:
        :return:
        """
        all_display_fields = self.displayfield_set.filter(aggregate__isnull=False)

        for display_field in all_display_fields:

            is_avg = display_field.aggregate == "Avg"
            is_max = display_field.aggregate == "Max"
            is_min = display_field.aggregate == "Min"
            is_count = display_field.aggregate == "Count"
            is_sum = display_field.aggregate == "Sum"

            annotate_value = display_field.path + display_field.field

            annotated = None

            if is_avg:
                annotated = Avg(annotate_value)
            elif is_max:
                annotated = Max(annotate_value)
            elif is_min:
                annotated = Min(annotate_value)
            elif is_count:
                annotated = Count(annotate_value)
            elif is_sum:
                annotated = Sum(annotate_value)

            if annotated is not None:
                queryset = queryset.annotate(annotated)

        return queryset

    def get_query(self):
        """
        Builds the report's queryset
        :return: QuerySet Object, Error messages
        """
        report = self
        model_class = report.root_model.model_class()

        # Check for report_builder_model_manger property on the model
        if getattr(model_class, 'report_builder_model_manager', False):
            objects = getattr(model_class, 'report_builder_model_manager').all()
        else:
            # Get global model manager
            manager = get_model_manager()
            objects = getattr(model_class, manager).all()

        # Filters & exclude
        and_filters, or_filters, excludes, message = FilterField.get_report_filters(report)

        if and_filters:
            and_filters = [Q(x) for x in and_filters]
            objects = objects.filter(reduce(operator.and_, and_filters))
        if or_filters:
            or_filters = [Q(x) for x in or_filters]
            objects = objects.filter(reduce(operator.or_, or_filters))
        if excludes:
            objects = objects.exclude(**excludes)

        # Aggregates
        objects = self.add_aggregates(objects)

        # Distinct
        if report.distinct:
            objects = objects.distinct()

        return objects, message

    def get_absolute_url(self):
        """
        Returns the report's edit URL
        :return: SafeText
        """
        absolute_url = reverse("report_update_view", args=str(self.id))

        return absolute_url

    def edit(self):
        """
        Renders the html for the edit button as SafeText
        :return: SafeText
        """
        edit_link = self.get_absolute_url()
        static_url = getattr(settings, 'STATIC_URL', '/static/')

        t = loader.get_template('elements/edit_button.html')
        c = Context({
            'edit_link': edit_link,
            'static_url': static_url
        })

        return t.render(c)

    def download_xlsx(self):
        """
        Renders the html for the download button as SafeText
        :return: SafeText
        """
        report_id = self.id
        download_link = reverse('report_download_xlsx', args=[report_id])
        static_url = getattr(settings, 'STATIC_URL', '/static/')
        async = getattr(settings, 'REPORT_BUILDER_ASYNC_REPORT', False)

        if async is True:
            template = 'elements/download_button_async.html'
        else:
            template = 'elements/download_button.html'

        t = loader.get_template(template)
        c = Context({
            'report_id': report_id,
            'download_link': download_link,
            'static_url': static_url,
            'async': async
        })

        return t.render(c)

    def copy_report(self):
        """
        Renders the html for the copy button as SafeText
        :return: SafeText
        """
        copy_link = reverse('report_builder.views.create_copy', args=[self.id])
        static_url = getattr(settings, 'STATIC_URL', '/static/')

        t = loader.get_template('elements/copy_button.html')
        c = Context({
            'copy_link': copy_link,
            'static_url': static_url
        })

        return t.render(c)

    def check_report_display_field_positions(self):
        """
        After report is saved, make sure positions are sane
        """
        for i, display_field in enumerate(self.displayfield_set.all()):
            if display_field.position != i+1:
                display_field.position = i+1
                display_field.save()

    # ==============================================================================
    # Arbitrary model properties
    # ==============================================================================
    edit.allow_tags = True
    download_xlsx.short_description = "Download"
    download_xlsx.allow_tags = True
    copy_report.short_description = "Copy"
    copy_report.allow_tags = True
