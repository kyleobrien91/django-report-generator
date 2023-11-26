from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from dateutil import parser
from report_builder.utils import get_model_from_path_string, get_aware_time

from django.db.models import Q

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


class FilterField(models.Model):
    """
    A display field to show in a report. Always belongs to a Report
    """
    FT_EXACT = 'exact'
    FT_IEXACT = 'iexact'
    FT_CONTAINS = 'contains'
    FT_ICONTAINS = 'icontains'
    FT_IN = 'in'
    FT_GT = 'gt'
    FT_GTE = 'gte'
    FT_LT = 'lt'
    FT_LTE = 'lte'
    FT_STARTSWITH = 'startswith'
    FT_ISTARTSWITH = 'istartswith'
    FT_ENDSWITH = 'endswith'
    FT_IENDSWITH = 'iendswith'
    FT_RANGE = 'range'
    FT_WEEKDAY = 'week_day'
    FT_ISNULL = 'isnull'
    FT_REGEX = 'regex'
    FT_IREGEX = 'iregex'

    FILTER_TYPE_CHOICES = (
        (FT_EXACT, 'Equals'),
        (FT_IEXACT, 'Equals (Case Insensitive)'),
        (FT_CONTAINS, 'Contains'),
        (FT_ICONTAINS, 'Contains (Case Insensitive)'),
        (FT_IN, 'In List (Comma Seperated - eg 1,2,3)'),
        (FT_GT, 'Greater Than'),
        (FT_GTE, 'Greater Than / Equals'),
        (FT_LT, 'Less Than'),
        (FT_LTE, 'Less Than / Equals'),
        (FT_STARTSWITH, 'Starts With'),
        (FT_ISTARTSWITH, 'Starts With (Case Insensitive)'),
        (FT_ENDSWITH, 'Ends With'),
        (FT_IENDSWITH, 'Ends With (Case Insensitive)'),
        (FT_RANGE, 'Range'),
        (FT_WEEKDAY, 'Week Day'),
        (FT_ISNULL, 'Is Null'),
        (FT_REGEX, 'Regular Expression'),
        (FT_IREGEX, 'Reg. Exp. (Case Insensitive)')
    )

    path = models.CharField(max_length=2000, blank=True)
    path_verbose = models.CharField(max_length=2000, blank=True)
    field = models.CharField(max_length=2000)
    field_verbose = models.CharField(max_length=2000)
    filter_type = models.CharField(max_length=20, choices=FILTER_TYPE_CHOICES, blank=True, default=FT_ICONTAINS)
    filter_value = models.CharField(max_length=2000)
    filter_value2 = models.CharField(max_length=2000, blank=True)
    exclude = models.BooleanField(default=False)
    position = models.PositiveSmallIntegerField(blank=True, null=True)
    or_filter = models.BooleanField(default=False)

    report = models.ForeignKey('Report')

    class Meta:
        ordering = ['position']

    @staticmethod
    def get_report_filters(report):
        """
        Returns the queryset filters and excludes as well as any error messages that might accompany them
        :param report: Report object for which to retrieve the filters and excludes
        :return: filters, excludes and messages
        """
        and_filters = []
        or_filters = []
        excludes = {}
        message = ''

        report_filter_fields = report.filterfield_set.all()

        for filter_field in report_filter_fields:
            # remove the namespace redundancy
            field_verbose = filter_field.field_verbose
            path = filter_field.path
            field = filter_field.field
            filter_type = filter_field.filter_type
            field_filter_value = filter_field.filter_value
            field_filter_value2 = filter_field.filter_value2

            filter_string = str(path + field)

            try:
                # exclude properties from standard ORM filtering
                # Properties shouldn't reach here but, just in case, let's cater for the possible eventuality
                if '[property]' in field_verbose:
                    continue
                if '[custom' in field_verbose:
                    continue

                if filter_type:
                    filter_string += f'__{filter_type}'

                # Check for special types such as isnull
                if filter_type == FilterField.FT_ISNULL and field_filter_value == "0":
                    filter_ = {filter_string: False}
                elif filter_type == FilterField.FT_IN:
                    filter_ = {filter_string: field_filter_value.split(',')}
                else:
                    # All filter values are stored as strings, but may need to be converted
                    if '[Date' in field_verbose:
                        filter_value = FilterField.get_date_filter_value(filter_field)
                    elif filter_type == FilterField.FT_RANGE:
                        filter_value = [field_filter_value, field_filter_value2]
                    else:
                        filter_value = field_filter_value

                    filter_ = (filter_string    , filter_value)

                if filter_field.exclude:
                    excludes.update(filter_)
                elif filter_field.or_filter == True:
                    or_filters.append(filter_)
                else:
                    and_filters.append(filter_)
            except Exception:
                import sys
                message += f"Filter Error on {filter_field.field_verbose}. If you are using the report builder then "
                message += "you found a bug! "
                message += "If you made this in admin, then you probably did something wrong."

        return and_filters, or_filters, excludes, message

    @staticmethod
    def get_date_filter_value(field):
        """
        Returns the appropriate representation of a date value entered as a filter
        :param field: Model field
        :return:
        """
        date_filter_value = parser.parse(field.filter_value)
        date_filter_value_2 = parser.parse(field.filter_value2)

        if settings.USE_TZ:
            date_filter_value = get_aware_time(date_filter_value)
            date_filter_value_2 = get_aware_time(date_filter_value_2)

        if field.filter_type == FilterField.FT_RANGE:
            filter_value = [date_filter_value, date_filter_value_2]
        else:
            filter_value = date_filter_value

        return filter_value

    def clean(self):
        if self.filter_type == self.FT_RANGE:
            if self.filter_value2 in [None, ""]:
                raise ValidationError('Range filters must have two values')
        return super(FilterField, self).clean()

    def get_choices(self, model, field_name):
        try:
            # The first index of the result of get_field_by_name [0] is the actual field object
            model_field = model._meta.get_field_by_name(field_name)[0]
        except:
            model_field = None
        if model_field and model_field.choices:
            return model_field.choices

    @property
    def choices(self):
        if self.pk:
            model = get_model_from_path_string(self.report.root_model.model_class(), self.path)
            return self.get_choices(model, self.field)

    def __unicode__(self):
        return self.field
