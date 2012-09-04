# -*- coding: utf-8 -*-
import math
from datetime import datetime

from django.db import models
from django.core.urlresolvers import reverse
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.comments import signals as comment_signals
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType

epoch = timezone.utc.localize(datetime(1970, 1, 1))


class Source(models.Model):
    name = models.CharField(max_length=255)
    homepage = models.URLField()
    url = models.URLField()
    crawler = models.CharField(max_length=255, default='rss')
    last_crawled = models.DateTimeField()

    def __unicode__(self):
        return self.name


class ArticleManager(models.Manager):
    def get_ordered(self):
        return self.get_query_set().order_by('-order')\
            .select_related('public_bodies', 'foirequests')

    def recalculate_order(self):
        for a in self.all().iterator():
            a.set_order()
            a.save()


class Article(models.Model):
    title = models.CharField(max_length=255)
    text = models.TextField()
    date = models.DateTimeField()
    url = models.URLField(unique=True, max_length=800)
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

    def get_absolute_url(self):
        return reverse('foiidea-show', kwargs={'article_id': self.id})

    def save(self, *args, **kwargs):
        self.set_order()
        super(Article, self).save(*args, **kwargs)

    def get_order(self, number_of_comments=None):
        """
        From: http://amix.dk/blog/post/19588
        https://github.com/reddit/reddit
        Reddit Hot Formula
        The hot formula. Should match the equivalent function in postgres.
        """
        if number_of_comments is None:
            number_of_comments = self.get_number_of_comments()
        s = self.score * 500 + self.rank * 1000 + number_of_comments * 50
        td = self.date - epoch
        ep_seconds = td.days * 86400 + td.seconds + (float(td.microseconds) / 1000000)
        order = math.log(max(abs(s), 1), 10)
        sign = 1 if s > 0 else -1 if s < 0 else 0
        seconds = ep_seconds - 1134028003
        return round(order + sign * seconds / 45000, 4) * 1000

    def set_order(self, number_of_comments=0):
        self.order = self.get_order(number_of_comments=number_of_comments)

    def get_number_of_comments(self):
        return Comment.objects.filter(
            content_type=ContentType.objects.get_for_model(self),
            object_pk=self.id).count()


@receiver(comment_signals.comment_was_posted,
            dispatch_uid="comment_was_posted_article")
def comment_was_posted_article(sender, comment, request, **kwargs):
    if comment.content_type.model_class() is not Article:
        return
    article = comment.content_object
    article.set_order(article.get_number_of_comments())
    article.save()


from froide.foirequest.models import FoiRequest


@receiver(FoiRequest.request_created,
    dispatch_uid="check_reference")
def check_reference(sender, reference, **kwargs):
    if reference is None:
        return
    if not 'article' in reference:
        return
    try:
        article_id = int(reference['article'])
    except ValueError:
        return
    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        return
    article.foirequests.add(sender)
