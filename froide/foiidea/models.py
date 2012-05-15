from django.db import models



class Source(models.Model):
    name = models.CharField(max_length=255)
    homepage = models.URLField()
    url = models.URLField()
    crawler = models.CharField(max_length=255)
    last_crawled = models.DateTimeField()

    def __unicode__(self):
        return self.name


class Article(models.Model):
    title = models.CharField(max_length=255)
    text = models.TextField()
    date = models.DateTimeField()
    url = models.URLField(unique=True)
    source = models.ForeignKey(Source, null=True)
    public_bodies = models.ManyToManyField('publicbody.PublicBody', blank=True)
    foirequests = models.ManyToManyField('foirequest.FoiRequest', blank=True)

    def __unicode__(self):
        return u"%s: %s" % (self.source, self.title)

    class Meta:
        ordering = ['-date']
