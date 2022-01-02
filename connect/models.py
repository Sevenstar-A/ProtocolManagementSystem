from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Tag(models.Model):
    name:str = models.CharField(max_length=100)
    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        self.name = self.name.upper()
        return super().save(*args, **kwargs)

class News(models.Model):
    class Meta:
        verbose_name = "News"

    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=200)
    image = models.ImageField( blank=True, default="", upload_to="Connect/NewsImages/")
    content = models.TextField()
    tags = models.ManyToManyField(to=Tag, related_name='news_set')
    published = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.title


class Events():
    pass
