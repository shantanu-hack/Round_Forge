RESOURCE_MAP = {
    "practical implementation detail": [
        {"title": "roadmap.sh backend roadmap", "url": "https://roadmap.sh/backend"},
        {"title": "Django documentation", "url": "https://docs.djangoproject.com/en/5.1/"},
        {"title": "MDN HTTP overview", "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview"},
    ],
    "dbms": [
        {"title": "GeeksForGeeks DBMS", "url": "https://www.geeksforgeeks.org/dbms/"},
        {"title": "SQLBolt interactive SQL", "url": "https://sqlbolt.com/"},
        {"title": "Database normalization guide", "url": "https://www.guru99.com/database-normalization.html"},
    ],
    "dsa": [
        {"title": "LeetCode beginner problem sets", "url": "https://leetcode.com/problemset/"},
        {"title": "NeetCode roadmap", "url": "https://neetcode.io/roadmap"},
        {"title": "GeeksForGeeks DSA tutorial", "url": "https://www.geeksforgeeks.org/data-structures/"},
    ],
    "system design": [
        {"title": "roadmap.sh system design roadmap", "url": "https://roadmap.sh/system-design"},
        {"title": "System Design Primer", "url": "https://github.com/donnemartin/system-design-primer"},
        {"title": "AWS architecture center", "url": "https://aws.amazon.com/architecture/"},
    ],
    "communication": [
        {"title": "STAR method guide", "url": "https://www.themuse.com/advice/star-interview-method"},
        {"title": "Google re:Work structured interviewing", "url": "https://rework.withgoogle.com/guides/hiring-use-structured-interviewing/steps/introduction/"},
        {"title": "Toastmasters impromptu speaking tips", "url": "https://www.toastmasters.org/resources/public-speaking-tips"},
    ],
    "communication structure": [
        {"title": "STAR method guide", "url": "https://www.themuse.com/advice/star-interview-method"},
        {"title": "Harvard Business Review concise communication", "url": "https://hbr.org/2016/11/how-to-write-email-with-military-precision"},
    ],
    "specific examples": [
        {"title": "STAR method guide", "url": "https://www.themuse.com/advice/star-interview-method"},
        {"title": "MIT CAPD behavioral interview guide", "url": "https://capd.mit.edu/resources/behavioral-interviews/"},
    ],
    "aptitude": [
        {"title": "IndiaBIX aptitude practice", "url": "https://www.indiabix.com/aptitude/questions-and-answers/"},
        {"title": "GeeksForGeeks quantitative aptitude", "url": "https://www.geeksforgeeks.org/quantitative-aptitude/"},
    ],
    "technical": [
        {"title": "roadmap.sh computer science roadmap", "url": "https://roadmap.sh/computer-science"},
        {"title": "Django documentation", "url": "https://docs.djangoproject.com/en/5.1/"},
    ],
}

DEFAULT_RESOURCES = [
    {"title": "roadmap.sh learning roadmaps", "url": "https://roadmap.sh/"},
    {"title": "STAR interview method guide", "url": "https://www.themuse.com/advice/star-interview-method"},
    {"title": "GeeksForGeeks aptitude preparation", "url": "https://www.geeksforgeeks.org/aptitude-gq/"},
]


def recommend_resources(weaknesses):
    resources = []
    seen = set()
    text = " ".join(str(item).lower() for item in weaknesses)
    for key, items in RESOURCE_MAP.items():
        if key in text:
            for item in items:
                if item["url"] not in seen:
                    resources.append(item)
                    seen.add(item["url"])
    return (resources or DEFAULT_RESOURCES)[:5]
