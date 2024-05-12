---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults

layout: default
title: ""
---

Sommige dingen vallen pas op als je er als buitenstaander naar kijkt. Met enige onregelmaat zal ik hier korte krabbels over schrijven.

## De vijf meest recente

{% assign recent_articles = site.posts | sort: 'date' | reverse %}
{% assign post_limit = 5 %}
{% assign post_count = 0 %}

<ul class="blog-posts">
  {% for post in recent_articles %}
    {% if post_count < post_limit %}
      {% assign post_count = post_count | plus: 1 %}
      <li>
        <span>
          <i>
            <time datetime="{{ post.date | date: "%Y-%m-%d" }}" pubdate="">
              {{ post.date | date: "%b %-d, %Y" }}
            </time>
          </i>
        </span>
        <a href="{{ site.baseurl }}{{ post.url }}">{{ post.title }}</a>
      </li>
    {% endif %}
  {% endfor %}
</ul>

Geen artikel missen? Volg de [RSS feed](/feed.xml) of mij op [Twitter](https://twitter.com/Roald87).

_Geïnspireerd door [ZOESKLÖT.nl](https://www.zoesklot.nl/)_
