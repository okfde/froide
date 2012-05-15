import math
from datetime import datetime

from django.db import models

epoch = datetime(1970, 1, 1)


class Source(models.Model):
    name = models.CharField(max_length=255)
    homepage = models.URLField()
    url = models.URLField()
    crawler = models.CharField(max_length=255)
    last_crawled = models.DateTimeField()

    def __unicode__(self):
        return self.name


class ArticleManager(models.Manager):
    def get_ordered(self):
        return self.get_query_set().order_by('-order').select_related('public_bodies', 'foirequests')

    def recalculate_order(self):
        for a in self.all().iterator():
            a.set_order()
            a.save()


class Article(models.Model):
    title = models.CharField(max_length=255)
    text = models.TextField()
    date = models.DateTimeField()
    url = models.URLField(unique=True)
    score = models.IntegerField(default=0)  # calculated
    rank = models.IntegerField(default=0)  # user
    order = models.IntegerField(default=0)  # order in list
    source = models.ForeignKey(Source, null=True)
    public_bodies = models.ManyToManyField('publicbody.PublicBody', blank=True)
    foirequests = models.ManyToManyField('foirequest.FoiRequest', blank=True)

    objects = ArticleManager()

    class Meta:
        ordering = ['-order']

    def __unicode__(self):
        return u"%s: %s" % (self.source, self.title)

    def get_order(self):
        """
        From: http://amix.dk/blog/post/19588
        https://github.com/reddit/reddit
        Reddit Hot Formula
        The hot formula. Should match the equivalent function in postgres.
        """
        s = self.score + self.rank
        td = self.date - epoch
        ep_seconds = td.days * 86400 + td.seconds + (float(td.microseconds) / 1000000)
        order = math.log(max(abs(s), 1), 10)
        sign = 1 if s > 0 else -1 if s < 0 else 0
        seconds = ep_seconds - 1134028003
        return round(order + sign * seconds / 45000, 7)

    def set_order(self):
        self.order = self.get_order()
