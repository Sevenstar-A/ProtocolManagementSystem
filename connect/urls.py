from django.contrib import admin
from django.urls import path
from django.urls.conf import include

from connect.views import (CreateNews, DeleteNews, EditNews, FilterNews, NewsDetail,
                           NewsFeed, NewsList, SearchNews, TaggedNews,
                           TogglePublishedStatus)

urlpatterns = [
    path('news-feed/', NewsFeed.as_view(), name='news-feed'),
    path('news-feed/<int:news_id>/', NewsDetail.as_view(), name='news_detail'),
    path('news/', NewsList.as_view(), name='news_list'),
    path('news/create/', CreateNews.as_view(), name='create_news'),
    path('news/edit/<int:news_id>/', EditNews.as_view(), name='edit_news'),
    path('news-feed/search/', SearchNews.as_view(), name='search-news'),
    path('news-feed/filter/<str:tag_name>/', FilterNews.as_view(), name='filter-news'),
    path('news/delete/<int:news_id>/', DeleteNews.as_view(), name='delete_news'),
    path('news/toggle-publish/<int:news_id>/', TogglePublishedStatus.as_view(), name='toggle-publish'),
    path('news/filter-tag/<str:tag_name>/',TaggedNews.as_view(), name='filter-tag'),
    
]
