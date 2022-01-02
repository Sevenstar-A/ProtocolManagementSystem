from django.contrib.auth import get_user
from django.shortcuts import redirect, render
from django.views import View
from .models import News, Tag
from .forms import NewsForm
from django.utils.decorators import method_decorator
from accounts.utils import staff_required


class NewsFeed(View):
    def get(self, *args, **kwargs):
        news_list = News.objects.filter(published=True).order_by('-date_created')
        return render(self.request, 'connect/news/news_list.html', {
            'news_list': news_list,
            'tag_set': Tag.objects.all(),
            'latest_news': News.objects.all().order_by('-date_created')[:3]
        })

class NewsDetail(View):

    def get(self, *args, **kwargs):
        news_id = kwargs['news_id']
        news = News.objects.get(id=news_id)
        return render(self.request, 'connect/news/news_detail.html', {
            'news': news,
            'tag_set': Tag.objects.all(),
            'latest_news': News.objects.all().order_by('-date_created')[:3]
        })

class SearchNews(View):

    def post(self, *args, **kwargs):
        keyword = self.request.POST.get('keyword')
        if not keyword:
            return redirect('news-feed')
        news_list = News.objects.filter(title__contains=keyword)
        return render(self.request, 'connect/news/search_results.html', {
            'keyword': keyword,
            'news_list': news_list,
            'tag_set': Tag.objects.all(),
            'latest_news': News.objects.all().order_by('-date_created')[:3]
        })

class FilterNews(View):

    def get(self, *args, **kwargs):
        tag_name:str = kwargs['tag_name']
        tag = Tag.objects.get(name=tag_name)
        news_list = tag.news_set.all()
        return render(self.request, 'connect/news/tagged_news.html', {
            'tag': tag,
            'news_list': news_list,
            'tag_set': Tag.objects.all(),
            'latest_news': News.objects.all().order_by('-date_created')[:3]
        })

@method_decorator(staff_required(), 'dispatch')
class NewsList(View):

    def get(self, *args, **kwargs):
        news_list = News.objects.all()
        return render(self.request, 'connect/news/staff/news_list.html', {
            'news_list': news_list,
        })

@method_decorator(staff_required(), 'dispatch')
class CreateNews(View):

    def get(self, *args, **kwargs):
        news_form = NewsForm()
        return render(self.request, 'connect/news/staff/create_news.html', {
            'news_form': news_form,
        })

    def post(self, *args, **kwargs):
        auth_user = get_user(self.request)
        news_form = NewsForm(self.request.POST, self.request.FILES)
        if news_form.is_valid():
            news = news_form.save(commit=False)
            news.created_by = auth_user
            news.save()
            news_form.save_m2m()
            return redirect('news_list')
        else:
            print(news_form.errors)
            return render(self.request, 'connect/news/staff/create_news.html', {
                'news_form': news_form
            })

@method_decorator(staff_required(), 'dispatch')
class EditNews(View):

    def get(self, *args, **kwargs):
        news_id = kwargs['news_id']
        news = News.objects.get(id=news_id)
        news_form = NewsForm(instance=news)
        return render(self.request, 'connect/news/staff/edit_news.html', {
            'news_form': news_form,
            'news': news,
        })

    def post(self, *args, **kwargs):
        news_id = kwargs['news_id']
        news = News.objects.get(id=news_id)
        print('Uploaded files are ', self.request.FILES)
        news_form = NewsForm(self.request.POST, self.request.FILES, instance=news)
        if news_form.is_valid():
            news_form.save(commit=True)
            
        return redirect('edit_news', news_id)


@method_decorator(staff_required(), 'dispatch')
class TaggedNews(View):
    
    def get(self, *args, **kwargs):
        tag_name:str = kwargs['tag_name'].upper()
        tag : Tag = Tag.objects.get(name=tag_name)
        return render(self.request, 'connect/news/staff/filter_with_tag.html', {
            'tag': tag,
            'news_list': tag.news_set.all()
        })


@method_decorator(staff_required(), 'dispatch')
class DeleteNews(View):

    def get(self, *args, **kwargs):
        news_id = kwargs['news_id']
        news = News.objects.get(id=news_id)
        news.delete()
        return redirect('news_list')


@method_decorator(staff_required(), 'dispatch')
class TogglePublishedStatus(View):

    def get(self, *args, **kwargs):
        news_id = kwargs['news_id']
        news = News.objects.get(id=news_id)
        news.published = not news.published
        news.save()
        return redirect('news_list')