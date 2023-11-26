from django.conf import settings
from django.db import models
from report_builder.utils import get_model_from_path_string

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


class DisplayField(models.Model):
    """
    A display field to show in a report. Always belongs to a Report
    """
    AGC_SUM = 'Sum'
    AGC_COUNT = 'Count'
    AGC_AVG = 'Avg'
    AGC_MAX = 'Max'
    AGC_MIN = 'Min'

    AGGREGATE_CHOICES = (
        (AGC_SUM,'Sum'),
        (AGC_COUNT,'Count'),
        (AGC_AVG,'Avg'),
        (AGC_MAX,'Max'),
        (AGC_MIN,'Min'),
    )

    path = models.CharField(max_length=2000, blank=True)
    path_verbose = models.CharField(max_length=2000, blank=True)
    field = models.CharField(max_length=2000)
    field_verbose = models.CharField(max_length=2000)
    name = models.CharField(max_length=2000)
    sort = models.IntegerField(blank=True, null=True)
    sort_reverse = models.BooleanField(verbose_name="Reverse", default=False)
    width = models.IntegerField(default=15)
    aggregate = models.CharField(max_length=5, choices = AGGREGATE_CHOICES, blank = True)
    position = models.PositiveSmallIntegerField(blank = True, null = True)
    total = models.BooleanField(default=False, verbose_name='Calculate Total Values?')
    group = models.BooleanField(default=False, verbose_name='Group values by this field?')

    report = models.ForeignKey('Report')
    display_format = models.ForeignKey('Format', blank=True, null=True)


    class Meta:
        ordering = ['position']

    def get_choices(self, model, field_name):
        try:
            model_field = model._meta.get_field_by_name(field_name)[0]
        except:
            model_field = None
        if model_field and model_field.choices:
            # See https://github.com/burke-software/django-report-builder/pull/93
            return ((model_field.get_prep_value(key), val) for key, val in model_field.choices)

    @property
    def choices_dict(self):
        choices_dict = {}
        if choices := self.choices:
            for choice in choices:
                choices_dict[choice[0]] = choice[1]
        return choices_dict

    @property
    def choices(self):
        if self.pk:
            model = get_model_from_path_string(self.report.root_model.model_class(), self.path)
            return self.get_choices(model, self.field)

    def __unicode__(self):
        return self.name
