from django.db import models


class Format(models.Model):
    """ 
    A specifies a Python string format for e.g. `DisplayField`s. 
    """
    name = models.CharField(max_length=50, blank=True, default='')
    string = models.CharField(max_length=300, blank=True, default='', help_text='Python string format. Ex ${} would place a $ in front of the result.')

    def __unicode__(self):
        return self.name