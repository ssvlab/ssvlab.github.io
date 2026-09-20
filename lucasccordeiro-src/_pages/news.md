---
layout: page
permalink: /news/
title: news
nav: true
nav_order: 1
description: The complete archive of announcements, newest first. The home page shows only the most recent few.
---

{% assign news_years = site.news | reverse | group_by_exp: 'item', "item.date | date: '%Y'" %}
{% for year in news_years %}
  <h2 id="{{ year.name }}">{{ year.name }}</h2>
  <div class="news">
    <div class="table-responsive">
      <table class="table table-sm table-borderless">
        {% for item in year.items %}
          <tr>
            <th scope="row" style="width: 20%">{{ item.date | date: '%b %d' }}</th>
            <td>
              {% if item.inline %}
                {{ item.content | remove: '<p>' | remove: '</p>' | emojify }}
              {% else %}
                <a class="news-title" href="{{ item.url | relative_url }}">{{ item.title }}</a>
              {% endif %}
            </td>
          </tr>
        {% endfor %}
      </table>
    </div>
  </div>
{% endfor %}
