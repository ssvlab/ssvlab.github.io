---
layout: page
permalink: /blog/
title: blogs
nav: true
nav_order: 1.5
description: Posts on our research, newest first.
---

{% for post in site.posts %}
  {% unless post.categories contains 'external-posts' %}
  <div class="mb-4">
    <h3 class="mb-1"><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
    <p class="post-meta mb-1">{{ post.date | date: '%B %-d, %Y' }}{% if post.tags.size > 0 %} &middot; {{ post.tags | join: ', ' }}{% endif %}</p>
    <p class="mb-0">{{ post.description }}</p>
  </div>
  {% endunless %}
{% endfor %}
