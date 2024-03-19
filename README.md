
# Google Search Console for Python (by Antoine Eripret)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Package purpose and content
`gscwrapper` is aimed at providing SEO profesionnals wotking with Python a strong basis to work with [Google Search Console](https://support.google.com/webmasters/answer/9128668)'s data. 

It provides an easy way to query and work with data from the following endpoints for the API: 
* [Search Analytics](https://developers.google.com/webmaster-tools/v1/searchanalytics?hl=en)
* [URL Inspection](https://developers.google.com/webmaster-tools/v1/urlInspection.index/urlInspection.index?hl=en)
* [Sitemaps](https://developers.google.com/webmaster-tools/v1/sitemaps?hl=en)

You can also use it to query your [GSC bulk data export](https://support.google.com/webmasters/answer/12918484?hl=en) without having to worry about writing SQL code. 

## Another GSC library? 

There are countless GSC libraries available. My favorite (and the one I've been using for years) is available [here](https://github.com/joshcarty/google-searchconsole). That being said, these libraries: 

* **Are often limited to downloading data** and don't offer methods to run common SEO analysis. I would often end up copying my code between notebooks and I needed a library to centralize the common operations I often do. 
* Are sometimes owned by non-SEO and therefore aren't always up-to-date, especially when there is an API update. Python is used by many SEO professionals and yet **we often rely on non-SEO to maintain the libraries we use as an industry**.    

I've decided to create my own based on my most common needs as a SEO profesionnal. It has also been a fun project to work on :)  

**DISCLAIMER**: **this library is not aimed at taking decisions for you, it just speeds up some repetitive data manipulation tasks we often do**. I strongly advise you to read & understand the code behind a method if you aim at taking decisions only based on the output of a method. In most cases, the only library used under the hood is [Pandas](https://pandas.pydata.org/). 

## Documentation 

- [Installation Instructions (API)](./README-API.md)
- [Installation Instructions (BQ)](./README-BQ.md)
- [List of methods](./README-METHODS.md)

## Can I run it in a Jupyter Notebook? 

While I haven't debugged my library on Colab and other similar products, I use (extensively) Jupyter notebooks (through VS Code) on my local machine, and it works perfectly. If you have any issue, please let me know and I'll have a look. 

## Suggestions? Issues? 

I'm more than welcome to receive suggestions or solve issues through GitHub. Nevertheless: 

* **The code is extensively commented** to make it readable for everyone, even if you don't master Python. If you have a question on how a method works under the hood, please have a look at the code first. 
* **I'm not a developer** and this is, by far, the most complex project I had to work on by myself. I try to stick to concepts I understand and I won't update my code just because I'm not using a best practice here and there. 
* **I do it for free** and hence I have to prioritize my (paid) work and my personnal life over this library. 

